"""首次配置向导路由"""
import os
import json
from pathlib import Path


def _find_key():
    """
    查找 API Key。
    优先 .env（用户显式配置），.env 无 Key 时视为需重新配置；
    .env 不存在时回退到环境变量（Docker/CI 场景）。
    """
    env_file = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").split("\n"):
            line = line.strip()
            if line.startswith(("ANTHROPIC_AUTH_TOKEN=", "ANTHROPIC_API_KEY=", "DEEPSEEK_API_KEY=")):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    return True
        return False  # .env 存在但无 Key → 允许重新配置
    # .env 不存在 → 回退环境变量
    for k in ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY"):
        if os.environ.get(k):
            return True
    return False


def handle_status(handler, parsed):
    """GET /api/setup/status — 检查是否需要首次配置"""
    has_key = _find_key()
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
            stripped = line.strip()
            # 匹配活跃行或注释行（替换而非追加，防止重复）
            if stripped.startswith(f"{key}=") or stripped.startswith(f"# {key}=") or stripped.startswith(f"#{key}="):
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
            "anthropic": {
                "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
                "ANTHROPIC_MODEL": "claude-sonnet-4-6",
            },
            "openai": {
                "ANTHROPIC_BASE_URL": "https://api.openai.com/v1",
                "ANTHROPIC_MODEL": "gpt-4o",
            },
            "google": {
                "ANTHROPIC_BASE_URL": "https://generativelanguage.googleapis.com/v1beta/openai",
                "ANTHROPIC_MODEL": "gemini-2.5-pro",
            },
            "xai": {
                "ANTHROPIC_BASE_URL": "https://api.x.ai/v1",
                "ANTHROPIC_MODEL": "grok-3",
            },
            "siliconflow": {
                "ANTHROPIC_BASE_URL": "https://api.siliconflow.cn/v1",
                "ANTHROPIC_MODEL": "Pro/deepseek-ai/DeepSeek-V3",
            },
            "qwen": {
                "ANTHROPIC_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "ANTHROPIC_MODEL": "qwen-plus",
            },
            "kimi": {
                "ANTHROPIC_BASE_URL": "https://api.moonshot.cn/v1",
                "ANTHROPIC_MODEL": "moonshot-v1-8k",
            },
            "glm": {
                "ANTHROPIC_BASE_URL": "https://open.bigmodel.cn/api/paas/v4",
                "ANTHROPIC_MODEL": "glm-4-plus",
            },
            "minimax": {
                "ANTHROPIC_BASE_URL": "https://api.minimax.chat/v1",
                "ANTHROPIC_MODEL": "abab7-chat",
            },
            "custom": {},
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
