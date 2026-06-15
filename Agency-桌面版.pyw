#!/usr/bin/env python3
"""Agency Desktop Launcher.

Detects whether WebView2 is available. If yes, opens standalone window.
If no, opens in default browser immediately (no black window).
"""

import sys, os, time, threading, webbrowser

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
SERVER_PORT = 8800
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"


def _webview2_available():
    """Check if Edge WebView2 runtime is actually installed."""
    import glob as _glob
    paths = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\EdgeWebView\Application\*\msedgewebview2.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\EdgeWebView\Application\*\msedgewebview2.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\EdgeWebView\Application\*\msedgewebview2.exe"),
        # Also check Edge's own bundled WebView2
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\*\msedgewebview2.exe"),
    ]
    for pat in paths:
        matches = _glob.glob(pat)
        if matches:
            return True
    return False


def _server_running():
    import urllib.request
    try:
        return urllib.request.urlopen(f"{SERVER_URL}/api/health", timeout=1).status == 200
    except Exception:
        return False


def _start_server():
    if _server_running():
        return
    try:
        from maestro.flask_app import app, socketio
        socketio.run(app, host="127.0.0.1", port=SERVER_PORT,
                     debug=False, allow_unsafe_werkzeug=True)
    except OSError:
        pass


def main():
    # Start server if needed
    if not _server_running():
        threading.Thread(target=_start_server, daemon=True).start()
        # Brief wait for server to come up
        for _ in range(20):
            time.sleep(0.3)
            if _server_running():
                break

    # Decide: pywebview or browser?
    if _webview2_available():
        # Standalone window path
        import webview
        window = webview.create_window(
            title="Agency", url=SERVER_URL,
            width=1280, height=800, min_size=(800, 500),
            confirm_close=True,
        )
        webview.start()
    else:
        # Browser fallback — works everywhere, always
        webbrowser.open(SERVER_URL)


if __name__ == "__main__":
    main()
