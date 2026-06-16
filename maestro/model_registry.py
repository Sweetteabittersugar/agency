#!/usr/bin/env python3
"""
Model Registry — Provider 预设 / 模型分级 / 路由解析 / 上下文压缩

从 models.py 拆分出来（2026-06-16），职责：
  - PROVIDER_PRESETS / PROVIDER_MAP — 供应商模型预设
  - MODEL_TIERS — 模型能力分级（powerful/balanced/fast）
  - MODEL_CONTEXT_WINDOWS — 上下文窗口容量
  - resolve_model() — tier → 具体模型名（含自动降级）
  - get_provider_config() — API key/base_url/headers 解析
  - check_compaction() — 上下文压缩判定
"""

from __future__ import annotations

import json as _json
import os
from pathlib import Path


# ═══════════════════════════════════════════════════
# Provider 预设
# ═══════════════════════════════════════════════════

PROVIDER_PRESETS = {
    "deepseek": {
        "heavy": "deepseek-v4-pro",
        "standard": "deepseek-v4-pro",
        "light": "deepseek-v4-flash",
        "base_url": "https://api.deepseek.com",
    },
    "anthropic": {
        "heavy": "claude-opus-4-8",
        "standard": "claude-sonnet-4-6",
        "light": "claude-haiku-4-5",
        "base_url": "https://api.anthropic.com/v1",
    },
    "openai": {
        "heavy": "gpt-5",
        "standard": "gpt-5-mini",
        "light": "gpt-5-nano",
        "base_url": "https://api.openai.com/v1",
    },
    "google": {
        "heavy": "gemini-2.5-pro",
        "standard": "gemini-2.5-flash",
        "light": "gemini-2.5-flash-lite",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
    },
    "xai": {
        "heavy": "grok-4.3",
        "standard": "grok-4.3",
        "light": "grok-4-1-fast-reasoning",
        "base_url": "https://api.x.ai/v1",
    },
    "qwen": {
        "heavy": "qwen3-max",
        "standard": "qwen3-max",
        "light": "qwen-long",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    },
    "zhipu": {
        "heavy": "GLM-5.2",
        "standard": "GLM-5.2",
        "light": "GLM-4-Flash",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
    },
    "kimi": {
        "heavy": "kimi-k2.6",
        "standard": "kimi-k2.6",
        "light": "kimi-k2.6",
        "base_url": "https://api.moonshot.cn/v1",
    },
    "minimax": {
        "heavy": "minimax-m3",
        "standard": "minimax-m3",
        "light": "minimax-m2.7",
        "base_url": "https://api.minimax.chat/v1",
    },
    "doubao": {
        "heavy": "doubao-pro-32k",
        "standard": "doubao-pro-32k",
        "light": "doubao-lite-32k",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    },
    "longcat": {
        "heavy": "longcat-2-preview",
        "standard": "longcat-2-preview",
        "light": "longcat-2-preview",
        "base_url": "https://api.longcat.chat/v1",
    },
    "mimo": {
        "heavy": "mimo-v2.5-pro",
        "standard": "mimo-v2.5-pro",
        "light": "mimo-v2.5-pro",
        "base_url": "https://api.mimo.tech/v1",
    },
    "baidu": {
        "heavy": "ernie-4.5",
        "standard": "ernie-4.5",
        "light": "ernie-speed",
        "base_url": "https://qianfan.baidubce.com/v2",
    },
}

