"""智能调度 + 路由建议 + 五阶段管线"""
import json
import os
import time
import subprocess
import logging

from maestro.shared import PROJECT_ROOT, CLAUDE_BIN, ISOLATED_CONFIG, simple_route, _extract_plan, build_isolated_env
from maestro.pipeline import (
    PipelineStateMachine, pass_k_verify, select_model,
    resolve_model_name, STAGE_ORDER, TASK_STATES,
)

log = logging.getLogger(__name__)


def handle_route(handler, body):
    """POST /api/route — 三级路由建议（关键词+语义+LLM兜底）"""
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

    try:
        # 发送初始管道结构
        _write_sse("stage", {
            "stage": "init",
            "status": "active",
            "pipeline": [
                {"stage": s, "label": TASK_STATES[s]["exit"],
                 "enter_condition": TASK_STATES[s]["enter"]}
                for s in STAGE_ORDER
            ],
        })

        for stage in STAGE_ORDER:
            sm.current_stage = stage
            retry_count = 0

            while retry_count <= max_retries:
                # 通知前端当前阶段
                _write_sse("stage", {
                    "stage": stage,
                    "status": "active",
                    "retry": retry_count,
                })

                # 选择模型
                model_tier = select_model({"task": task, "agent": agent}, agent)
                model_name = resolve_model_name(model_tier, api_provider)
                _write_sse("stage", {
                    "stage": stage,
                    "status": "active",
                    "model_tier": model_tier,
                    "model_name": model_name,
                })

                # 获取阶段 prompt
                prompt = sm.get_current_prompt()
                _write_sse("phase", {"msg": f"📋 阶段: {stage} ({model_tier})"})

                # 调用 Claude
                stage_output = ""
                try:
                    safe_prompt = prompt.replace('\n', ' ').replace('\r', ' ')
                    iso_env = build_isolated_env(api_key, api_provider)
                    iso_env["ANTHROPIC_MODEL"] = model_name

                    cmd = [
                        "cmd", "/c", CLAUDE_BIN, "-p", safe_prompt,
                        "--bare", "--permission-mode", "auto",
                        "--model", model_name,
                    ]
                    if proj_dir and os.path.isdir(proj_dir):
                        cmd += ["--add-dir", proj_dir]

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
                        stage_output += stripped + "\n"
                        _write_sse("", {"content": stripped + chr(10)})

                    try:
                        proc.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        pass
                except Exception as e:
                    log.error(f"阶段 {stage} 调用失败: {e}")
                    stage_output = f"[错误] {e}"
                finally:
                    if proc:
                        from maestro.proc_manager import kill_proc, untrack_proc
                        kill_proc(proc)
                        untrack_proc(proc)
                        proc = None

                full_output_all += stage_output

                # review 阶段特殊处理：pass@k 验证
                if stage == "review":
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
                        # 回退到 implement 阶段
                        stage = "implement"
                        sm.current_stage = "implement"
                        retry_count += 1
                        continue

                # 检查是否可以推进
                ok, reason = sm.can_advance(stage, stage_output)
                if ok:
                    sm.advance(stage_output)
                    stages_completed.append(stage)
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
