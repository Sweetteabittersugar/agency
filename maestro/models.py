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
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelPrice:
    """模型定价——含缓存感知价格 + token 估算系数。

    cache_read:  缓存命中输入价格（USD/MTok），通常为 input 的 10-20%
    cache_write: 缓存写入价格（USD/MTok），仅 Anthropic/Google/Qwen 收取。
                 5-min TTL 通常为 input 的 1.25×，1-hour TTL 为 2×。
                 此字段取 5-min TTL 值（高频场景默认）。
    tok_per_char: 中文场景 token/字符 估算系数。
                  不同模型 tokenizer 对同一中文文本的 token 数可差 3 倍：
                  Claude ~0.8 tok/字，DeepSeek ~0.5 tok/字，Qwen ~0.3 tok/字。
                  取实测上限值（保守高估），用于无 API usage 时的 fallback 估算。
    """
    input: float
    cache_read: float
    output: float
    cache_write: float = 0.0
    tok_per_char: float = 0.40  # 默认保守值

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


# === 模型定价表（2026.06.15 WebSearch 核实，含缓存感知价格） ===
# 格式: ModelPrice(input, cache_read, output, cache_write)
#   - input:       标准输入 / cache miss (USD/MTok)
#   - cache_read:  缓存命中输入 (USD/MTok)，通常为 input 的 10-20%
#   - output:      输出 (USD/MTok)
#   - cache_write: 缓存写入 (USD/MTok)，仅 Anthropic/Google/Qwen 收取
#
# 缓存折扣对比（跨厂商）：
#   DeepSeek V4 Pro:   cache_read=$0.0145,  97% off (!)
#   Claude Opus 4.8:   cache_read=$0.50,    90% off
#   GPT-5:             cache_read=$0.125,   90% off
#   Gemini 2.5 Pro:    cache_read=$0.125,   90% off
#   Grok 4.3:          cache_read=$0.20,    84% off
#   Kimi K2.6:         cache_read=$0.16,    83% off
#   MiniMax M3:        cache_read=$0.06,    80% off
#
# 数据来源（2026.06.15 WebSearch）：
#   cloudzero.com/blog/claude-api-pricing
#   cloudzero.com/blog/deepseek-pricing
#   openai.com/api/pricing
#   opslyft.com/blog/google-gemini-api-pricing-2026
#   docs.x.ai/developers/pricing
#   alibabacloud.com/help/zh/model-studio/model-pricing
#   platform.minimax.io/docs/guides/pricing-paygo
#   kimi.com/resources/kimi-k2-6-pricing
PRICING: dict[str, ModelPrice] = {
    # ── DeepSeek — api-docs.deepseek.com（2026.05 75%永久降价） ──
    # cache 自动生效，无 cache_write 费
    # tok_per_char=0.5: 中文高效 tokenizer，实测 0.3-0.5 tok/字，取上限
    "deepseek-v4-pro": ModelPrice(
        input=0.435, cache_read=0.0145, output=0.87, tok_per_char=0.5,
    ),
    "deepseek-v4-flash": ModelPrice(
        input=0.14, cache_read=0.028, output=0.28, tok_per_char=0.5,
    ),
    # 旧名兼容（2026.07退役，迁移到 v4-flash）
    "deepseek-chat": ModelPrice(
        input=0.14, cache_read=0.028, output=0.28, tok_per_char=0.5,
    ),
    "deepseek-reasoner": ModelPrice(
        input=0.14, cache_read=0.028, output=0.28, tok_per_char=0.5,
    ),

    # ── Anthropic Claude — platform.claude.com ──
    # cache_write: 5-min TTL = 1.25× input, 1-hour TTL = 2× input
    # tok_per_char=0.8: 中文 token 税最高（比英文贵 64%），实测 0.6-0.8 tok/字
    "claude-opus-4-8": ModelPrice(
        input=5.00, cache_read=0.50, output=25.00, cache_write=6.25, tok_per_char=0.8,
    ),
    "claude-sonnet-4-6": ModelPrice(
        input=3.00, cache_read=0.30, output=15.00, cache_write=3.75, tok_per_char=0.8,
    ),
    "claude-haiku-4-5": ModelPrice(
        input=1.00, cache_read=0.10, output=5.00, cache_write=1.25, tok_per_char=0.8,
    ),
    # Fable 5 / Mythos 5 — 2026-06-10 发布，美国政府禁止非美国用户访问（2026-06-12）
    # ⚠️ US-ONLY: 国内 DeepSeek 路由不可达
    "claude-fable-5": ModelPrice(
        input=10.00, cache_read=1.00, output=50.00, cache_write=12.50, tok_per_char=0.8,
    ),
    "claude-mythos-5": ModelPrice(
        input=15.00, cache_read=1.50, output=75.00, cache_write=18.75, tok_per_char=0.8,
    ),

    # ── OpenAI GPT-5 — developers.openai.com ──
    # cache 自动生效（≥1024 token 前缀匹配），无 cache_write 费
    # tok_per_char=0.65: 中文比英文贵 ~35%，实测 0.45-0.65 tok/字
    "gpt-5": ModelPrice(
        input=1.25, cache_read=0.125, output=10.00, tok_per_char=0.65,
    ),
    "gpt-5-mini": ModelPrice(
        input=0.25, cache_read=0.025, output=2.00, tok_per_char=0.65,
    ),
    "gpt-5-nano": ModelPrice(
        input=0.05, cache_read=0.005, output=0.40, tok_per_char=0.65,
    ),
    "gpt-5.2": ModelPrice(
        input=1.75, cache_read=0.175, output=14.00, tok_per_char=0.65,
    ),
    "gpt-5.4": ModelPrice(
        input=2.50, cache_read=0.25, output=15.00, tok_per_char=0.65,
    ),
    "gpt-5.4-mini": ModelPrice(
        input=0.75, cache_read=0.075, output=4.50, tok_per_char=0.65,
    ),
    "gpt-5.4-nano": ModelPrice(
        input=0.20, cache_read=0.02, output=1.25, tok_per_char=0.65,
    ),
    "gpt-5-pro": ModelPrice(
        input=15.00, cache_read=0, output=120.00, tok_per_char=0.65,  # Pro 不支持缓存
    ),
    # GPT-4.1 系列（保留兼容）
    "gpt-4.1": ModelPrice(
        input=2.00, cache_read=0.50, output=8.00, tok_per_char=0.55,
    ),
    "gpt-4.1-mini": ModelPrice(
        input=0.40, cache_read=0.10, output=1.60, tok_per_char=0.55,
    ),
    "gpt-4.1-nano": ModelPrice(
        input=0.10, cache_read=0.025, output=0.40, tok_per_char=0.55,
    ),
    # GPT-4o 旧版（保留兼容）
    "gpt-4o": ModelPrice(
        input=2.50, cache_read=1.25, output=10.00, tok_per_char=0.55,
    ),
    "gpt-4o-mini": ModelPrice(
        input=0.15, cache_read=0.075, output=0.60, tok_per_char=0.55,
    ),

    # ── Google Gemini — opslyft.com ──
    # cache_write: 按小时收费的存储费（此处取标准 5-min 等价）
    # tok_per_char=0.6: 中位水平
    "gemini-2.5-pro": ModelPrice(
        input=1.25, cache_read=0.125, output=10.00, cache_write=1.5625, tok_per_char=0.6,
    ),
    "gemini-2.5-flash": ModelPrice(
        input=0.30, cache_read=0.03, output=2.50, cache_write=0.375, tok_per_char=0.6,
    ),
    "gemini-2.5-flash-lite": ModelPrice(
        input=0.10, cache_read=0.01, output=0.40, cache_write=0.125, tok_per_char=0.6,
    ),

    # ── xAI Grok — docs.x.ai（2026.05） ──
    # tok_per_char=0.55: 中位偏上
    "grok-4.3": ModelPrice(
        input=1.25, cache_read=0.20, output=2.50, tok_per_char=0.55,
    ),
    "grok-4.20": ModelPrice(
        input=1.25, cache_read=0.20, output=2.50, tok_per_char=0.55,
    ),
    "grok-build-0.1": ModelPrice(
        input=1.00, cache_read=0.20, output=2.00, tok_per_char=0.55,
    ),
    "grok-4-1-fast-reasoning": ModelPrice(
        input=0.20, cache_read=0.05, output=0.50, tok_per_char=0.55,
    ),

    # ── Qwen 通义千问 — help.aliyun.com（2026.06） ──
    # 显式缓存：write=1.25×input, read=0.1×input
    # tok_per_char=0.35: 中文最高效，实测 0.25-0.4 tok/字
    "qwen3-max": ModelPrice(
        input=0.34, cache_read=0.034, output=1.38, cache_write=0.425, tok_per_char=0.35,
    ),
    "qwen3.7-max": ModelPrice(
        input=2.50, cache_read=0.25, output=7.50, cache_write=3.125, tok_per_char=0.35,
    ),
    "qwen3.6-flash": ModelPrice(
        input=0.25, cache_read=0.025, output=0.70, cache_write=0.3125, tok_per_char=0.35,
    ),
    "qwen-long": ModelPrice(
        input=0.07, cache_read=0.007, output=0.28, cache_write=0.0875, tok_per_char=0.35,
    ),
    "qwen-turbo": ModelPrice(
        input=0.10, cache_read=0.02, output=0.30, tok_per_char=0.35,
    ),

    # ── Zhipu 智谱 — bigmodel.cn ──
    # tok_per_char=0.55: 中位水平
    "GLM-5.2": ModelPrice(
        # 2026-06-15 发布，1M 上下文，MIT 开源。API 定价待确认，暂按 5.1 上浮 20% 估算
        input=1.00, cache_read=0.10, output=3.50, cache_write=1.25, tok_per_char=0.55,
    ),
    "GLM-5.1": ModelPrice(
        input=0.83, cache_read=0.083, output=3.31, cache_write=1.0375, tok_per_char=0.55,
    ),
    "GLM-4.7": ModelPrice(
        input=0.55, cache_read=0.055, output=2.20, cache_write=0.6875, tok_per_char=0.55,
    ),
    "GLM-4.5-air": ModelPrice(
        input=0.27, cache_read=0.027, output=1.10, tok_per_char=0.55,
    ),
    "GLM-4-Flash": ModelPrice(
        input=0, cache_read=0, output=0, tok_per_char=0.55,  # 免费
    ),

    # ── Kimi / Moonshot — kimi.com（2026.05 K2.6） ──
    # tok_per_char=0.5: 中位
    "kimi-k2.6": ModelPrice(
        input=0.95, cache_read=0.16, output=4.00, tok_per_char=0.5,
    ),

    # ── MiniMax — platform.minimax.io（2026.06 M3） ──
    # 50% 启动折扣已永久化，英文效率最优（-4.3%）
    # tok_per_char=0.45: 英文最优，中文取中位
    "minimax-m3": ModelPrice(
        input=0.30, cache_read=0.06, output=1.20, tok_per_char=0.45,
    ),
    "minimax-m2.7": ModelPrice(
        input=0.15, cache_read=0.03, output=0.60, tok_per_char=0.45,
    ),

    # ── 豆包 / 火山引擎 — ark.cn-beijing.volces.com ──
    # tok_per_char=0.4: 中文优化，接近 Qwen
    "doubao-pro-32k": ModelPrice(
        input=0.10, cache_read=0.02, output=0.40, tok_per_char=0.4,
    ),
    "doubao-lite-32k": ModelPrice(
        input=0.04, cache_read=0.008, output=0.16, tok_per_char=0.4,
    ),

    # ── 美团 LongCat — longcat.chat ──
    "longcat-2-preview": ModelPrice(
        input=0.28, cache_read=0.056, output=1.10, tok_per_char=0.5,
    ),

    # ── 小米 MiMo — api.mimo.tech ──
    "mimo-v2.5-pro": ModelPrice(
        input=1.00, cache_read=0.20, output=3.00, tok_per_char=0.5,
    ),

    # ── 百度千帆 — qianfan.baidubce.com ──
    "ernie-4.5": ModelPrice(
        input=0.82, cache_read=0.082, output=3.28, tok_per_char=0.55,
    ),
    "ernie-speed": ModelPrice(
        input=0.06, cache_read=0.012, output=0.24, tok_per_char=0.55,
    ),
}

