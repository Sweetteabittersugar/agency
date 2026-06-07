"""智能调度 + 路由建议"""
import json
import os
import time
import subprocess
import logging

from maestro.shared import PROJECT_ROOT, CLAUDE_BIN, ISOLATED_CONFIG, simple_route, _extract_plan, build_isolated_env

log = logging.getLogger(__name__)


def handle_route(handler, body):
    """POST /api/route — 关键词路由建议"""
    task = body.get("task", "")
    route_info = simple_route(task)
    if route_info:
        handler.send_json({"agent": route_info["agent"], "model": route_info["model"], "method": "keyword"})
    else:
        handler.send_json({"agent": "coder", "model": "", "method": "keyword"})
    return True


def handle_orchestrate(handler, body):
    """POST /api/orchestrate — 智能调度 SSE 流"""
    task = body.get("task", "")
    proj_dir = body.get("proj_dir", "")
    api_key = body.get("api_key", "")
    api_provider = body.get("api_provider", "")
    if not task:
        handler.send_json({"error": "task required"})
        return True
    if not CLAUDE_BIN:
        handler.send_json({"error": "Claude CLI not found"})
        return True

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
            handler.wfile.write(f"event: done\ndata: {json.dumps({'summary': '无法解析调度计划'})}\n\n".encode())
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
