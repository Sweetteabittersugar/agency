#!/usr/bin/env python3
"""
Model System v3 — 向后兼容重导出层

拆分历史（2026-06-16）：
  - pricing.py       → ModelPrice / PRICING / estimate_* / normalize
  - model_registry.py → PROVIDER_* / MODEL_* / resolve / compaction

此文件保留所有公开 API 的重导出，确保现有调用方无需修改。
新代码应直接从 pricing.py 或 model_registry.py 导入。
"""

from __future__ import annotations

# ── 定价（pricing.py） ──
from maestro.pricing import (  # noqa: F401 — re-export for backward compat
    ModelPrice,
    PRICING,
    get_model_price,
    get_price,
    estimate_tokens,
    estimate_cost,
    normalize_model_name,
    load_pricing_overrides,
    _MODEL_ALIAS_MAP,
    _LEGACY_PRICING_CACHE,
    _estimate_cost_legacy,
)

# ── 模型注册（model_registry.py） ──
from maestro.model_registry import (  # noqa: F401 — re-export for backward compat
    PROVIDER_PRESETS,
    PROVIDER_MAP,
    MODEL_TIERS,
    MODEL_CONTEXT_WINDOWS,
    COMPACTION_WARN_RATIO,
    COMPACTION_FORCE_RATIO,
    get_provider_config,
    resolve_model,
    get_actual_model,
    get_context_limit,
    get_model_tier,
    get_default_model,
    check_compaction,
)