# 向后兼容：从 ModelPrice 提取 (input, output) 二元组
# 旧代码通过 get_price() 访问，无需直接读取此表
_LEGACY_PRICING_CACHE: dict[str, tuple[float, float]] = {}

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
    "zhipu": {"powerful": "GLM-5.2", "balanced": "GLM-5.2", "fast": "GLM-4-Flash"},
    "kimi": {"powerful": "kimi-k2.6", "balanced": "kimi-k2.6", "fast": "kimi-k2.6"},
    "minimax": {"powerful": "minimax-m3", "balanced": "minimax-m3", "fast": "minimax-m2.7"},
    "doubao": {"powerful": "doubao-pro-32k", "balanced": "doubao-pro-32k", "fast": "doubao-lite-32k"},
    "longcat": {"powerful": "longcat-2-preview", "balanced": "longcat-2-preview", "fast": "longcat-2-preview"},
    "mimo": {"powerful": "mimo-v2.5-pro", "balanced": "mimo-v2.5-pro", "fast": "mimo-v2.5-pro"},
    "baidu": {"powerful": "ernie-4.5", "balanced": "ernie-4.5", "fast": "ernie-speed"},
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
    "GLM-5.2": 1_000_000,  # 2026-06-15 发布
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


def get_model_price(model: str) -> ModelPrice | None:
    """获取模型的完整定价信息（含缓存价格）。
    先查用户覆盖（pricing.json），再查内置 PRICING 表。
    返回 None 表示未知模型。"""
    overrides = load_pricing_overrides()
    if model in overrides:
        ov = overrides[model]
        if isinstance(ov, dict):
            return ModelPrice(
                input=ov.get("input", 0),
                cache_read=ov.get("cache_read", 0),
                output=ov.get("output", 0),
                cache_write=ov.get("cache_write", 0),
                tok_per_char=ov.get("tok_per_char", 0.40),
            )
    return PRICING.get(model)


