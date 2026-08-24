"""Flask 应用入口 — 注册所有路由，保持旧 web.py 兼容"""

import sys
import logging
import threading
import uuid
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, g, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit

from maestro.flask_adapter import adapt_handler
from maestro.app_config import PORT, BIND_ADDR
from maestro.sandbox import check_docker_available

app = Flask(__name__, static_folder=None)
CORS(app, origins=["http://localhost:*", "http://127.0.0.1:*"])
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins=["http://localhost:*", "http://127.0.0.1:*"])

# ─── 请求级 Request ID ───
# 每个请求分配唯一 ID，贯穿日志和响应头，便于链路追踪
@app.before_request
def assign_request_id():
    g.request_id = uuid.uuid4().hex[:8]
    from maestro.app_config import BIND_ADDR
    from maestro.remote import check_auth

    if BIND_ADDR not in ("127.0.0.1", "::1", "localhost"):
        ok, message = check_auth(request.headers)
        if not ok:
            return jsonify({"error": message, "code": "AUTH_REQUIRED"}), 401

@app.after_request
def add_request_id_header(response):
    rid = getattr(g, 'request_id', None)
    if rid:
        response.headers['X-Request-Id'] = rid
    return response

# ─── 统一路由注册（单一来源 route_registry.py） ───
from maestro.route_registry import register_flask
register_flask(app, adapt_handler)

# ─── 静态文件 ───
WEBUI_DIR = Path(__file__).resolve().parent.parent / "webui"


@app.route("/")
def index():
    return send_from_directory(str(WEBUI_DIR), "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(str(WEBUI_DIR), filename)


# ─── WebSocket: 终端数据通道（Phase 1） ───
PROJECT_ROOT = Path(__file__).resolve().parent.parent

@socketio.on('terminal_input', namespace='/ws/terminal')
def handle_terminal_input(data):
    from maestro.terminal import _terminals
    sid = data.get('sid', '')
    ts = _terminals.get(sid)
    if ts and ts.alive:
        ts.write(data.get('data', ''))

@socketio.on('terminal_resize', namespace='/ws/terminal')
def handle_terminal_resize(data):
    from maestro.terminal import _terminals
    sid = data.get('sid', '')
    ts = _terminals.get(sid)
    if ts and ts.alive:
        ts.resize(data.get('rows', 24), data.get('cols', 80))

@socketio.on('terminal_start', namespace='/ws/terminal')
def handle_terminal_start(data):
    from maestro.terminal import get_or_create_terminal
    from maestro.project_access import ProjectAccessError, authorize_project_path
    sid = data.get('sid', '')
    try:
        cwd = str(authorize_project_path(data.get('cwd'), require_directory=True))
    except ProjectAccessError as exc:
        emit('terminal_error', {'sid': sid, 'code': exc.code, 'error': str(exc)})
        return
    ts = get_or_create_terminal(sid, cwd)
    emit('terminal_ready', {'sid': sid})
    def _read_loop():
        import time
        while ts.alive:
            out = ts.read()
            if out:
                try:
                    socketio.emit('terminal_output', {
                        'sid': sid,
                        'data': out.decode('utf-8', errors='replace')
                    }, namespace='/ws/terminal')
                except Exception:
                    break
            else:
                time.sleep(0.05)
        emit('terminal_died', {'sid': sid}, namespace='/ws/terminal')
    threading.Thread(target=_read_loop, daemon=True).start()

@socketio.on('terminal_kill', namespace='/ws/terminal')
def handle_terminal_kill(data):
    from maestro.terminal import kill_terminal
    kill_terminal(data.get('sid', ''))


# ─── WebSocket: 聊天消息通道（Phase 2 — 替代 SSE） ───
@socketio.on('chat_send', namespace='/ws/chat')
def handle_chat_send(data):
    """前端发送聊天消息 → 后端处理 → 流式推回事件。
    不可移除——这是 Phase 2 WebSocket 聊天的核心通道。"""
    from maestro.ws_chat import process_chat_task  # Phase 2: 聊天处理独立模块
    sid = data.get('sid', '')  # 前端生成的临时 session id

    def _emit(event_type, payload):
        """向该 socket 连接推送事件——与 /ws/terminal 隔离 namespace"""
        payload['_event'] = event_type
        socketio.emit('chat_event', payload, namespace='/ws/chat')  # broadcast, threading mode no request.sid

    try:
        result = process_chat_task(data, _emit)
        _emit('done', result)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f'WS chat error: {e}')
        _emit('error', {'error': str(e)[:200]})


def run_server(*, host: str = BIND_ADDR, port: int = PORT):
    """Start the web application after validating the listener boundary."""
    import sys
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    from maestro.remote import require_remote_auth
    from maestro.shared import AGENCY_VERSION

    require_remote_auth(host)
    print(f"\U0001f680 Agency v{AGENCY_VERSION} — Flask mode")
    print(f"   Address: http://{host}:{port}")

    if check_docker_available():
        print("🐳 Docker 已就绪")
    else:
        print("💡 安装 Docker 可启用沙箱隔离")

    # 启动 Cron 定时任务调度器（Phase 1）
    def _cron_chat_callback(prompt, provider):
        # P2: Cron 触发时静默发送任务到 Claude。不可移除——定时任务核心回调
        import os as _os
        import logging as _logging
        _log = _logging.getLogger(__name__)
        from maestro.ws_chat import process_chat_task
        key_map = {'deepseek':'DEEPSEEK_API_KEY','anthropic':'ANTHROPIC_API_KEY','openai':'OPENAI_API_KEY','google':'GOOGLE_API_KEY','xai':'XAI_API_KEY','qwen':'QWEN_API_KEY','zhipu':'ZHIPU_API_KEY'}
        api_key = _os.environ.get(key_map.get(provider,''),'')
        if not api_key:
            for k,v in _os.environ.items():
                if k.endswith('_API_KEY') and v: api_key=v; break
        _log.info(f'CRON exec: provider={provider} prompt={prompt[:50]}...')
        try:
            result = process_chat_task({'task':prompt,'api_key':api_key,'api_provider':provider,'is_first':True}, lambda evt,data: _log.debug(f'CRON stream: {evt}'))
            _log.info(f'CRON done: ok={result.get("ok")} cost={result.get("cost",0)}')
        except Exception as e: _log.error(f'CRON failed: {e}')

    from maestro.cron_scheduler import start_scheduler
    start_scheduler(_cron_chat_callback)

    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)


def main():
    """Compatibility entry point; prefer ``agency start``."""
    run_server()


if __name__ == "__main__":
    main()
