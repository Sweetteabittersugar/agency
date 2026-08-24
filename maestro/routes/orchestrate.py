"""智能调度 + 路由建议 + 五阶段管线"""

import json
import hashlib
import os
import re
import threading
import uuid
from pathlib import Path

# 编排器默认模型 — 全局变量，_policy_gate / _run_pipeline_orchestrate 共用
orchestrator_model = "deepseek-v4-pro"


def _orch_estimate_tokens(text: str, model: str = "") -> int:
    """Token 估算——根据模型 tokenizer 特性加权。"""
    from maestro.models import estimate_tokens
    return estimate_tokens(text, model or "deepseek-v4-flash")
import sys
import time
import subprocess
import logging

from maestro.shared import (
    PROJECT_ROOT,
    CLAUDE_BIN,
)
from maestro.task_classifier import (
    _extract_plan,
    classify_task_complexity,
)
from maestro.app_config import (
    RUN_ARTIFACTS_DIR,
    RUN_LEDGER_PATH,
    STATE_DIR,
    build_isolated_env,
)
from maestro.execution_dag import DagNode, ExecutionDAG
from maestro.project_access import ProjectAccessError, project_binding
from maestro.run_ledger import (
    LedgerError,
    RunLedger,
    RunnerClaimConflict,
    RunResumeRejected,
    task_digest,
    validate_run_id,
)
from maestro.main import simple_route
from maestro.pipeline import (
    PipelineStateMachine,
    pass_k_verify,
    select_model,
    resolve_model_name,
    STAGE_ORDER,
    TASK_STATES,
    hard_gate_check,
)
from maestro.context_layer import ContextLayer
from maestro.permission_engine import get_engine
from maestro.coordinator import Coordinator

log = logging.getLogger(__name__)

RUNNER_LEASE_SECONDS = 900


class _RunnerLeaseWatchdog:
    """Renew one exact runner fence while a model process is active."""

    def __init__(self, ledger: RunLedger, run_id: str, owner: str, fence: str):
        self.ledger = ledger
        self.run_id = run_id
        self.owner = owner
        self.fence = fence
        self.error: Exception | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        interval = max(1, RUNNER_LEASE_SECONDS // 3)
        while not self._stop.wait(interval):
            try:
                self.ledger.renew_runner(
                    self.run_id,
                    self.owner,
                    self.fence,
                    lease_seconds=RUNNER_LEASE_SECONDS,
                )
            except Exception as exc:  # surfaced on the request thread
                self.error = exc
                self._stop.set()

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)
        if self.error is not None:
            raise RunnerClaimConflict(str(self.error))


def _prepare_run(body: dict) -> dict:
    raw_run_id = body.get("run_id")
    if raw_run_id is not None and not isinstance(raw_run_id, str):
        raise LedgerError("run_id must be a string")
    requested_run_id = raw_run_id.strip() if isinstance(raw_run_id, str) else None
    if requested_run_id == "":
        requested_run_id = None
    if requested_run_id is not None:
        validate_run_id(requested_run_id)

    task = str(body.get("task") or "")
    project_path = project_binding(body.get("proj_dir"))
    digest = task_digest(task)
    ledger = RunLedger(RUN_LEDGER_PATH)
    if requested_run_id and ledger.has_run(requested_run_id):
        ledger.resume_run(
            requested_run_id,
            task_digest_value=digest,
            project_path=project_path,
        )
        run_id = requested_run_id
    else:
        run_id = ledger.create_run(
            run_id=requested_run_id,
            task_digest_value=digest,
            project_path=project_path,
            metadata={"api_provider": str(body.get("api_provider") or "")},
        )
    owner = f"agency-{os.getpid()}-{threading.get_ident()}-{uuid.uuid4().hex[:8]}"
    fence = ledger.claim_runner(run_id, owner, lease_seconds=RUNNER_LEASE_SECONDS)
    return {
        "ledger": ledger,
        "run_id": run_id,
        "owner": owner,
        "fence": fence,
        "project_path": project_path,
        "task_digest": digest,
    }


