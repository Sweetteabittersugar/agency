"""健康检查端点"""
import time

_boot = time.time()


def handle_health(handler, parsed):
    handler.send_json({
        "status": "ok",
        "uptime": round(time.time() - _boot, 1),
        "version": "0.1.0",
        "active_procs": 0,
    })
    return True
