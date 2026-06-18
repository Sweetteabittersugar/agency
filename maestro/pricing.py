#!/usr/bin/env python3
"""
Pricing v3 — 缓存感知模型定价 + Token 估算

从 models.py 拆分出来（2026-06-16），职责：
  - ModelPrice dataclass
  - PRICING 表（47 模型 / 14 供应商）
  - 外部定价覆盖（pricing.json 热加载）
  - Token 估算（tok_per_char 每模型系数）
  - 费用估算（estimate_cost 三元组）
  - 模型名标准化（alias → canonical）
"""

from __future__ import annotations

import json as _json
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


# ═══════════════════════════════════════════════════
# 模型定价表
# ═══════════════════════════════════════════════════
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
#
# 缓存折扣对比（跨厂商）：
#   DeepSeek V4 Pro:   cache_read=$0.0145,  97% off (!)
#   Claude Opus 4.8:   cache_read=$0.50,    90% off
#   GPT-5:             cache_read=$0.125,   90% off
#   Gemini 2.5 Pro:    cache_read=$0.125,   90% off
#   Grok 4.3:          cache_read=$0.20,    84% off
#   Kimi K2.6:         cache_read=$0.16,    83% off
#   MiniMax M3:        cache_read=$0.06,    80% off

PRICING: dict[str, ModelPrice] = {
    # ── DeepSeek — api-docs.deepseek.com（2026.06 缓存降价至首发价 1/10） ──
    # cache 自动生效，无 cache_write 费
    # tok_per_char=0.5: 中文高效 tokenizer，实测 0.3-0.5 tok/字，取上限
    "deepseek-v4-pro": ModelPrice(
        input=0.435, cache_read=0.003625, output=0.87, tok_per_char=0.5,
    ),
    "deepseek-v4-flash": ModelPrice(
        input=0.14, cache_read=0.0028, output=0.28, tok_per_char=0.5,
    ),
    # 旧名兼容（2026.07退役，迁移到 v4-flash）
    "deepseek-chat": ModelPrice(
        input=0.14, cache_read=0.0028, output=0.28, tok_per_char=0.5,
    ),
    "deepseek-reasoner": ModelPrice(
        input=0.14, cache_read=0.0028, output=0.28, tok_per_char=0.5,
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
    # 官方标准价。早前 50% 启动促销已于 2026.05 结束。
    # tok_per_char=0.45: 英文最优，中文取中位
    "minimax-m3": ModelPrice(
        input=0.60, cache_read=0.12, output=2.40, tok_per_char=0.45,
    ),
    "minimax-m2.7": ModelPrice(
        input=0.30, cache_read=0.06, output=1.20, tok_per_char=0.45,
    ),

    # ── 豆包 / 火山引擎 — ark.cn-beijing.volces.com ──
    # 2026.06 定价（豆包2.0 Pro/Lite），¥→$≈7.2:1
    # tok_per_char=0.4: 中文优化，接近 Qwen
    "doubao-pro-32k": ModelPrice(
        input=0.45, cache_read=0.09, output=2.25, tok_per_char=0.4,
    ),
    "doubao-lite-32k": ModelPrice(
        input=0.08, cache_read=0.016, output=0.45, tok_per_char=0.4,
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
_LEGACY_PRICING_CACHE: dict[str, tuple[float, float]] = {}

# ═══════════════════════════════════════════════════
# 定价外部化（pricing.json 热加载）
# ═══════════════════════════════════════════════════

PRICING_FILE = Path(__file__).resolve().parent.parent / "pricing.json"

_pricing_cache = None
_pricing_cache_mtime = 0


def load_pricing_overrides() -> dict:
    """加载用户自定义定价覆盖（mtime 缓存）。"""
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
    支持 'input', 'output', 'cache_read', 'cache_write'。"""
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


# ═══════════════════════════════════════════════════
# 模型名标准化
# ═══════════════════════════════════════════════════
#
# Claude Code 的 result 事件中 model 字段可能用简称（如 "sonnet"），
# 与 PRICING 表键名（如 "claude-sonnet-4-6"）不一致，导致费用计算、聚合统计出错。
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
    "gpt-5": "gpt-5",
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
    "deepseek-chat": "deepseek-v4-flash",
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
    # 已是 PRICING 表中的规范名 → 直接返回，不走别名匹配
    # （防止 "deepseek-v4-flash" 被 "deepseek" 前缀误映射成 "deepseek-v4-pro"）
    if lower in PRICING:
        return model
    # 精确匹配别名
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

    返回:
      (total_cost_usd, cache_saved_usd, cache_hit_rate_pct)

    >>> estimate_cost("deepseek-v4-pro", 100000, 10000, cache_read=50000)
    (0.0725, 0.021, 50.0)
    """
    price = get_model_price(model)
    if price is None:
        # Unknown model: conservative estimate ($1/M input + $3/M output)
        miss = max(0, in_tokens - cache_read - cache_write)
        cost = (miss / 1_000_000) * 1.0 + (out_tokens / 1_000_000) * 3.0
        saved = (cache_read / 1_000_000) * 1.0
        hit_rate = (cache_read / (in_tokens + 1)) * 100 if in_tokens > 0 else 0
        return (cost, saved, hit_rate)

    miss_tokens = max(0, in_tokens - cache_read - cache_write)

    cost = (
        (miss_tokens / 1_000_000) * price.input
        + (cache_read / 1_000_000) * price.cache_read
        + (cache_write / 1_000_000) * price.cache_write
        + (out_tokens / 1_000_000) * price.output
    )

    saved = (cache_read / 1_000_000) * (price.input - price.cache_read)

    hit_rate = (cache_read / (in_tokens + 1)) * 100 if in_tokens > 0 else 0

    return (cost, saved, hit_rate)


def _estimate_cost_legacy(model: str, in_tokens: int, out_tokens: int) -> float:
    """旧版 estimate_cost 兼容包装——仅返回 total_cost。
    新代码应使用 estimate_cost() 获取完整三元组。"""
    cost, _, _ = estimate_cost(model, in_tokens, out_tokens)
    return cost
