"""首次配置向导路由"""
import os
import json
from pathlib import Path


def handle_status(handler, parsed):
    """GET /api/setup/status — 检查是否需要首次配置"""
    has_key = bool(
        os.environ.get("ANTHROPIC_AUTH_TOKEN") or
        os.environ.get("ANTHROPIC_API_KEY") or
        os.environ.get("DEEPSEEK_API_KEY")
    )
    from maestro.remote import is_remote_enabled, get_local_ip, PORT
    needs_setup = not has_key
    handler.send_json({
        "needs_setup": needs_setup,
        "has_key": has_key,
        "remote_enabled": is_remote_enabled(),
        "remote_url": f"http://{get_local_ip()}:{PORT}" if is_remote_enabled() else "",
    })
    return True


def handle_save(handler, body):
    """POST /api/setup — 保存首次配置"""
    env_file = Path(__file__).resolve().parent.parent.parent / ".env"
    lines = []
    if env_file.exists():
        lines = [l.rstrip("\n") for l in env_file.read_text(encoding="utf-8").split("\n")]

    def set_env(key, value):
        nonlocal lines
        if not value:
            return
        found = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):
                lines[i] = f"{key}={value}"
                found = True
                break
        if not found:
            lines.append(f"{key}={value}")

    # API Key 配置
    api_key = body.get("api_key", "")
    api_provider = body.get("api_provider", "deepseek")
    if api_key:
        set_env("ANTHROPIC_AUTH_TOKEN", api_key)
        provider_map = {
            "deepseek": {
                "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
                "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-v4-pro",
                "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek-v4-flash",
                "ANTHROPIC_MODEL": "deepseek-v4-pro",
            },
            "anthropic": {},
            "openai": {"ANTHROPIC_BASE_URL": "https://api.openai.com/v1"},
        }
        for k, v in provider_map.get(api_provider, provider_map["deepseek"]).items():
            set_env(k, v)

    # 远端配置
    remote_enabled = body.get("remote_enabled", False)
    remote_token = body.get("remote_token", "")
    if remote_enabled:
        from maestro.remote import set_token, generate_token
        token = remote_token or generate_token()
        set_token(token)
    # 不处理 remote_enabled=false，因为默认就是关闭

    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    handler.send_json({
        "ok": True,
        "restart_needed": api_key and True,  # API key 需要重启才能加载到环境变量
    })
    return True
