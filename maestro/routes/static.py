"""静态文件 + 首页路由"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def handle_index(handler, parsed):
    """GET / — 返回 index.html"""
    html_path = PROJECT_ROOT / "webui" / "index.html"
    if html_path.exists():
        handler.send_response(200)
        handler.send_header("Content-Type", "text/html; charset=utf-8")
        handler.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        handler.send_header("X-Content-Type-Options", "nosniff")
        handler.send_header("X-Frame-Options", "DENY")
        handler.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; font-src https://fonts.gstatic.com; img-src 'self' data:",
        )
        handler.end_headers()
        handler.wfile.write(html_path.read_bytes())
    else:
        handler.send_response(200)
        handler.send_header("Content-Type", "text/html; charset=utf-8")
        handler.send_header("X-Content-Type-Options", "nosniff")
        handler.send_header("X-Frame-Options", "DENY")
        handler.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; font-src https://fonts.gstatic.com; img-src 'self' data:",
        )
        handler.end_headers()
        handler.wfile.write(b"<h1>Agency</h1><p>webui/index.html not found.</p>")
    return True


def serve_static(handler, path):
    """静态文件 — 防路径穿越。返回 True 表示已处理"""
    webui_root = (PROJECT_ROOT / "webui").resolve()
    try:
        static_path = (PROJECT_ROOT / "webui" / path.lstrip("/")).resolve()
        static_path.relative_to(webui_root)
    except ValueError:
        return False
    if static_path.exists() and static_path.is_file():
        ct = "text/html"
        if path.endswith(".css"):
            ct = "text/css"
        elif path.endswith(".js"):
            ct = "application/javascript"
        elif path.endswith(".svg"):
            ct = "image/svg+xml"
        elif path.endswith(".png"):
            ct = "image/png"
        handler.send_response(200)
        handler.send_header("Content-Type", ct)
        handler.send_header("Cache-Control", "no-cache")
        handler.send_header("X-Content-Type-Options", "nosniff")
        handler.send_header("X-Frame-Options", "DENY")
        handler.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self' ws: wss:",
        )
        handler.end_headers()
        handler.wfile.write(static_path.read_bytes())
        return True
    return False