def _store_run_artifact(run_id: str, stage: str, output: str) -> tuple[str, str]:
    validate_run_id(run_id)
    digest = hashlib.sha256(output.encode("utf-8")).hexdigest()
    root = RUN_ARTIFACTS_DIR.expanduser().resolve()
    target = (root / run_id / f"{stage}-{digest}.txt").resolve()
    if os.path.commonpath((str(target), str(root))) != str(root):
        raise LedgerError("run artifact path escaped its local state directory")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(output, encoding="utf-8")
    return str(target), digest


def _load_run_artifact(reference: str, expected_digest: str) -> str:
    root = RUN_ARTIFACTS_DIR.expanduser().resolve()
    target = Path(reference).expanduser().resolve(strict=True)
    if os.path.commonpath((str(target), str(root))) != str(root):
        raise LedgerError("run artifact is outside the local state directory")
    output = target.read_text(encoding="utf-8")
    if hashlib.sha256(output.encode("utf-8")).hexdigest() != expected_digest:
        raise LedgerError("run artifact digest mismatch")
    return output


def _policy_gate(stage: str, output: str, task_text: str, policy, coordinator) -> str | None:
    """策略门：阶段推进前执行 Policy Checkpoint。返回错误消息或 None

    为什么每阶段都检查成本而非只在开始时检查一次？
    因为 pass@k 和复核可能让实际 token 远超预估，阶段间检查可以在中途拦截超支。
    """
    task_id = task_text[:60]

    if stage == "plan":
        planned_files = re.findall(r"(?:文件|修改|创建|写入)[：:]\s*([^\s,;；\n]+)", output)
        planned_files += re.findall(r'[`"\']([\w./\\-]+\.\w{1,6})[`"\']', output)
        if planned_files:
            ok, msg = policy.pre_write_check("pipeline", planned_files[:10])
            if not ok:
                coordinator.escalate(task_id, msg, "block")
                return msg

    elif stage in ("implement", "review"):
        ok, msg = policy.validate_output(output, "")
        if not ok:
            coordinator.escalate(task_id, msg, "warn")

    # 成本检查（每个阶段）
    estimated_units = _orch_estimate_tokens(output + " " + task_text, orchestrator_model)
    ok, msg = policy.check_cost_budget(estimated_units)
    if not ok:
        coordinator.escalate(task_id, msg, "block")
        return msg

    return None


def handle_route(handler, body):
    """POST /api/route — 三级路由建议（关键词+语义+LLM兜底）+ 置信度门控"""
    task = body.get("task", "")
    force_agent = body.get("force_agent", "")

    from maestro.routes.category import classify

    category = classify(task)

    # 强制指定 agent 时跳过路由
    if force_agent:
        handler.send_json(
            {
                "agent": force_agent,
                "model": "",
                "confidence": 0.99,
                "keyword_score": 0.0,
                "semantic_score": 0.0,
                "source": "force",
                "method": "force",
                "category": category,
                "matched_keywords": 0,
                "candidates": [],
                "low_confidence": False,
                "fallback_chain": [],
            }
        )
        return True

    route_info = simple_route(task)

    if route_info:
        handler.send_json(
            {
                "agent": route_info["agent"],
                "model": route_info.get("model", ""),
                "confidence": route_info.get("confidence", 0),
                "keyword_score": route_info.get("keyword_score", 0),
                "semantic_score": route_info.get("semantic_score", 0),
                "source": route_info.get("source", "keyword"),
                "method": route_info.get("method", "three_tier"),
                "category": category,
                "matched_keywords": route_info.get("matched_keywords", 0),
                "candidates": route_info.get("candidates", []),
                "low_confidence": route_info.get("low_confidence", False),
                "fallback_chain": route_info.get("fallback_chain", []),
            }
        )
    else:
        handler.send_json(
            {
                "agent": "orchestrator",
                "model": "",
                "confidence": 0.0,
                "keyword_score": 0.0,
                "semantic_score": 0.0,
                "source": "fallback",
                "method": "fallback",
                "category": category,
                "matched_keywords": 0,
                "candidates": [],
                "low_confidence": True,
                "fallback_chain": [],
            }
        )
    return True


