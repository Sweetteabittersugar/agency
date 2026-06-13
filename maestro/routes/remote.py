"""远端访问路由 — 配置 + 状态"""

from maestro.remote import (
    get_token,
    set_token,
    clear_token,
    generate_token,
    get_local_ip,
    is_remote_enabled,
    PORT,
)


def handle_status(handler, parsed):
    """GET /api/remote/status — 获取远端状态"""
    handler.send_json(
        {
            "enabled": is_remote_enabled(),
            "has_token": bool(get_token()),
            "ip": get_local_ip(),
            "port": PORT,
            "url": f"http://{get_local_ip()}:{PORT}" if is_remote_enabled() else "",
        }
    )
    return True


def handle_config(handler, body):
    """POST /api/remote/config — 配置远端访问"""
    enabled = body.get("enabled", False)
    custom_token = body.get("token", "")

    if enabled:
        token = custom_token or generate_token()
        set_token(token)
        handler.send_json(
            {
                "ok": True,
                "enabled": True,
                "token": token,
                "url": f"http://{get_local_ip()}:{PORT}",
            }
        )
    else:
        clear_token()
        handler.send_json(
            {
                "ok": True,
                "enabled": False,
            }
        )
    return True
