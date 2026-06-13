"""健康检查端点"""

import sys
import time
import subprocess
from pathlib import Path

_boot = time.time()

_version_file = Path(__file__).resolve().parent.parent.parent / "VERSION"
_version = _version_file.read_text().strip() if _version_file.exists() else "unknown"


def _count_active_procs():
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return len([l for l in result.stdout.strip().split("\n") if l.strip()])
        else:
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
            return len([l for l in result.stdout.strip().split("\n") if "python" in l])
    except Exception:
        return -1


def handle_health(handler, parsed):
    handler.send_json(
        {
            "status": "ok",
            "uptime": round(time.time() - _boot, 1),
            "version": _version,
            "active_procs": _count_active_procs(),
        }
    )
    return True
