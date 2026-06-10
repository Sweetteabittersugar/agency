"""智能调度 + 路由建议 + 五阶段管线"""
import json
import os
import re
import time
import subprocess
import logging

from maestro.shared import (
    PROJECT_ROOT, CLAUDE_BIN, ISOLATED_CONFIG, simple_route,
    _extract_plan, build_isolated_env, classify_task_complexity,
)
from maestro.pipeline import (
    PipelineStateMachine, pass_k_verify, select_model,
    resolve_model_name, STAGE_ORDER, TASK_STATES, hard_gate_check,
)
from maestro.context_layer import ContextLayer
from maestro.permission_engine import get_engine
from maestro.coordinator import Coordinator

log = logging.getLogger(__name__)


def _policy_gate(stage: str, output: str, task_text: str,
                 policy, coordinator) -> str | None:
    """策略门：阶段推进前执行 Policy Checkpoint。返回错误消息或 None"""
    task_id = task_text[:60]

    if stage == "plan":
        planned_files = re.findall(r'(?:文件|修改|创建|写入)[：:]\s*([^\s,;；\n]+)', output)
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
    est_tokens = len(output) // 2 + len(task_text) // 4
    ok, msg = policy.check_cost_budget(est_tokens)
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
        handler.send_json({
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
        })
        return True

    from maestro.shared import simple_route
    route_info = simple_route(task)

    if route_info:
        handler.send_json({
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
        })
    else:
        handler.send_json({
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
        })
    return True


def handle_orchestrate(handler, body):
    """POST /api/orchestrate — 智能调度 SSE 流（支持 pipeline 模式）"""
    task = body.get("task", "")
    proj_dir = body.get("proj_dir", "")
    api_key = body.get("api_key", "")
    api_provider = body.get("api_provider", "")
    use_pipeline = body.get("pipeline", False)

    if not task:
        handler.send_json({"error": "请输入要执行的任务描述。智能调度需要一个具体的任务才能完成拆分和分派"})
        return True
    if not CLAUDE_BIN:
        handler.send_json({"error": "Claude CLI not found"})
        return True

    if use_pipeline:
        return _run_pipeline_orchestrate(handler, body)

    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "close")
    handler.end_headers()

    proc = None
    full_output = ""
    start_time = time.time()
    try:
        safe_task = task.replace('\n', ' ').replace('\r', ' ')
        cmd = ["cmd", "/c", CLAUDE_BIN, "-p", safe_task, "--bare", "--permission-mode", "auto", "--agent", "orchestrator"]
        if proj_dir and os.path.isdir(proj_dir):
            cmd += ["--add-dir", proj_dir]

        handler.wfile.write(f"event: phase\ndata: {json.dumps({'msg': '🧠 分析任务…'})}\n\n".encode())
        handler.wfile.flush()

        iso_env = build_isolated_env(api_key, api_provider)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                encoding='utf-8', errors='replace', bufsize=1,
                                cwd=str(PROJECT_ROOT), env=iso_env)
        from maestro.proc_manager import track_proc
        track_proc(proc)
        for line in iter(proc.stdout.readline, ''):
            if not line: break
            stripped = line.rstrip('\n\r')
            if not stripped: continue
            full_output += stripped + "\n"
            try:
                handler.wfile.write(f"data: {json.dumps({'content': stripped + chr(10)})}\n\n".encode())
                handler.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                break

        try: proc.wait(timeout=15)
        except subprocess.TimeoutExpired: pass

        from maestro.models import estimate_cost
        from maestro.web_cost import record_cost
        elapsed = time.time() - start_time
        in_tokens = len(task) // 4
        out_tokens = len(full_output) // 2
        orchestrator_model = "deepseek-v4-pro"
        cost = estimate_cost(orchestrator_model, in_tokens, out_tokens)
        record_cost(PROJECT_ROOT, time.strftime("%Y-%m-%d %H:%M:%S"), orchestrator_model, in_tokens, out_tokens, cost, elapsed, "orchestrator", proj_dir or "")

        plan = _extract_plan(full_output)
        if plan:
            handler.wfile.write(f"event: plan\ndata: {json.dumps(plan, ensure_ascii=False)}\n\n".encode())
            handler.wfile.flush()
        else:
            handler.wfile.write(f"event: done\ndata: {json.dumps({'summary': '调度计划解析失败。可能 AI 返回格式异常，请用更简单的任务描述重试'})}\n\n".encode())
            handler.wfile.flush()
    except Exception as e:
        try:
            handler.wfile.write(f"event: error\ndata: {json.dumps({'msg': str(e)})}\n\n".encode())
            handler.wfile.flush()
        except Exception: pass
    finally:
        if proc:
            from maestro.proc_manager import kill_proc, untrack_proc
            kill_proc(proc)
            untrack_proc(proc)
    return True