def handle_orchestrate(handler, body):
    """POST /api/orchestrate — 智能调度 SSE 流（支持 pipeline 模式）

    决策点：前端传 pipeline=true → 走五阶段管线（plan→implement→review→verify→deploy）；
    否则走单 agent 直调。pipeline 使用 pass@k 验证（默认 k=3），失败则自动重试或升级模型。
    """
    task = body.get("task", "")
    proj_dir = body.get("proj_dir", "")
    api_key = body.get("api_key", "")
    api_provider = body.get("api_provider", "")
    use_pipeline = body.get("pipeline", False)

    if not task:
        handler.send_json(
            {"error": "请输入要执行的任务描述。智能调度需要一个具体的任务才能完成拆分和分派"}
        )
        return True
    if not CLAUDE_BIN:
        handler.send_json({"error": "Claude CLI not found"})
        return True

    try:
        durable = _prepare_run(body)
    except ProjectAccessError as exc:
        handler.send_json({"error": str(exc), "code": exc.code}, 403)
        return True
    except RunnerClaimConflict as exc:
        handler.send_json({"error": str(exc), "code": "RUNNER_ALREADY_ACTIVE"}, 409)
        return True
    except (LedgerError, RunResumeRejected) as exc:
        handler.send_json({"error": str(exc), "code": "RUN_RESUME_REJECTED"}, 409)
        return True

    ledger = durable["ledger"]
    run_id = durable["run_id"]
    runner_owner = durable["owner"]
    runner_fence = durable["fence"]
    proj_dir = durable["project_path"]

    if ledger.unresolved_side_effects(run_id):
        handler.send_response(200)
        handler.send_header("Content-Type", "text/event-stream")
        handler.send_header("Cache-Control", "no-cache")
        handler.send_header("Connection", "close")
        handler.end_headers()
        payload = {
            "code": "ACTION_RECONCILIATION_REQUIRED",
            "msg": "A previous side-effecting action has no recorded result; verify it before continuing.",
            "run_id": run_id,
        }
        handler.wfile.write(
            f"event: pause\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n".encode()
        )
        handler.wfile.flush()
        ledger.finish_run(run_id, "paused", runner_fence=runner_fence)
        ledger.release_runner(run_id, runner_owner, runner_fence)
        return True

    if use_pipeline:
        internal_body = dict(body)
        internal_body["proj_dir"] = proj_dir
        internal_body["_durable"] = durable
        return _run_pipeline_orchestrate(handler, internal_body)

    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "close")
    handler.end_headers()

    proc = None
    full_output = ""
    start_time = time.time()
    watchdog = _RunnerLeaseWatchdog(ledger, run_id, runner_owner, runner_fence)
    watchdog.start()

    def _write_sse(event_type: str, data: dict):
        data = dict(data)
        data.setdefault("run_id", run_id)
        handler.wfile.write(
            f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()
        )
        handler.wfile.flush()

    try:
        _write_sse("stage", {"stage": "init", "status": "active"})
        # 提示注入检测：将用户输入送入 safety 引擎扫描
        from maestro.safety import check_input as _safety_check
        _check_ok, _check_msg = _safety_check(task, source="orchestrate")
        if not _check_ok:
            _write_sse("error", {"msg": "输入被安全策略拦截: " + (_check_msg or "未知风险")})
            ledger.finish_run(run_id, "failed", runner_fence=runner_fence)
            return True

        safe_task = task.replace("\n", " ").replace("\r", " ")
        shell_prefix = ["cmd", "/c"] if sys.platform == "win32" else []
        cmd = shell_prefix + [
            CLAUDE_BIN,
            "-p",
            safe_task,
            "--bare",
            "--permission-mode",
            "auto",
            "--agent",
            "orchestrator",
        ]
        cmd += ["--add-dir", proj_dir]

        _write_sse("phase", {"msg": "🧠 分析任务…"})

        ledger.record_action_intent(
            run_id,
            "orchestrate",
            "orchestrate:0",
            {"project_path": proj_dir},
            side_effect=True,
            runner_fence=runner_fence,
        )

        iso_env = build_isolated_env(api_key, api_provider)
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=proj_dir,
            env=iso_env,
        )
        from maestro.proc_manager import track_proc

        track_proc(proc)
        for line in iter(proc.stdout.readline, ""):
            if not line:
                break
            stripped = line.rstrip("\n\r")
            if not stripped:
                continue
            full_output += stripped + "\n"
            try:
                _write_sse("content", {"content": stripped + chr(10)})
            except (BrokenPipeError, ConnectionResetError):
                break

        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            log.warning("orchestrate proc wait timeout")

        ledger.record_action_result(
            run_id,
            "orchestrate:0",
            {"status": "completed", "exit_code": proc.returncode},
            runner_fence=runner_fence,
        )

        from maestro.models import estimate_cost
        from maestro.web_cost import record_cost

        elapsed = time.time() - start_time
        estimated_input_units = _orch_estimate_tokens(task, orchestrator_model)
        out_tokens = len(full_output) // 2
        cost, _, _ = estimate_cost(orchestrator_model, estimated_input_units, out_tokens)
        record_cost(
            PROJECT_ROOT,
            time.strftime("%Y-%m-%d %H:%M:%S"),
            orchestrator_model,
            estimated_input_units,
            out_tokens,
            cost,
            elapsed,
            "orchestrator",
            proj_dir or "",
        )

        plan = _extract_plan(full_output)
        if plan:
            _write_sse("plan", plan)
            _write_sse(
                "done",
                {
                    "summary": "Orchestration plan ready",
                    "elapsed": round(elapsed, 1),
                    "cost": round(cost, 6),
                },
            )
        else:
            _write_sse(
                "done",
                {"summary": "调度计划解析失败。可能 AI 返回格式异常，请用更简单的任务描述重试"},
            )
        ledger.finish_run(run_id, "completed", runner_fence=runner_fence)
    except Exception as e:
        try:
            _write_sse("error", {"msg": str(e), "code": "ORCHESTRATION_FAILED"})
            ledger.finish_run(run_id, "failed", runner_fence=runner_fence)
        except Exception as e2:
            log.warning(f"orchestrate SSE error write error: {e2}")
    finally:
        if proc:
            from maestro.proc_manager import kill_proc, untrack_proc

            kill_proc(proc)
            untrack_proc(proc)
        try:
            watchdog.stop()
        except RunnerClaimConflict as exc:
            log.error("runner lease lost for %s: %s", run_id, exc)
        try:
            ledger.release_runner(run_id, runner_owner, runner_fence)
        except RunnerClaimConflict:
            pass
    return True


