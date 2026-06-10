"""健康检查端点"""
import sys
import time
import subprocess

_boot = time.time()


def _count_active_procs():
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=5)
            return len([l for l in result.stdout.strip().split('\n') if l.strip()])
        else:
            result = subprocess.run(
                ["ps", "aux"], capture_output=True, text=True, timeout=5)
            return len([l for l in result.stdout.strip().split('\n') if 'python' in l])
    except Exception:
        return -1


def handle_health(handler, parsed):
    handler.send_json({
        "status": "ok",
        "uptime": round(time.time() - _boot, 1),
        "version": "0.1.0",
        "active_procs": _count_active_procs(),
    })
    return True
