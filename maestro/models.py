#!/usr/bin/env python3
"""
Model System v3 --- 多级模型映射 + 自动降级 + 主流模型预设

Agent frontmatter 中的 model 字段是"能力级别"：
  haiku  → 轻量级（简单搜索、费用分析）
  sonnet → 标准级（代码编写、审查、规划）
  opus   → 重量级（复杂推理、深度创作）

用户配置具体模型，支持自动降级：配了重型用重型，没配自动用标准，标准也没配用轻量。
"""

import os

# === 主流模型预设（用户只需选 provider） ===

PROVIDER_PRESETS = {
    "deepseek": {
        "heavy": "deepseek-v4-pro",
        "standard": "deepseek-v4-pro",
        "light": "deepseek-v4-flash",
        "base_url": "https://api.deepseek.com",
    },
    "openai": {
        "heavy": "gpt-4o",
        "standard": "gpt-4o-mini",
        "light": "gpt-4o-mini",
        "base_url": "https://api.openai.com/v1",
    },
    "anthropic": {
        "heavy": "claude-opus-4-8",
        "standard": "claude-sonnet-4-6",
        "light": "claude-haiku-4-5",
        "base_url": "https://api.anthropic.com/v1",
    },
    "gemini": {
        "heavy": "gemini-2.5-pro",
        "standard": "gemini-2.5-flash",
        "light": "gemini-2.5-flash-lite",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
    },
    "qwen": {
        "heavy": "qwen-max",
        "standard": "qwen-plus",
        "light": "qwen-turbo",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    },
    "zhipu": {
        "heavy": "glm-4-plus",
        "standard": "glm-4-air",
        "light": "glm-4-flash",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
    },
    "moonshot": {
        "heavy": "moonshot-v1-8k",
        "standard": "moonshot-v1-8k",
        "light": "moonshot-v1-8k",
        "base_url": "https://api.moonshot.cn/v1",
    },
    "ollama": {
        "heavy": "qwen2.5:72b",
        "standard": "qwen2.5:32b",
        "light": "qwen2.5:7b",
        "base_url": "http://localhost:11434/v1",
    },
    "google": {
        "heavy": "gemini-2.5-pro",
        "standard": "gemini-2.5-pro",
        "light": "gemini-2.5-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
    },
    "xai": {
        "heavy": "grok-3",
        "standard": "grok-3",
        "light": "grok-3-mini",
        "base_url": "https://api.x.ai/v1",
    },
    "minimax": {
        "heavy": "abab7-chat",
        "standard": "abab7-chat",
        "light": "abab6.5s-chat",
        "base_url": "https://api.minimax.chat/v1",
    },
}


def get_provider_config():
    """
    解析 API 配置。

    优先级：环境变量 > provider 预设

    返回 (base_url, api_key, headers)
    """
    provider = os.environ.get("PROVIDER", "deepseek").lower()
    preset = PROVIDER_PRESETS.get(provider, {})

    # API Key
    key_env_map = {
        "deepseek": "DEEPSEEK_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "qwen": "QWEN_API_KEY",
        "zhipu": "ZHIPU_API_KEY",
        "moonshot": "MOONSHOT_API_KEY",
        "ollama": None,
        "google": "GOOGLE_API_KEY",
        "xai": "XAI_API_KEY",
        "minimax": "MINIMAX_API_KEY",
    }

    api_key = ""
    key_env = key_env_map.get(provider)
    if key_env:
        api_key = os.environ.get(key_env, "")
    if not api_key:
        # Fallback: CUSTOM_API_KEY or any *_API_KEY
        for k, v in os.environ.items():
            if k.endswith("_API_KEY") and v:
                api_key = v
                break

    # Base URL
    base_url = os.environ.get("BASE_URL", preset.get("base_url", "https://api.deepseek.com"))

    # Headers
    headers = {"Content-Type": "application/json"}
    if provider == "ollama":
        pass  # Ollama doesn't need auth
    elif api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    return base_url.rstrip("/"), api_key, headers


def resolve_model(agent_tier):
    """
    根据 Agent 的能力级别解析实际模型名。自动降级。

    agent_tier: "haiku" | "sonnet" | "opus" (from agent frontmatter model field)
    如果传入的不是已知能力级别，原样返回（说明已经是具体模型名）。

    返回: 实际模型名 (str)
    """
    # 不是能力级别 → 已解析过的具体模型名，原样返回
    if agent_tier and agent_tier not in ("haiku", "sonnet", "opus"):
        return agent_tier

    # 空值 → 用默认
    if not agent_tier:
        return get_default_model()

    provider = os.environ.get("PROVIDER", "deepseek").lower()

    # 用户手动覆盖（最高优先级）
    provider_upper = provider.upper()
    env_map_with_provider = {
        "opus": [f"{provider_upper}_HEAVY_MODEL", "HEAVY_MODEL"],
        "sonnet": [f"{provider_upper}_STANDARD_MODEL", "STANDARD_MODEL"],
        "haiku": [f"{provider_upper}_LIGHT_MODEL", "LIGHT_MODEL"],
    }

    # 尝试精准匹配
    for env_name in env_map_with_provider.get(agent_tier, []):
        model = os.environ.get(env_name)
        if model:
            return model

    # 没配置 → 自动降级
    preset = PROVIDER_PRESETS.get(provider, {})
    tier_fallback = {
        "opus": ["heavy", "standard", "light", "default"],
        "sonnet": ["standard", "light", "default"],
        "haiku": ["light", "default"],
    }

    for fallback in tier_fallback.get(agent_tier, ["default"]):
        if fallback == "default":
            model = os.environ.get("DEFAULT_MODEL")
            if model:
                return model
        else:
            model = preset.get(fallback)
            if model:
                return model

    # 终极降级
    return "deepseek-chat"


def get_actual_model(agent_frontmatter_model):
    """兼容旧 API 的包装器"""
    return resolve_model(agent_frontmatter_model)


def get_default_model():
    """获取默认模型（用于未指定 Agent 的调用）"""
    return os.environ.get("DEFAULT_MODEL") or resolve_model("sonnet")


# === 最新模型价格（2026.06） ===

PRICING = {
    # DeepSeek
    "deepseek-v4-pro": (0.28, 0.28),       # $/1M tokens, input=output after 2026.05 降价
    "deepseek-v4-flash": (0.07, 0.07),
    "deepseek-v3": (0.27, 0.27),
    "deepseek-r1": (0.55, 2.19),
    "deepseek-chat": (0.27, 1.10),
    "deepseek-reasoner": (0.55, 2.19),
    # OpenAI
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    # Anthropic (Claude)
    "claude-opus-4-8": (15.00, 75.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5": (0.80, 4.00),
    # Google
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.5-flash-lite": (0.15, 0.60),
    # Qwen (通义千问)
    "qwen-max": (2.00, 6.00),
    "qwen-plus": (1.00, 2.00),
    "qwen-turbo": (0.30, 0.60),
    # Zhipu (智谱)
    "glm-4-plus": (7.00, 7.00),
    "glm-4-air": (0.35, 0.35),
    "glm-4-flash": (0.20, 0.20),
    # Moonshot
    "moonshot-v1-8k": (2.00, 2.00),
}


def estimate_cost(model, in_tokens, out_tokens):
    """估算费用（美元）"""
    if model in PRICING:
        in_price, out_price = PRICING[model]
        return (in_tokens / 1_000_000) * in_price + (out_tokens / 1_000_000) * out_price
    # Unknown model: conservative estimate
    return (in_tokens / 1_000_000) * 1.0 + (out_tokens / 1_000_000) * 3.0