# API Provider 映射（chat / orchestrate 共用）
PROVIDER_MAP = {
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
        "ANTHROPIC_MODEL": "gpt-5",
    },
    "google": {
        "ANTHROPIC_BASE_URL": "https://generativelanguage.googleapis.com/v1beta/openai",
        "ANTHROPIC_MODEL": "gemini-2.5-pro",
    },
    "xai": {
        "ANTHROPIC_BASE_URL": "https://api.x.ai/v1",
        "ANTHROPIC_MODEL": "grok-4.3",
    },
    "qwen": {
        "ANTHROPIC_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "ANTHROPIC_MODEL": "qwen3-max",
    },
    "zhipu": {
        "ANTHROPIC_BASE_URL": "https://open.bigmodel.cn/api/paas/v4",
        "ANTHROPIC_MODEL": "GLM-5.1",
    },
    "kimi": {
        "ANTHROPIC_BASE_URL": "https://api.moonshot.cn/v1",
        "ANTHROPIC_MODEL": "kimi-k2.6",
    },
    "minimax": {
        "ANTHROPIC_BASE_URL": "https://api.minimax.chat/v1",
        "ANTHROPIC_MODEL": "minimax-m3",
    },
    "doubao": {
        "ANTHROPIC_BASE_URL": "https://ark.cn-beijing.volces.com/api/v3",
        "ANTHROPIC_MODEL": "doubao-pro-32k",
    },
    "longcat": {
        "ANTHROPIC_BASE_URL": "https://api.longcat.chat/v1",
        "ANTHROPIC_MODEL": "longcat-2-preview",
    },
    "mimo": {
        "ANTHROPIC_BASE_URL": "https://api.mimo.tech/v1",
        "ANTHROPIC_MODEL": "mimo-v2.5-pro",
    },
    "baidu": {
        "ANTHROPIC_BASE_URL": "https://qianfan.baidubce.com/v2",
        "ANTHROPIC_MODEL": "ernie-4.5",
    },
    "custom": {},
}


def get_provider_config() -> tuple[str, str, dict[str, str]]:
    """解析 API 配置。优先级：环境变量 > provider 预设。
    返回 (base_url, api_key, headers)。"""
    provider = os.environ.get("PROVIDER", "deepseek").lower()
    preset = PROVIDER_PRESETS.get(provider, {})

    key_env_map = {
        "deepseek": "DEEPSEEK_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "qwen": "QWEN_API_KEY",
        "zhipu": "ZHIPU_API_KEY",
        "google": "GOOGLE_API_KEY",
        "xai": "XAI_API_KEY",
        "kimi": "KIMI_API_KEY",
        "minimax": "MINIMAX_API_KEY",
        "doubao": "DOUBAO_API_KEY",
        "longcat": "LONGCAT_API_KEY",
        "mimo": "MIMO_API_KEY",
        "baidu": "BAIDU_API_KEY",
    }

    api_key = ""
    key_env = key_env_map.get(provider)
    if key_env:
        api_key = os.environ.get(key_env, "")
    if not api_key:
        for k, v in os.environ.items():
            if k.endswith("_API_KEY") and v:
                api_key = v
                break

    base_url = os.environ.get("BASE_URL", preset.get("base_url", "https://api.deepseek.com"))

    headers = {"Content-Type": "application/json"}
    if provider == "ollama":
        pass  # Ollama doesn't need auth
    elif api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    return base_url.rstrip("/"), api_key, headers


# ═══════════════════════════════════════════════════
# 模型分级与路由
# ═══════════════════════════════════════════════════

_TIER_ALIAS = {
    "opus": "powerful", "sonnet": "balanced", "haiku": "fast",
    "heavy": "powerful", "standard": "balanced", "light": "fast",
}

