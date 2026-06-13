"""通用 Webhook — 外部服务调用 Agent"""

import json
import os
import time
import subprocess
import logging
from pathlib import Path
from urllib.parse import urlparse

log = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def handle_webhook(handler, body):
    """POST /api/webhook/:channel — 外部服务触发 Agent"""
    # 认证检查
    token = handler.headers.get("Authorization", "").replace("Bearer ", "").strip()
    expected = os.environ.get("AGENCY_AUTH_TOKEN", "")
    if expected:
        if token != expected:
            handler.send_json({"ok": False, "error": "未授权"}, 401)
            return True
    else:
        client_ip = handler.client_address[0] if handler.client_address else ""
        if client_ip not in ("127.0.0.1", "::1", "localhost"):
            handler.send_json({"ok": False, "error": "未授权"}, 401)
            return True

    path = urlparse(handler.path).path
    channel = path[len("/api/webhook/") :] if path.startswith("/api/webhook/") else "generic"

    message = body.get("message", body.get("text", body.get("task", "")))
    if not message:
        handler.send_json({"error": "缺少必填字段 message。请在请求体中提供要发送的消息内容"}, 400)
        return True

    from maestro.shared import CLAUDE_BIN, build_isolated_env

    # 会话复用
    session_id = body.get("session_id", "")
    api_key = body.get("api_key", "")
    api_provider = body.get("api_provider", "")

    # SSE
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "close")
    handler.end_headers()

    start_time = time.time()
    proc = None
    full_output = ""
    try:
        cmd = [CLAUDE_BIN, "-p", message, "--bare", "--permission-mode", "auto"]
        if session_id:
            cmd += ["--session-id", session_id]

        handler.wfile.write(
            f"event: meta\ndata: {json.dumps({'channel': channel, 'session': session_id[:8] if session_id else 'new'})}\n\n".encode()
        )
        handler.wfile.flush()

        iso_env = build_isolated_env(api_key, api_provider)
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=str(PROJECT_ROOT),
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
                handler.wfile.write(
                    f"data: {json.dumps({'content': stripped + chr(10)}, ensure_ascii=False)}\n\n".encode()
                )
                handler.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                break

        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            log.warning("webhook proc wait timeout")

        # 费用记录
        elapsed = time.time() - start_time
        try:
            handler.wfile.write(
                f"event: done\ndata: {json.dumps({'elapsed': elapsed})}\n\n".encode()
            )
            handler.wfile.flush()
        except Exception as e:
            log.warning(f"webhook SSE write error: {e}")

    except Exception as e:
        try:
            handler.wfile.write(f"data: {json.dumps({'error': str(e)})}\n\n".encode())
            handler.wfile.flush()
        except Exception as e2:
            log.warning(f"webhook SSE error write error: {e2}")
    finally:
        if proc:
            from maestro.proc_manager import kill_proc, untrack_proc

            kill_proc(proc)
            untrack_proc(proc)
    return True