def _run_pipeline_orchestrate(handler, body) -> bool:
    """五阶段管线编排 SSE 流

    为什么用 PipelineStateMachine 而非线性调用？
    每个阶段都可能通过 pass@k 多次生成+验证（默认 k=3），失败时自动模型升级
    （如 deepseek → claude-haiku → claude-sonnet），而不是直接报错。
    状态机保证阶段间依赖顺序（plan→implement→review→verify→deploy）的同时，
    允许单阶段内部重试，避免从头开始。
    """
    task = body.get("task", "")
    proj_dir = body.get("proj_dir", "")
    api_key = body.get("api_key", "")
    api_provider = body.get("api_provider", "deepseek")
    agent = body.get("force_agent", "")
    max_retries = body.get("max_retries", 2)
    durable = body["_durable"]
    ledger: RunLedger = durable["ledger"]
    run_id = durable["run_id"]
    runner_owner = durable["owner"]
    runner_fence = durable["fence"]

    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "close")
    handler.end_headers()

    sm = PipelineStateMachine({"task": task, "agent": agent, "proj_dir": proj_dir})
    task_id = run_id
    ctx = ContextLayer(task_id, STATE_DIR)
    policy = get_engine()
    coordinator = Coordinator()
    stages_completed = []
    proc = None
    start_time = time.time()
    full_output_all = ""
    dag = None
    run_finished = False
    watchdog = _RunnerLeaseWatchdog(ledger, run_id, runner_owner, runner_fence)
    watchdog.start()

    def _write_sse(event_type: str, data: dict):
        try:
            data = dict(data)
            data.setdefault("run_id", run_id)
            handler.wfile.write(
                f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()
            )
            handler.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _ctx_write_stage(ctx: ContextLayer, stage: str, output: str):
        """将阶段产出写入共享记忆黑板"""
        key_map = {
            "research": "research_result",
            "plan": "plan",
            "dry_run": "dry_run_plan",
            "gate": "gate_result",
            "implement": "implemented_files",
            "review": "review_findings",
            "verify": "verify_result",
        }
        key = key_map.get(stage, f"{stage}_output")
        ctx.set_short_term(key, output[:5000])
        ctx.log_episodic(stage, f"stage_{stage}_complete", output[:500])

    def _call_claude_stage(prompt: str, model_name: str, perm_mode: str = "auto") -> str:
        """调用 Claude CLI 执行单个阶段，返回输出文本"""
        nonlocal proc
        safe_prompt = prompt.replace("\n", " ").replace("\r", " ")
        iso_env = build_isolated_env(api_key, api_provider)
        iso_env["ANTHROPIC_MODEL"] = model_name
        shell_prefix = ["cmd", "/c"] if sys.platform == "win32" else []
        cmd = shell_prefix + [
            CLAUDE_BIN,
            "-p",
            safe_prompt,
            "--bare",
            "--permission-mode",
            perm_mode,
            "--model",
            model_name,
        ]
        cmd += ["--add-dir", proj_dir]
        output = ""
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=proj_dir,
            env=iso_env,
        )
        from maestro.proc_manager import track_proc

        track_proc(proc)
        for line in iter(proc.stdout.readline, ""):
            if not line:
                break
            stripped = line.rstrip("\n\r")
            if not stripped:
                continue
            output += stripped + "\n"
            _write_sse("", {"content": stripped + chr(10)})
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            pass
        finally:
            from maestro.proc_manager import kill_proc, untrack_proc

            kill_proc(proc)
            untrack_proc(proc)
            proc = None
        return output

    def _parse_dry_run_plan(output: str) -> dict:
        """从 dry-run 输出中提取结构化变更计划"""
        import re

        m = re.search(r"```json\s*\n(.*?)\n```", output, re.DOTALL)
        if not m:
            m = re.search(r'\{[^{}]*"files"\s*:\s*\[.*?\][^{}]*\}', output, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1) if "```" in output else m.group(0))
            except Exception:
                pass
        return {"files": [], "total_changes": 0, "raw_output": output[:1000]}

    try:
        # ── 任务分级路由 ──
        complexity = classify_task_complexity(task)
        _write_sse("phase", {"msg": f"📊 任务复杂度: {complexity}"})

        # trivial: 跳过管线，直通执行
        if complexity == "trivial":
            _write_sse("phase", {"msg": "⚡ 快速通道 — 直接执行"})
            model_tier = select_model({"task": task, "agent": agent}, agent)
            model_name = resolve_model_name(model_tier, api_provider)
            ledger.record_action_intent(
                run_id,
                "direct_execute",
                "direct_execute:0",
                {"project_path": proj_dir},
                side_effect=True,
                runner_fence=runner_fence,
            )
            direct_output = _call_claude_stage(
                f"直接执行以下任务（无需研究/计划/审查）：\n\n{task}",
                model_name,
                perm_mode="acceptEdits",
            )
            ledger.record_action_result(
                run_id,
                "direct_execute:0",
                {"status": "completed"},
                runner_fence=runner_fence,
            )
            full_output_all += direct_output
            _write_sse(
                "done",
                {
                    "summary": "⚡ 快速通道完成",
                    "stages": ["direct_execute"],
                    "elapsed": round(time.time() - start_time, 1),
                    "complexity": "trivial",
                },
            )
            ledger.finish_run(run_id, "completed", runner_fence=runner_fence)
            run_finished = True
            return True

        # 选择阶段列表
        if complexity == "simple":
            pipeline_stages = ["plan", "implement", "verify"]
            _write_sse("phase", {"msg": "⚡ 简化链路: plan → implement → verify"})
        elif complexity == "complex":
            pipeline_stages = list(STAGE_ORDER)  # 完整6阶段
            _write_sse("phase", {"msg": "🔬 完整管线 + pass@k 审查"})
        else:
            pipeline_stages = list(STAGE_ORDER)  # 标准6阶段

        sm.active_stages = pipeline_stages
        nodes = []
        for index, stage in enumerate(pipeline_stages):
            dependency = (pipeline_stages[index - 1],) if index else ()
            node_input = hashlib.sha256(
                f"{durable['task_digest']}:{stage}".encode("utf-8")
            ).hexdigest()
            nodes.append(DagNode(stage, stage, dependency, node_input))
        dag = ExecutionDAG(
            ledger,
            run_id,
            nodes,
            runner_fence=runner_fence,
        )

        # 发送初始管道结构
        _write_sse(
            "stage",
            {
                "stage": "init",
                "status": "active",
                "complexity": complexity,
                "pipeline": [
                    {
                        "stage": s,
                        "label": TASK_STATES[s]["exit"],
                        "enter_condition": TASK_STATES[s]["enter"],
                    }
                    for s in pipeline_stages
                ],
            },
        )

        for stage in pipeline_stages:
            sm.current_stage = stage
            retry_count = 0

            saved = dag.state()[stage]
            if saved["status"] == "completed":
                stage_output = _load_run_artifact(
                    saved["output_ref"], saved["output_digest"]
                )
                sm.advance(stage_output)
                stages_completed.append(stage)
                full_output_all += stage_output
                _ctx_write_stage(ctx, stage, stage_output)
                _write_sse(
                    "stage",
                    {"stage": stage, "status": "passed", "resumed": True},
                )
                continue

            while retry_count <= max_retries:
                dag.start(stage)
                # 通知前端当前阶段
                _write_sse(
                    "stage",
                    {
                        "stage": stage,
                        "status": "active",
                        "retry": retry_count,
                    },
                )

                # ── gate 阶段特殊处理：不调 Agent，直接硬门控 ──
                if stage == "gate":
                    _write_sse("phase", {"msg": "🛡 硬门控检查中…"})
                    dry_plan = _parse_dry_run_plan(sm.stage_outputs.get("dry_run", ""))
                    gate_ok, gate_reason = hard_gate_check(dry_plan)
                    stage_output = json.dumps(
                        {
                            "passed": gate_ok,
                            "reason": gate_reason,
                            "plan": dry_plan,
                        },
                        ensure_ascii=False,
                    )
                    _write_sse(
                        "stage",
                        {
                            "stage": "gate",
                            "status": "passed" if gate_ok else "failed",
                            "gate_result": {"passed": gate_ok, "reason": gate_reason},
                        },
                    )
                    if not gate_ok:
                        _write_sse(
                            "error",
                            {
                                "msg": f"硬门控未通过: {gate_reason}",
                            },
                        )
                        sm.fail_stage(gate_reason)
                        dag.fail(stage, gate_reason)
                        stages_completed.append("gate")
                        break  # gate 失败不重试，直接终止管线
                    sm.advance(stage_output)
                    stages_completed.append(stage)
                    _ctx_write_stage(ctx, stage, stage_output)
                    artifact_ref, output_digest = _store_run_artifact(
                        run_id, stage, stage_output
                    )
                    dag.complete(
                        stage,
                        output_ref=artifact_ref,
                        output_digest=output_digest,
                    )
                    _write_sse(
                        "stage",
                        {
                            "stage": stage,
                            "status": "passed",
                            "output": stage_output[:500],
                        },
                    )
                    break

                # 选择模型
                model_tier = select_model({"task": task, "agent": agent}, agent)
                model_name = resolve_model_name(model_tier, api_provider)
                _write_sse(
                    "stage",
                    {
                        "stage": stage,
                        "status": "active",
                        "model_tier": model_tier,
                        "model_name": model_name,
                    },
                )

                # 获取阶段 prompt，注入共享上下文
                prompt = sm.get_current_prompt()
                ctx_summary = ctx.get_context_for_agent(stage)
                if ctx_summary:
                    prompt = prompt + "\n\n---\n## 共享记忆黑板\n" + ctx_summary
                _write_sse("phase", {"msg": f"📋 阶段: {stage} ({model_tier})"})

                # Only the implementation node may edit the authorized project.
                perm_mode = "acceptEdits" if stage == "implement" else "plan"
                if perm_mode == "plan":
                    _write_sse("phase", {"msg": "🔍 只读预演 — 禁止写文件"})

                action_key = f"{stage}:{retry_count}"
                ledger.record_action_intent(
                    run_id,
                    stage,
                    action_key,
                    {"project_path": proj_dir, "permission_mode": perm_mode},
                    side_effect=stage == "implement",
                    runner_fence=runner_fence,
                )
                try:
                    stage_output = _call_claude_stage(prompt, model_name, perm_mode=perm_mode)
                except Exception as e:
                    log.error(f"阶段 {stage} 调用失败: {e}")
                    if stage == "implement":
                        raise
                    stage_output = f"[错误] {e}"
                ledger.record_action_result(
                    run_id,
                    action_key,
                    {"status": "completed", "output_bytes": len(stage_output.encode("utf-8"))},
                    runner_fence=runner_fence,
                )

                full_output_all += stage_output

                # dry_run 阶段：解析并写入变更计划到 context
                if stage == "dry_run":
                    dry_plan = _parse_dry_run_plan(stage_output)
                    ctx.set_short_term("dry_run_plan", dry_plan)
                    _write_sse(
                        "stage",
                        {
                            "stage": "dry_run",
                            "status": "active",
                            "dry_run_plan": {
                                "total_changes": dry_plan.get("total_changes", 0),
                                "file_count": len(dry_plan.get("files", [])),
                            },
                        },
                    )

                # review 阶段特殊处理：pass@k 验证（仅 complex 任务启用）
                if stage == "review" and complexity == "complex":
                    _write_sse("phase", {"msg": "🔍 pass@3 轻量验证中…"})
                    pk_ok, pk_results = pass_k_verify(
                        stage_output,
                        task,
                        k=3,
                        api_key=api_key,
                        api_provider=api_provider,
                    )
                    _write_sse(
                        "stage",
                        {
                            "stage": "review",
                            "status": "verifying",
                            "pass_k": {
                                "overall": pk_ok,
                                "perspectives": {
                                    name: {"passed": r["passed"]} for name, r in pk_results.items()
                                },
                            },
                        },
                    )
                    if not pk_ok:
                        fail_details = {
                            name: r["raw"][:200]
                            for name, r in pk_results.items()
                            if not r["passed"]
                        }
                        _write_sse(
                            "stage",
                            {
                                "stage": "review",
                                "status": "failed",
                                "reason": f"pass@3 未通过（需 ≥2/3），失败视角: {list(fail_details.keys())}",
                            },
                        )
                        sm.fail_stage(f"pass@3 未通过: {fail_details}")
                        dag.fail(stage, f"pass@3 未通过: {fail_details}")
                        sm.current_stage = stage
                        retry_count += 1
                        continue

                # 检查是否可以推进
                ok, reason = sm.can_advance(stage, stage_output)
                if ok:
                    # ── 策略门：阶段推进前的合规检查 ──
                    gate_fail = _policy_gate(stage, stage_output, task, policy, coordinator)
                    if gate_fail:
                        _write_sse(
                            "stage", {"stage": stage, "status": "blocked", "reason": gate_fail}
                        )
                        sm.fail_stage(gate_fail)
                        dag.block(stage, gate_fail)
                        break

                    sm.advance(stage_output)
                    stages_completed.append(stage)
                    # 写入共享记忆黑板
                    _ctx_write_stage(ctx, stage, stage_output)
                    artifact_ref, output_digest = _store_run_artifact(
                        run_id, stage, stage_output
                    )
                    dag.complete(
                        stage,
                        output_ref=artifact_ref,
                        output_digest=output_digest,
                    )
                    # 记录 coordinator checkpoint
                    _cp_map = {
                        "plan": "plan_approved",
                        "implement": "implement_done",
                        "review": "review_passed",
                    }
                    if stage in _cp_map:
                        try:
                            snapshot = (
                                ctx.get_short_term() if hasattr(ctx, "get_short_term") else {}
                            )
                        except Exception:
                            snapshot = {}
                        coordinator.save_checkpoint(task_id, _cp_map[stage], snapshot)
                    _write_sse(
                        "stage",
                        {
                            "stage": stage,
                            "status": "passed",
                            "output": stage_output[:500],
                        },
                    )
                    break  # 进入下一阶段
                else:
                    _write_sse(
                        "stage",
                        {
                            "stage": stage,
                            "status": "failed",
                            "reason": reason,
                        },
                    )
                    sm.fail_stage(reason)
                    dag.fail(stage, reason)
                    retry_count += 1
                    if retry_count <= max_retries:
                        _write_sse(
                            "phase",
                            {
                                "msg": f"⚠ 阶段 {stage} 未通过 ({reason})，重试 {retry_count}/{max_retries}",
                            },
                        )
                        sm.rollback()
                        sm.current_stage = stage

            if retry_count > max_retries:
                _write_sse(
                    "stage",
                    {
                        "stage": stage,
                        "status": "failed",
                        "reason": f"超过最大重试次数 ({max_retries})",
                    },
                )
                _write_sse(
                    "error",
                    {
                        "msg": f"阶段 {stage} 失败，已重试 {max_retries} 次仍不通过",
                    },
                )
                break

        # 记录费用
        from maestro.models import estimate_cost
        from maestro.web_cost import record_cost

        elapsed = time.time() - start_time
        pipeline_model = "pipeline-v1"
        estimated_input_units = _orch_estimate_tokens(
            task + " " + full_output_all, pipeline_model
        )
        out_tokens = len(full_output_all) // 2
        cost, _, _ = estimate_cost(pipeline_model, estimated_input_units, out_tokens)
        record_cost(
            PROJECT_ROOT,
            time.strftime("%Y-%m-%d %H:%M:%S"),
            pipeline_model,
            estimated_input_units,
            out_tokens,
            cost,
            elapsed,
            "pipeline",
            proj_dir or "",
        )

        # 积累长期记忆 — 成功的阶段模式写入
        if len(stages_completed) >= 3:
            plan_text = ctx.get_short_term().get("plan", "")
            if plan_text:
                ctx.set_long_term("last_successful_plan", str(plan_text)[:3000])
            ctx.set_long_term(
                "pipeline_patterns",
                json.dumps({"stages": stages_completed, "task_len": len(task)}, ensure_ascii=False),
            )

        completed = dag is not None and all(
            item["status"] == "completed" for item in dag.state().values()
        )
        terminal_status = "completed" if completed else "failed"
        ledger.finish_run(run_id, terminal_status, runner_fence=runner_fence)
        run_finished = True
        terminal_event = "done" if completed else "error"
        payload = {
            "summary": f"管线完成: {len(stages_completed)}/{len(pipeline_stages)} 阶段通过",
            "stages": stages_completed,
            "elapsed": round(elapsed, 1),
            "cost": round(cost, 6),
        }
        if not completed:
            payload.update(code="PIPELINE_FAILED", msg="One or more pipeline stages failed")
        _write_sse(terminal_event, payload)

    except Exception as e:
        log.error(f"管线编排异常: {e}", exc_info=True)
        try:
            if ledger.unresolved_side_effects(run_id):
                ledger.finish_run(run_id, "paused", runner_fence=runner_fence)
                run_finished = True
                _write_sse(
                    "pause",
                    {
                        "code": "ACTION_RECONCILIATION_REQUIRED",
                        "msg": "A side-effecting action has no recorded result; it will not be replayed automatically.",
                    },
                )
            else:
                ledger.finish_run(run_id, "failed", runner_fence=runner_fence)
                run_finished = True
                _write_sse("error", {"code": "PIPELINE_FAILED", "msg": str(e)})
        except Exception:
            pass
    finally:
        if proc:
            from maestro.proc_manager import kill_proc, untrack_proc

            kill_proc(proc)
            untrack_proc(proc)
        try:
            watchdog.stop()
        except RunnerClaimConflict as exc:
            log.error("runner lease lost for %s: %s", run_id, exc)
        try:
            ledger.release_runner(run_id, runner_owner, runner_fence)
        except RunnerClaimConflict:
            pass

    return True