MODEL_TIERS = {
    "deepseek": {"powerful": "deepseek-v4-pro", "balanced": "deepseek-v4-pro", "fast": "deepseek-v4-flash"},
    "anthropic": {"powerful": "claude-opus-4-8", "balanced": "claude-sonnet-4-6", "fast": "claude-haiku-4-5"},
    "openai": {"powerful": "gpt-5", "balanced": "gpt-5-mini", "fast": "gpt-5-nano"},
    "google": {"powerful": "gemini-2.5-pro", "balanced": "gemini-2.5-flash", "fast": "gemini-2.5-flash-lite"},
    "xai": {"powerful": "grok-4.3", "balanced": "grok-4.3", "fast": "grok-4-1-fast-reasoning"},
    "qwen": {"powerful": "qwen3-max", "balanced": "qwen3-max", "fast": "qwen-long"},
    "zhipu": {"powerful": "GLM-5.2", "balanced": "GLM-5.2", "fast": "GLM-4-Flash"},
    "kimi": {"powerful": "kimi-k2.6", "balanced": "kimi-k2.6", "fast": "kimi-k2.6"},
    "minimax": {"powerful": "minimax-m3", "balanced": "minimax-m3", "fast": "minimax-m2.7"},
    "doubao": {"powerful": "doubao-pro-32k", "balanced": "doubao-pro-32k", "fast": "doubao-lite-32k"},
    "longcat": {"powerful": "longcat-2-preview", "balanced": "longcat-2-preview", "fast": "longcat-2-preview"},
    "mimo": {"powerful": "mimo-v2.5-pro", "balanced": "mimo-v2.5-pro", "fast": "mimo-v2.5-pro"},
    "baidu": {"powerful": "ernie-4.5", "balanced": "ernie-4.5", "fast": "ernie-speed"},
}

# 模型上下文窗口容量（token），用于判断是否需要压缩
MODEL_CONTEXT_WINDOWS = {
    "deepseek-v4-pro": 1_000_000,
    "deepseek-v4-flash": 1_000_000,
    "deepseek-chat": 128_000,
    "deepseek-reasoner": 128_000,
    "claude-opus-4-8": 1_000_000,
    "claude-sonnet-4-6": 200_000,
    "claude-haiku-4-5": 200_000,
    "claude-fable-5": 200_000,   # US-only
    "claude-mythos-5": 200_000,  # US-only
    "gpt-5": 400_000,
    "gpt-5-mini": 400_000,
    "gpt-5-nano": 400_000,
    "gpt-5.2": 400_000,
    "gpt-5.4": 272_000,
    "gpt-5.4-mini": 400_000,
    "gpt-5.4-nano": 400_000,
    "gpt-5-pro": 400_000,
    "gpt-4.1": 1_000_000,
    "gpt-4.1-mini": 1_000_000,
    "gpt-4.1-nano": 1_000_000,
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gemini-2.5-pro": 1_000_000,
    "gemini-2.5-flash": 1_000_000,
    "gemini-2.5-flash-lite": 1_000_000,
    "grok-4.3": 1_000_000,
    "grok-4.20": 1_000_000,
    "grok-build-0.1": 256_000,
    "grok-4-1-fast-reasoning": 2_000_000,
    "qwen3-max": 262_144,
    "qwen3.7-max": 1_000_000,
    "qwen3.6-flash": 1_000_000,
    "qwen-long": 1_000_000,
    "qwen-turbo": 128_000,
    "GLM-5.2": 1_000_000,
    "GLM-5.1": 200_000,
    "GLM-4.7": 200_000,
    "GLM-4.5-air": 128_000,
    "GLM-4-Flash": 128_000,
    "kimi-k2.6": 262_144,
    "minimax-m3": 1_000_000,
    "minimax-m2.7": 256_000,
    "doubao-pro-32k": 32_000,
    "doubao-lite-32k": 32_000,
    "longcat-2-preview": 256_000,
    "mimo-v2.5-pro": 256_000,
    "ernie-4.5": 128_000,
    "ernie-speed": 128_000,
}


