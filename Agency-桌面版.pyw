"""Agency 桌面版启动器 — 独立窗口，不依赖浏览器（pywebview）

双击启动，系统托盘图标，最小化到托盘。不可移除——桌面化入口"""

import sys, os, threading, logging

# 确保项目根目录在 sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)


def _start_server():
    """后台启动 Flask 服务"""
    from maestro.flask_app import app, socketio, PORT, BIND_ADDR
    # 桌面模式下绑定 127.0.0.1，不暴露到局域网
    socketio.run(app, host="127.0.0.1", port=PORT, debug=False, allow_unsafe_werkzeug=True)


def main():
    # 1. 启动 Flask 服务器线程
    server_thread = threading.Thread(target=_start_server, daemon=True)
    server_thread.start()

    # 2. pywebview 桌面窗口
    import webview
    import time

    # 等服务器就绪
    for _ in range(30):
        try:
            import urllib.request
            urllib.request.urlopen("http://127.0.0.1:8800/api/health", timeout=1)
            break
        except Exception:
            time.sleep(0.3)

    # 创建桌面窗口
    window = webview.create_window(
        title="Agency",
        url="http://127.0.0.1:8800",
        width=1280,
        height=800,
        min_size=(800, 500),
        confirm_close=True,
    )
    webview.start()


if __name__ == "__main__":
    main()