def get_price(model: str, token_type: str = "input") -> float:
    """获取模型单一价格（向后兼容旧调用方）。
    支持 'input', 'output', 'cache_read', 'cache_write'。
    旧代码只传 'input'/'output' 仍正常工作。"""
    overrides = load_pricing_overrides()
    if model in overrides and token_type in overrides[model]:
        return float(overrides[model][token_type])

    price = PRICING.get(model)
    if price is None:
        return 0.0
    return getattr(price, token_type, 0.0)


def estimate_tokens(text: str, model: str = "") -> int:
    """根据模型 tokenizer 特性估算 token 数（中文场景）。

    不同模型对同一中文文本的 token 数可差 3 倍（见 ModelPrice.tok_per_char），
    因此不能用统一的 len(text)//4 估算。

    tok_per_char 取实测上限值（保守高估），来源：
    极客公园 2026.05 22 段平行文本 5 个 tokenizer 横向对比。

    返回估算 token 数，最小为 1。
    """
    if not text:
        return 0
    price = get_model_price(model) if model else None
    coeff = price.tok_per_char if price else 0.40
    return max(1, int(len(text) * coeff))


# === 模型名标准化 ===
# Claude Code 的 result 事件中 model 字段可能用简称（如 "sonnet"），
# 与此处 PRICING 表键名（如 "claude-sonnet-4-6"）不一致，导致费用计算、聚合统计出错。
# 此映射将简称统一到 PRICING 标准键名，单向查找，不强制对称。