def resolve_model(agent_tier: str | None = None) -> str:
    """根据 Agent 的能力级别解析实际模型名。自动降级。

    agent_tier 接受：
      - 新命名: "fast" | "balanced" | "powerful"
      - 旧命名（兼容）: "haiku" | "sonnet" | "opus" | "light" | "standard" | "heavy"
      - 具体模型名: 如 "deepseek-v4-pro" → 原样返回
    """
    if not agent_tier:
        return get_default_model()

    tier = _TIER_ALIAS.get(agent_tier, agent_tier)
    if tier not in ("fast", "balanced", "powerful"):
        return tier

    provider = os.environ.get("PROVIDER", "deepseek").lower()

    # 1) 用户手动覆盖（最高优先级）—— 环境变量
    env_keys = {
        "powerful": [f"{provider.upper()}_HEAVY_MODEL", "HEAVY_MODEL"],
        "balanced": [f"{provider.upper()}_STANDARD_MODEL", "STANDARD_MODEL"],
        "fast": [f"{provider.upper()}_LIGHT_MODEL", "LIGHT_MODEL"],
    }
    for env_name in env_keys.get(tier, []):
        model = os.environ.get(env_name)
        if model:
            return model

    # 2) MODEL_TIERS 表查找
    provider_tiers = MODEL_TIERS.get(provider, {})
    fallback_order = {
        "powerful": ["powerful", "balanced", "fast"],
        "balanced": ["balanced", "fast", "powerful"],
        "fast": ["fast", "balanced", "powerful"],
    }
    for fb in fallback_order.get(tier, ["balanced"]):
        model = provider_tiers.get(fb)
        if model:
            return model

    # 3) 旧 PROVIDER_PRESETS fallback
    preset = PROVIDER_PRESETS.get(provider, {})
    preset_fallback = {
        "powerful": ["heavy", "standard", "light"],
        "balanced": ["standard", "light"],
        "fast": ["light"],
    }
    for fb in preset_fallback.get(tier, ["standard"]):
        model = preset.get(fb)
        if model:
            return model

    # 4) 终极降级
    return "deepseek-v4-flash"


def get_actual_model(agent_frontmatter_model: str | None = None) -> str:
    """兼容旧 API 的包装器"""
    return resolve_model(agent_frontmatter_model)


def get_context_limit(model: str) -> int:
    """查询模型的上下文窗口容量（token），未知模型默认 128K"""
    return MODEL_CONTEXT_WINDOWS.get(model, 128_000)


def get_model_tier(model: str) -> str:
    """反查具体模型名属于哪个 tier，用于仪表盘展示"""
    for provider_tiers in MODEL_TIERS.values():
        for tier, name in provider_tiers.items():
            if name == model:
                return tier
    return "unknown"


def get_default_model() -> str:
    """获取默认模型"""
    return os.environ.get("DEFAULT_MODEL") or resolve_model("sonnet")


# ═══════════════════════════════════════════════════
# 上下文压缩策略
# ═══════════════════════════════════════════════════

COMPACTION_WARN_RATIO = 0.70
COMPACTION_FORCE_RATIO = 0.85


def _load_compaction_overrides() -> dict:
    """读取用户自定义的压缩比例覆盖"""
    cfg_path = Path(__file__).resolve().parent / "compaction_config.json"
    try:
        if cfg_path.exists():
            return _json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def check_compaction(model: str, used_tokens: int) -> dict:
    """返回压缩状态: {warn, force, capacity, ratio, model}。
    先查用户自定义比例，无则用全局默认 70%/85%。"""
    capacity = MODEL_CONTEXT_WINDOWS.get(model, 128_000)
    ratio = used_tokens / capacity if capacity > 0 else 0
    overrides = _load_compaction_overrides()
    defaults = overrides.get("defaults", {"warn": COMPACTION_WARN_RATIO, "force": COMPACTION_FORCE_RATIO})
    model_cfg = overrides.get("models", {}).get(model, {})
    warn_ratio = model_cfg.get("warn", defaults["warn"])
    force_ratio = model_cfg.get("force", defaults["force"])
    return {
        "model": model,
        "used": used_tokens,
        "capacity": capacity,
        "ratio": round(ratio, 3),
        "warn": ratio >= warn_ratio,
        "force": ratio >= force_ratio,
    }
