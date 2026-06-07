"""远端访问模块 — 认证 + IP 检测 + 启动信息"""
import os
import socket
import logging

log = logging.getLogger(__name__)

# 从环境变量读取配置
AUTH_TOKEN = os.environ.get("AGENCY_TOKEN", "")
BIND_ADDR = os.environ.get("AGENCY_BIND", "127.0.0.1")
PORT = int(os.environ.get("AGENCY_PORT", "8800"))


def check_auth(headers):
    """验证请求的 Authorization header。返回 (ok, error_msg)"""
    if not AUTH_TOKEN:
        return True, ""  # 未配置 token，不校验

    auth = headers.get("Authorization", "")
    if not auth:
        return False, "未提供认证令牌"

    # 支持 Bearer token 和直接 token
    if auth.startswith("Bearer "):
        token = auth[7:]
    else:
        token = auth

    if token != AUTH_TOKEN:
        return False, "认证令牌无效"

    return True, ""


def get_local_ip():
    """获取本机局域网 IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def startup_info():
    """打印远程连接信息"""
    is_remote = BIND_ADDR != "127.0.0.1"
    auth_on = bool(AUTH_TOKEN)

    lines = []
    if is_remote:
        local_ip = get_local_ip()
        lines.append(f"  远程模式: http://{local_ip}:{PORT}")
        lines.append(f"  本地访问: http://127.0.0.1:{PORT}")
    else:
        lines.append(f"  http://localhost:{PORT}")

    if auth_on:
        lines.append(f"  认证: 已启用 (Bearer token)")
    else:
        if is_remote:
            lines.append(f"  ⚠ 认证: 未启用 (建议设置 AGENCY_TOKEN)")
        else:
            lines.append(f"  认证: 关闭 (本地模式)")

    return "\n".join(lines)