_MODEL_ALIAS_MAP = {
    # Anthropic 简称 → 全称
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-8",
    "haiku": "claude-haiku-4-5",
    "claude-sonnet": "claude-sonnet-4-6",
    "claude-opus": "claude-opus-4-8",
    "claude-haiku": "claude-haiku-4-5",
    "claude-fable": "claude-fable-5",
    "claude-mythos": "claude-mythos-5",
    # GPT 系列
    "gpt-5": "gpt-5",  # 保持不变，仅占位
    "gpt-5.1": "gpt-5",
    "gpt-5.4": "gpt-5.4",
    # Grok 系列
    "grok": "grok-4.3",
    "grok-4": "grok-4.3",
    # Gemini 系列
    "gemini-pro": "gemini-2.5-pro",
    "gemini-flash": "gemini-2.5-flash",
    # DeepSeek 系列
    "deepseek": "deepseek-v4-pro",
    "deepseek-chat": "deepseek-v4-flash",  # 即将退役
    # Qwen 系列
    "qwen": "qwen3-max",
    "qwen3": "qwen3-max",
    # Zhipu 系列
    "glm": "GLM-5.2",
    "glm-5": "GLM-5.2",
    "glm-5.2": "GLM-5.2",
    "glm-4": "GLM-4.7",
    # Kimi 系列
    "kimi": "kimi-k2.6",
    "moonshot": "kimi-k2.6",
    # MiniMax
    "minimax": "minimax-m3",
    # 豆包
    "doubao": "doubao-pro-32k",
    # LongCat
    "longcat": "longcat-2-preview",
    # MiMo
    "mimo": "mimo-v2.5-pro",
    # 百度
    "ernie": "ernie-4.5",
    "baidu": "ernie-4.5",
}


