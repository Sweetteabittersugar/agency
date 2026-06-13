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

    # 自动检测模式：Flask 模式重启 flask_app.py，legacy 模式重启 web.py
    maestro_dir = os.path.dirname(os.path.dirname(__file__))
    if os.environ.get("AGENCY_USE_LEGACY") == "1":
        script = os.path.join(maestro_dir, "web.py")
    else:
        script = os.path.join(maestro_dir, "flask_app.py")
    subprocess.Popen(
        [sys.executable, script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=os.path.dirname(os.path.dirname(script)),
    )
    # 当前进程退出
    os._exit(0)
    return True
