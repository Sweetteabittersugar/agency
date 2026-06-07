"""服务重启路由"""
import os
import sys
import subprocess
import logging

log = logging.getLogger(__name__)


def handle_restart(handler, body):
    """POST /api/restart — 重启 web 服务"""
    handler.send_json({"ok": True, "msg": "正在重启…"})
    handler.wfile.flush()

    # 启动新进程
    script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web.py")
    subprocess.Popen(
        [sys.executable, script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=os.path.dirname(os.path.dirname(script)),
    )
    # 当前进程退出
    os._exit(0)
    return True
