#!/usr/bin/env python3
"""
Agency — Claude Code Web 前端
  python maestro/web.py   →   http://localhost:8800
"""
import os, sys, json, time, threading, subprocess, logging
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── 隔离配置同步 ──
from maestro.settings_sync import sync_isolated_config
sync_isolated_config(PROJECT_ROOT)

# ── 加载 .env ──
from maestro.env_loader import load_dotenv
load_dotenv(PROJECT_ROOT)

# ── 远端访问配置 ──
from maestro.remote import BIND_ADDR, PORT, check_auth, startup_info, get_token

# ── 诊断日志 ──
logging.basicConfig(
    level=getattr(logging, os.environ.get("AGENCY_LOG_LEVEL", "INFO").upper(), logging.INFO),
    format='%(asctime)s [%(thread)d] %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(str(PROJECT_ROOT / 'maestro' / 'agency.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stderr),
    ]
)
log = logging.getLogger('agency')

# ── 共享状态（从 shared.py 导入，避免循环依赖）──
from maestro.shared import (
    PROJECT_ROOT, ISOLATED_CONFIG, _claude_dir, AGENCY_VERSION, CLAUDE_BIN,
    load_agents, simple_route, _extract_plan, _scan_subagents,
)
# 修正 PROJECT_ROOT（shared.py 在其自己的目录上下文计算）
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── 费用估算 ──
from maestro.models import estimate_cost

# ── Harness 模块 ──
from maestro.harness.watcher import bus
from maestro.harness.hooks_receiver import handle_hook_callback

# ── 权限日志 ──
_permission_log = []
_permission_log_lock = threading.Lock()

def record_permission(tool_name, decision, risk, reason=""):
    entry = {"time": time.strftime("%H:%M:%S"), "tool": tool_name, "decision": decision, "risk": risk, "reason": reason}
    with _permission_log_lock:
        _permission_log.append(entry)
        if len(_permission_log) > 200:
            _permission_log[:] = _permission_log[-200:]

def get_permission_stats():
    with _permission_log_lock:
        total = len(_permission_log)
        allowed = sum(1 for e in _permission_log if e["decision"] == "allow")
        denied = sum(1 for e in _permission_log if e["decision"] == "deny")
        blocked = sum(1 for e in _permission_log if e["decision"] == "block")
    return {"total": total, "allowed": allowed, "denied": denied, "blocked": blocked}

# ── 子进程清理 ──
from maestro.proc_manager import cleanup_all_procs


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """多线程 HTTP Server"""
    daemon_threads = True
    request_queue_size = 32


class Handler(BaseHTTPRequestHandler):
    """请求处理器 — 路由分发到各路模块"""

    def _check_auth(self):
        """API 请求认证检查。静态文件/localhost/remote端点 放行"""
        path = urlparse(self.path).path
        if not path.startswith("/api/"):
            return True
        # localhost 上的请求免认证（本机用户可随时改配置）
        client_ip = self.client_address[0] if self.client_address else ""
        if client_ip in ("127.0.0.1", "::1", "localhost"):
            return True
        ok, msg = check_auth(self.headers)
        if not ok:
            self.send_json({"error": msg}, 401)
        return ok

    def do_GET(self):
        if not self._check_auth():
            return
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            from maestro.routes.static import handle_index
            handle_index(self, parsed)
            return

        if not path.startswith("/api/"):
            from maestro.routes.static import serve_static
            if serve_static(self, path):
                return

        for prefix, handler_func in self._get_routes:
            if path == prefix or (prefix.endswith("/") and len(path) > len(prefix) and path.startswith(prefix)):
                handler_func(self, parsed)
                return

        self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        if not self._check_auth():
            return
        length = int(self.headers.get("Content-Length", 0))
        body = {}
        if length > 0:
            ct = self.headers.get("Content-Type", "")
            if not ct.startswith("application/json"):
                self.send_json({"error": "需要 JSON 格式"}, 400)
                return
            raw = self.rfile.read(length)
            # 尝试 UTF-8 → GBK → latin-1 三种编码
            for enc in ('utf-8', 'gbk', 'latin-1'):
                try:
                    body = json.loads(raw.decode(enc))
                    break
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
            else:
                self.send_json({"error": "invalid JSON body"}, 400)
                return
        from maestro.safety import check_input, check_rate_limit
        if not check_rate_limit(self.client_address[0]):
            self.send_json({"error": "请求过于频繁"}, 429)
            return
        user_text = body.get("task", body.get("message", body.get("text", "")))
        if user_text:
            is_safe, reason = check_input(user_text)
            if not is_safe:
                self.send_json({"error": f"不安全: {reason}"}, 400)
                return

        path = urlparse(self.path).path
        skip_csrf = path in ("/api/setup", "/api/setup/status", "/api/route", "/api/remote/status", "/api/health", "/api/version")
        if not skip_csrf:
            origin = self.headers.get("Origin", "")
            if origin:
                from urllib.parse import urlparse as up
                oh = up(origin).hostname or ""
                if oh and oh not in ("127.0.0.1", "localhost", "::1"):
                    self.send_json({"error": "CSRF: invalid origin"}, 403)
                    return

        for prefix, handler_func in self._post_routes:
            if path == prefix or (prefix.endswith("/") and len(path) > len(prefix) and path.startswith(prefix)):
                handler_func(self, body)
                return

        self.send_json({"error": "not found"}, 404)

    def send_json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        pass


# ── 注册路由 ──
from maestro.routes import register_all
register_all(Handler)


# ═══════════════════════════════════════
# Startup
# ═══════════════════════════════════════
def _kill_old():
    try:
        subprocess.run(
            f'powershell -Command "'
            f'$pids = (Get-NetTCPConnection -LocalPort {PORT} -ErrorAction SilentlyContinue |'
            f' Select-Object -ExpandProperty OwningProcess | Sort-Object -Unique);'
            f' foreach ($p in $pids) {{ if ($p -ne $pid) {{ Stop-Process -Id $p -Force }} }}"',
            shell=True, capture_output=True, timeout=10
        )
    except Exception:
        log.debug("Failed to kill old process on port 8800", exc_info=True)

if __name__ == "__main__":
    import webbrowser, socket
    _kill_old()
    httpd = ThreadingHTTPServer((BIND_ADDR, PORT), Handler)
    httpd.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    httpd.timeout = 30
    # 仅本地模式自动打开浏览器
    if BIND_ADDR == "127.0.0.1":
        threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    print(f"\n  Agency v{AGENCY_VERSION}  [多线程模式]")
    print(startup_info())
    print(f"  Claude Code config: {_claude_dir}\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        cleanup_all_procs()
        httpd.shutdown()