def normalize_model_name(model: str) -> str:
    """将 Claude Code 可能用的模型简称标准化为 PRICING 表键名。
    不在映射表中的名称原样返回。"""
    if not model:
        return model
    lower = model.lower().strip()
    # 精确匹配优先
    if lower in _MODEL_ALIAS_MAP:
        return _MODEL_ALIAS_MAP[lower]
    # 前缀匹配（如 "sonnet-20250601" → "claude-sonnet-4-6"）
    for alias, canonical in _MODEL_ALIAS_MAP.items():
        if lower.startswith(alias):
            return canonical
    return model


def estimate_cost(model: str, in_tokens: int, out_tokens: int,
                  cache_read: int = 0, cache_write: int = 0) -> tuple[float, float, float]:
    """估算费用（美元）— 仅 fallback 用。缓存感知版。

    正常路径应使用 Claude Code result.total_cost_usd（API 实际扣费金额），
    该值在 claude_session.py 的 result 事件中直接读取，天然准确。

    本函数只在以下场景使用：
    1. 无 Claude 进程时读取历史 JSONL 做离线统计
    2. Claude result 事件异常未报 cost 时做兜底（此时标记 is_estimated=True）
    3. cost-tracker / cost-analyzer 等只读 cost.db 的工具做补充估算
    4. 预算检查时预估新任务的费用

    计费公式（缓存感知）:
      cost = miss_tokens × input_price
           + cache_read × cache_read_price
           + cache_write × cache_write_price
           + out_tokens × output_price

    返回:
      (total_cost_usd, cache_saved_usd, cache_hit_rate_pct)

      cache_saved:      与完全不使用缓存相比节省的输入费用
      cache_hit_rate:   缓存命中率 (0-100)，无缓存时返回 0

    >>> estimate_cost("deepseek-v4-pro", 100000, 10000, cache_read=50000)
    (0.0725, 0.021, 50.0)
    """
    price = get_model_price(model)
    if price is None:
        # Unknown model: conservative estimate ($1/M input + $3/M output)
        miss = max(0, in_tokens - cache_read - cache_write)
        cost = (miss / 1_000_000) * 1.0 + (out_tokens / 1_000_000) * 3.0
        saved = (cache_read / 1_000_000) * 1.0  # 保守估计缓存节省
        hit_rate = (cache_read / (in_tokens + 1)) * 100 if in_tokens > 0 else 0
        return (cost, saved, hit_rate)

    # 缓存写入的 token 按 cache_write 价计，剩余的按标准输入价
    miss_tokens = max(0, in_tokens - cache_read - cache_write)

    cost = (
        (miss_tokens / 1_000_000) * price.input
        + (cache_read / 1_000_000) * price.cache_read
        + (cache_write / 1_000_000) * price.cache_write
        + (out_tokens / 1_000_000) * price.output
    )

    # 缓存节省 = 如果不使用缓存需要付的输入费 - 实际付的缓存费
    saved = (cache_read / 1_000_000) * (price.input - price.cache_read)

    hit_rate = (cache_read / (in_tokens + 1)) * 100 if in_tokens > 0 else 0

    return (cost, saved, hit_rate)


# 向后兼容包装：旧调用方只接受 3 参数、期望返回 float
def _estimate_cost_legacy(model: str, in_tokens: int, out_tokens: int) -> float:
    """旧版 estimate_cost 兼容包装——仅返回 total_cost，忽略缓存信息。
    新代码应使用 estimate_cost() 获取完整三元组。"""
    cost, _, _ = estimate_cost(model, in_tokens, out_tokens)
    return cost
