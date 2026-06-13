#!/usr/bin/env python3
"""
Model System v3 --- 多级模型映射 + 自动降级 + 主流模型预设

Agent frontmatter 中的 model 字段是"能力级别"：
  haiku  → 轻量级（简单搜索、费用分析）
  sonnet → 标准级（代码编写、审查、规划）
  opus   → 重量级（复杂推理、深度创作）

用户配置具体模型，支持自动降级：配了重型用重型，没配自动用标准，标准也没配用轻量。
"""

from __future__ import annotations

import os
from pathlib import Path

# === 主流模型预设（用户只需选 provider） ===

# 2026.06 更新：精简为7大主流Provider，移除moonshot/ollama/minimax/siliconflow/kimi/glm重复项
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
        "heavy": "GLM-5.1",
        "standard": "GLM-5.1",
        "light": "GLM-4-Flash",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
    },
}

# === API Provider 映射（chat / orchestrate 共用）===

# 2026.06 更新：与PROVIDER_PRESETS对齐，移除旧provider
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
    "custom": {},
}


def get_provider_config() -> tuple[str, str, dict[str, str]]:
    """
    解析 API 配置。

    优先级：环境变量 > provider 预设

    返回 (base_url, api_key, headers)
    """
    provider = os.environ.get("PROVIDER", "deepseek").lower()
    preset = PROVIDER_PRESETS.get(provider, {})

    # API Key
    # 2026.06 更新：精简为8个provider，移除moonshot/ollama/minimax/siliconflow/kimi/glm
    key_env_map = {
        "deepseek": "DEEPSEEK_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "qwen": "QWEN_API_KEY",
        "zhipu": "ZHIPU_API_KEY",
        "google": "GOOGLE_API_KEY",
        "xai": "XAI_API_KEY",
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


# 旧 tier 名 → 新 tier 名映射
_TIER_ALIAS = {
    "opus": "powerful", "sonnet": "balanced", "haiku": "fast",
    "heavy": "powerful", "standard": "balanced", "light": "fast",
}


def resolve_model(agent_tier: str | None = None) -> str:
    """
    根据 Agent 的能力级别解析实际模型名。自动降级。

    agent_tier 接受：
      - 新命名: "fast" | "balanced" | "powerful"
      - 旧命名（兼容）: "haiku" | "sonnet" | "opus" | "light" | "standard" | "heavy"
      - 具体模型名: 如 "deepseek-v4-pro" → 原样返回

    返回: 实际模型名 (str)
    """
    # 空值 → 用默认
    if not agent_tier:
        return get_default_model()

    # 统一为 fast/balanced/powerful
    tier = _TIER_ALIAS.get(agent_tier, agent_tier)

    # 不是已知 tier → 已解析过的具体模型名，原样返回
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

    # 4) 终极降级 → deepseek-v4-flash（不再用已废弃的 deepseek-chat）
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
    """获取默认模型（用于未指定 Agent 的调用）"""
    return os.environ.get("DEFAULT_MODEL") or resolve_model("sonnet")


# === 模型定价表（2026.06 WebSearch 核实） ===
# (input_price, output_price) 单位 USD/百万token
#
# DeepSeek 来源: api-docs.deepseek.com/quick_start/pricing
#   - deepseek-chat/reasoner 将于 2026-07-24 废弃，迁移到 v4-flash
#   - V4 Pro 75% 永久折扣: $1.74→$0.435, $3.48→$0.87
# Anthropic 来源: cloudzero.com/blog/claude-api-pricing
#   - Opus 4.6+ 降价 67%: $15/$75 → $5/$25
# OpenAI 来源: openai.com/api/pricing (GPT-4.1 取代 GPT-4o)
# Google 来源: opslyft.com/blog/google-gemini-api-pricing-2026
#
# 2026.06 更新：GPT-5系列定价、xAI Grok 4.3、Qwen3/Zhipu GLM-5.1
PRICING = {
    # DeepSeek — api-docs.deepseek.com（2026.04 V4 永久促销）
    "deepseek-v4-pro": (0.435, 0.87),
    "deepseek-v4-flash": (0.14, 0.28),
    "deepseek-chat": (0.14, 0.28),      # 2026.07退役→v4-flash，保留兼容
    "deepseek-reasoner": (0.14, 0.28),  # 同上
    # Anthropic Claude — platform.claude.com（Opus 4.6+ 降价67%）
    "claude-opus-4-8": (5.00, 25.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    # OpenAI GPT-5 — developers.openai.com（2025.08）
    "gpt-5": (1.25, 10.00),
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5-nano": (0.05, 0.40),
    "gpt-4.1": (2.00, 8.00),            # 长上下文1M，保留兼容
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4o": (2.50, 10.00),            # 旧版，保留兼容
    "gpt-4o-mini": (0.15, 0.60),
    # Google Gemini — opslyft.com
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-flash-lite": (0.10, 0.40),
    # xAI Grok — docs.x.ai（2026.05）
    "grok-4.3": (1.25, 2.50),
    "grok-4-1-fast-reasoning": (0.20, 0.50),
    # Qwen 通义千问 — help.aliyun.com（1USD≈7.25CNY）
    "qwen3-max": (0.34, 1.38),
    "qwen-long": (0.07, 0.28),
    # Zhipu 智谱 — cloudprice.net
    "GLM-5.1": (0.83, 3.31),
    "GLM-4-Flash": (0, 0),              # 免费
}

# === 模型分级 ===
# 替代旧的 haiku/sonnet/opus 命名，统一为三级：
#   fast:     便宜快响应的日常任务（路由、搜索、简单编辑）
#   balanced: 性价比主力（代码生成、审查、复杂逻辑）
#   powerful: 最强推理（架构设计、难题调试、关键决策）
#
# 每个 Provider 的 PRESETS 中 heavy/standard/light 对应 powerful/balanced/fast
# 2026.06 更新：GPT-5系列、xAI/Qwen/Zhipu分级
MODEL_TIERS = {
    "deepseek": {"powerful": "deepseek-v4-pro", "balanced": "deepseek-v4-pro", "fast": "deepseek-v4-flash"},
    "anthropic": {"powerful": "claude-opus-4-8", "balanced": "claude-sonnet-4-6", "fast": "claude-haiku-4-5"},
    "openai": {"powerful": "gpt-5", "balanced": "gpt-5-mini", "fast": "gpt-5-nano"},
    "google": {"powerful": "gemini-2.5-pro", "balanced": "gemini-2.5-flash", "fast": "gemini-2.5-flash-lite"},
    "xai": {"powerful": "grok-4.3", "balanced": "grok-4.3", "fast": "grok-4-1-fast-reasoning"},
    "qwen": {"powerful": "qwen3-max", "balanced": "qwen3-max", "fast": "qwen-long"},
    "zhipu": {"powerful": "GLM-5.1", "balanced": "GLM-5.1", "fast": "GLM-4-Flash"},
}

# === 模型上下文窗口容量（token） ===
# 用于判断是否需要压缩，不再统一用 300K
# 2026.06 更新：GPT-5系列400K、xAI Grok 4.3/Qwen3/GLM-5.1上下文窗口
MODEL_CONTEXT_WINDOWS = {
    "deepseek-v4-pro": 1_000_000,
    "deepseek-v4-flash": 1_000_000,
    "deepseek-chat": 128_000,
    "deepseek-reasoner": 128_000,
    "claude-opus-4-8": 1_000_000,
    "claude-sonnet-4-6": 200_000,
    "claude-haiku-4-5": 200_000,
    "gpt-5": 400_000,
    "gpt-5-mini": 400_000,
    "gpt-5-nano": 400_000,
    "gpt-4.1": 1_000_000,
    "gpt-4.1-mini": 1_000_000,
    "gpt-4.1-nano": 1_000_000,
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gemini-2.5-pro": 1_000_000,
    "gemini-2.5-flash": 1_000_000,
    "gemini-2.5-flash-lite": 1_000_000,
    "grok-4.3": 1_000_000,
    "grok-4-1-fast-reasoning": 2_000_000,
    "qwen3-max": 262_144,
    "qwen-long": 1_000_000,
    "GLM-5.1": 200_000,
    "GLM-4-Flash": 128_000,
}

# === 上下文压缩策略 ===
# 行业惯例：警告 70%，强制压缩 85%。
# 参考：Claude 建议 75% 时考虑总结，GPT-4 在 80% 触发 truncation，
# Gemini 推荐 75-85% 区间。取中庸值：70% 提醒 / 85% 自动压缩。
COMPACTION_WARN_RATIO = 0.70   # 达到此比例时前端/后端触发提醒
COMPACTION_FORCE_RATIO = 0.85  # 达到此比例时自动触发上下文压缩


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


# === 定价外部化 ===

import json as _json

PRICING_FILE = Path(__file__).resolve().parent.parent / "pricing.json"


# Cache: avoid repeated file I/O on every cost estimate call
_pricing_cache = None
# Cache pricing file by mtime to avoid repeated disk I/O on every cost estimate call
_pricing_cache_mtime = 0

def load_pricing_overrides() -> dict:
    """加载用户自定义定价覆盖。"""
    if PRICING_FILE.exists():
        try:
            global _pricing_cache, _pricing_cache_mtime
            mtime = PRICING_FILE.stat().st_mtime
            if _pricing_cache is not None and mtime == _pricing_cache_mtime:
                return _pricing_cache
            _pricing_cache = _json.loads(PRICING_FILE.read_text(encoding="utf-8"))
            _pricing_cache_mtime = mtime
            return _pricing_cache
        except Exception:
            pass
    return {}


def get_price(model: str, token_type: str = "input") -> float:
    """获取模型价格（支持用户覆盖）。"""
    overrides = load_pricing_overrides()
    if model in overrides and token_type in overrides[model]:
        return overrides[model][token_type]
    idx = 0 if token_type == "input" else 1
    return PRICING.get(model, (0, 0))[idx]


def estimate_cost(model: str, in_tokens: int, out_tokens: int) -> float:
    """估算费用（美元）"""
    in_price = get_price(model, "input")
    out_price = get_price(model, "output")
    if in_price > 0 or out_price > 0:
        return (in_tokens / 1_000_000) * in_price + (out_tokens / 1_000_000) * out_price
    # Unknown model: conservative estimate
    return (in_tokens / 1_000_000) * 1.0 + (out_tokens / 1_000_000) * 3.0