def _run_pipeline_orchestrate(handler, body) -> bool:
    """五阶段管线编排 SSE 流"""
    task = body.get("task", "")
    proj_dir = body.get("proj_dir", "")
    api_key = body.get("api_key", "")
    api_provider = body.get("api_provider", "deepseek")
    agent = body.get("force_agent", "")
    max_retries = body.get("max_retries", 2)

    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "close")
    handler.end_headers()

    sm = PipelineStateMachine({"task": task, "agent": agent, "proj_dir": proj_dir})
    task_id = f"pipeline_{int(time.time())}"
    ctx = ContextLayer(task_id, PROJECT_ROOT)
    policy = get_engine()
    coordinator = Coordinator()
    stages_completed = []
    proc = None
    start_time = time.time()
    full_output_all = ""

    def _write_sse(event_type: str, data: dict):
        try:
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
        safe_prompt = prompt.replace('\n', ' ').replace('\r', ' ')
        iso_env = build_isolated_env(api_key, api_provider)
        iso_env["ANTHROPIC_MODEL"] = model_name
        cmd = [
            "cmd", "/c", CLAUDE_BIN, "-p", safe_prompt,
            "--bare", "--permission-mode", perm_mode,
            "--model", model_name,
        ]
        if proj_dir and os.path.isdir(proj_dir):
            cmd += ["--add-dir", proj_dir]
        output = ""
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            encoding='utf-8', errors='replace', bufsize=1,
            cwd=str(PROJECT_ROOT), env=iso_env,
        )
        from maestro.proc_manager import track_proc
        track_proc(proc)
        for line in iter(proc.stdout.readline, ''):
            if not line:
                break
            stripped = line.rstrip('\n\r')
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
        m = re.search(r'```json\s*\n(.*?)\n```', output, re.DOTALL)
        if not m:
            m = re.search(r'\{[^{}]*"files"\s*:\s*\[.*?\][^{}]*\}', output, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1) if '```' in output else m.group(0))
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
            direct_output = _call_claude_stage(
                f"直接执行以下任务（无需研究/计划/审查）：\n\n{task}",
                model_name, perm_mode="auto",
            )
            full_output_all += direct_output
            _write_sse("done", {
                "summary": "⚡ 快速通道完成",
                "stages": ["direct_execute"],
                "elapsed": round(time.time() - start_time, 1),
                "complexity": "trivial",
            })
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

        # 发送初始管道结构
        _write_sse("stage", {
            "stage": "init",
            "status": "active",
            "complexity": complexity,
            "pipeline": [
                {"stage": s, "label": TASK_STATES[s]["exit"],
                 "enter_condition": TASK_STATES[s]["enter"]}
                for s in pipeline_stages
            ],
        })

        for stage in pipeline_stages:
            sm.current_stage = stage
            retry_count = 0

            while retry_count <= max_retries:
                # 通知前端当前阶段
                _write_sse("stage", {
                    "stage": stage,
                    "status": "active",
                    "retry": retry_count,
                })

                # ── gate 阶段特殊处理：不调 Agent，直接硬门控 ──
                if stage == "gate":
                    _write_sse("phase", {"msg": "🛡 硬门控检查中…"})
                    dry_plan = _parse_dry_run_plan(
                        sm.stage_outputs.get("dry_run", "")
                    )
                    gate_ok, gate_reason = hard_gate_check(dry_plan)
                    stage_output = json.dumps({
                        "passed": gate_ok, "reason": gate_reason,
                        "plan": dry_plan,
                    }, ensure_ascii=False)
                    _write_sse("stage", {
                        "stage": "gate",
                        "status": "passed" if gate_ok else "failed",
                        "gate_result": {"passed": gate_ok, "reason": gate_reason},
                    })
                    if not gate_ok:
                        _write_sse("error", {
                            "msg": f"硬门控未通过: {gate_reason}",
                        })
                        sm.fail_stage(gate_reason)
                        stages_completed.append("gate")
                        break  # gate 失败不重试，直接终止管线
                    sm.advance(stage_output)
                    stages_completed.append(stage)
                    _ctx_write_stage(ctx, stage, stage_output)
                    _write_sse("stage", {
                        "stage": stage, "status": "passed",
                        "output": stage_output[:500],
                    })
                    break

                # 选择模型
                model_tier = select_model({"task": task, "agent": agent}, agent)
                model_name = resolve_model_name(model_tier, api_provider)
                _write_sse("stage", {
                    "stage": stage,
                    "status": "active",
                    "model_tier": model_tier,
                    "model_name": model_name,
                })

                # 获取阶段 prompt，注入共享上下文
                prompt = sm.get_current_prompt()
                ctx_summary = ctx.get_context_for_agent(stage)
                if ctx_summary:
                    prompt = prompt + "\n\n---\n## 共享记忆黑板\n" + ctx_summary
                _write_sse("phase", {"msg": f"📋 阶段: {stage} ({model_tier})"})

                # dry_run 阶段：计划模式（只读），其他阶段：自动模式
                perm_mode = "plan" if stage == "dry_run" else "auto"
                if perm_mode == "plan":
                    _write_sse("phase", {"msg": "🔍 只读预演 — 禁止写文件"})

                try:
                    stage_output = _call_claude_stage(prompt, model_name, perm_mode=perm_mode)
                except Exception as e:
                    log.error(f"阶段 {stage} 调用失败: {e}")
                    stage_output = f"[错误] {e}"

                full_output_all += stage_output

                # dry_run 阶段：解析并写入变更计划到 context
                if stage == "dry_run":
                    dry_plan = _parse_dry_run_plan(stage_output)
                    ctx.set_short_term("dry_run_plan", dry_plan)
                    _write_sse("stage", {
                        "stage": "dry_run",
                        "status": "active",
                        "dry_run_plan": {
                            "total_changes": dry_plan.get("total_changes", 0),
                            "file_count": len(dry_plan.get("files", [])),
                        },
                    })

                # review 阶段特殊处理：pass@k 验证（仅 complex 任务启用）
                if stage == "review" and complexity == "complex":
                    _write_sse("phase", {"msg": "🔍 pass@3 轻量验证中…"})
                    pk_ok, pk_results = pass_k_verify(
                        stage_output, task, k=3,
                        api_key=api_key, api_provider=api_provider,
                    )
                    _write_sse("stage", {
                        "stage": "review",
                        "status": "verifying",
                        "pass_k": {
                            "overall": pk_ok,
                            "perspectives": {
                                name: {"passed": r["passed"]}
                                for name, r in pk_results.items()
                            },
                        },
                    })
                    if not pk_ok:
                        fail_details = {
                            name: r["raw"][:200]
                            for name, r in pk_results.items() if not r["passed"]
                        }
                        _write_sse("stage", {
                            "stage": "review",
                            "status": "failed",
                            "reason": f"pass@3 未通过（需 ≥2/3），失败视角: {list(fail_details.keys())}",
                        })
                        sm.fail_stage(f"pass@3 未通过: {fail_details}")
                        sm.rollback()
                        stage = "implement"
                        sm.current_stage = "implement"
                        retry_count += 1
                        continue

                # 检查是否可以推进
                ok, reason = sm.can_advance(stage, stage_output)
                if ok:
                    # ── 策略门：阶段推进前的合规检查 ──
                    gate_fail = _policy_gate(stage, stage_output, task, policy, coordinator)
                    if gate_fail:
                        _write_sse("stage", {"stage": stage, "status": "blocked", "reason": gate_fail})
                        sm.fail_stage(gate_fail)
                        break

                    sm.advance(stage_output)
                    stages_completed.append(stage)
                    # 写入共享记忆黑板
                    _ctx_write_stage(ctx, stage, stage_output)
                    # 记录 coordinator checkpoint
                    _cp_map = {"plan": "plan_approved", "implement": "implement_done", "review": "review_passed"}
                    if stage in _cp_map:
                        try:
                            snapshot = ctx.get_short_term() if hasattr(ctx, "get_short_term") else {}
                        except Exception:
                            snapshot = {}
                        coordinator.save_checkpoint(task_id, _cp_map[stage], snapshot)
                    _write_sse("stage", {
                        "stage": stage,
                        "status": "passed",
                        "output": stage_output[:500],
                    })
                    break  # 进入下一阶段
                else:
                    _write_sse("stage", {
                        "stage": stage,
                        "status": "failed",
                        "reason": reason,
                    })
                    sm.fail_stage(reason)
                    retry_count += 1
                    if retry_count <= max_retries:
                        _write_sse("phase", {
                            "msg": f"⚠ 阶段 {stage} 未通过 ({reason})，重试 {retry_count}/{max_retries}",
                        })
                        sm.rollback()

            if retry_count > max_retries:
                _write_sse("stage", {
                    "stage": stage,
                    "status": "failed",
                    "reason": f"超过最大重试次数 ({max_retries})",
                })
                _write_sse("error", {
                    "msg": f"阶段 {stage} 失败，已重试 {max_retries} 次仍不通过",
                })
                break

        # 记录费用
        from maestro.models import estimate_cost
        from maestro.web_cost import record_cost
        elapsed = time.time() - start_time
        in_tokens = len(task) // 4 + len(full_output_all) // 4
        out_tokens = len(full_output_all) // 2
        pipeline_model = "pipeline-v1"
        cost = estimate_cost(pipeline_model, in_tokens, out_tokens)
        record_cost(
            PROJECT_ROOT, time.strftime("%Y-%m-%d %H:%M:%S"),
            pipeline_model, in_tokens, out_tokens, cost,
            elapsed, "pipeline", proj_dir or "",
        )

        # 积累长期记忆 — 成功的阶段模式写入
        if len(stages_completed) >= 3:
            plan_text = ctx.get_short_term().get("plan", "")
            if plan_text:
                ctx.set_long_term("last_successful_plan", str(plan_text)[:3000])
            ctx.set_long_term(
                "pipeline_patterns",
                json.dumps({"stages": stages_completed, "task_len": len(task)},
                           ensure_ascii=False),
            )

        # 发送完成事件
        _write_sse("done", {
            "summary": f"管线完成: {len(stages_completed)}/{len(STAGE_ORDER)} 阶段通过",
            "stages": stages_completed,
            "elapsed": round(elapsed, 1),
            "cost": round(cost, 6),
        })

    except Exception as e:
        log.error(f"管线编排异常: {e}", exc_info=True)
        try:
            _write_sse("error", {"msg": str(e)})
        except Exception:
            pass
    finally:
        if proc:
            from maestro.proc_manager import kill_proc, untrack_proc
            kill_proc(proc)
            untrack_proc(proc)

    return True
