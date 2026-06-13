"""远端访问模块 — 认证/IP检测/运行时配置（不重启生效）"""

import os
import socket
import secrets
import logging
from pathlib import Path

log = logging.getLogger(__name__)

from maestro.app_config import (
    PORT,
    BIND_ADDR,
)  # 默认仅本机，远端需设 AGENCY_HOST=0.0.0.0 + AGENCY_TOKEN

# 内存中的 token（None=未初始化，\"\"=已显式关闭，其他=密码）
_token = None


def _load_env_token():
    """从 .env 加载 token，首次启动自动生成"""
    global _token
    if _token is not None:
        return
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").split("\n"):
            line = line.strip()
            if line.startswith("AGENCY_TOKEN="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    _token = val
                    break
                else:
                    _token = ""  # 显式设为空=已关闭
                    break
    # 环境变量覆盖
    if _token is None:
        _token = os.environ.get("AGENCY_TOKEN", "")
    # 首次启动自动生成 token（远端访问强制要求）
    if not _token and _token is not None:
        # 显式设为空 — 但如果远端访问，强制生成
        if BIND_ADDR not in ("127.0.0.1", "::1", "localhost"):
            _token = generate_token()
            _save_env_token(_token)
            log.warning(f"远端访问模式 (AGENCY_HOST={BIND_ADDR})，已强制生成认证令牌")
    elif not _token:
        _token = generate_token()
        _save_env_token(_token)
        log.info("Auto-generated remote token (see .env or startup log)")

    # 统一：None → ""
    if _token is None:
        _token = ""


def _save_env_token(token: str):
    """将 token 持久化到 .env"""
    env_file = Path(__file__).resolve().parent.parent / ".env"
    lines = []
    found = False
    if env_file.exists():
        lines = env_file.read_text(encoding="utf-8").split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if (
                stripped.startswith("AGENCY_TOKEN=")
                or stripped.startswith("# AGENCY_TOKEN=")
                or stripped.startswith("#AGENCY_TOKEN=")
            ):
                lines[i] = f"AGENCY_TOKEN={token}"
                found = True
                break
    if not found:
        lines.append(f"AGENCY_TOKEN={token}")
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_token():
    """生成随机 token"""
    return secrets.token_urlsafe(16)


def get_token():
    """获取当前 token（首次调用时从 .env 加载）"""
    global _token
    if _token is None:
        _load_env_token()
    return _token or ""


def set_token(token: str):
    """运行时设置 token — 即时生效 + 持久化"""
    global _token
    _token = token or ""
    _save_env_token(token or "")
    if token:
        log.info(f"Remote token updated (len={len(token)})")


def clear_token():
    """关闭远端认证"""
    global _token
    _token = ""
    _save_env_token("")
    os.environ.pop("AGENCY_TOKEN", None)
    log.info("Remote auth disabled")


def check_auth(headers):
    """验证请求。返回 (ok, error_msg)"""
    token = get_token()
    if not token:
        if BIND_ADDR in ("127.0.0.1", "::1", "localhost"):
            return True, ""
        return False, "远端访问需要配置 AGENCY_TOKEN，请在 .env 中设置或通过 Web 设置页生成令牌"

    auth = headers.get("Authorization", "")
    if not auth:
        return False, "请提供访问令牌"

    if auth.startswith("Bearer "):
        auth = auth[7:]

    if auth != token:
        return False, "令牌无效"

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


def is_remote_enabled():
    """远端功能是否启用（有 token = 启用）"""
    return bool(get_token())


def startup_info():
    """打印启动连接信息"""
    token = get_token()
    local_ip = get_local_ip()

    lines = []
    lines.append(f"  本地: http://localhost:{PORT}")
    lines.append(f"  远端: http://{local_ip}:{PORT}")
    if token:
        lines.append("  认证: 已启用")
    else:
        lines.append("  认证: 关闭")
    return "\n".join(lines)
