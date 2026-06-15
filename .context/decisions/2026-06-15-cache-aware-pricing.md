# Decision: PRICING 升级为缓存感知 ModelPrice

**Date**: 2026-06-15
**Status**: accepted
**Supersedes**: (extends 2026-06-14-unified-pricing-source)

## Context

v1 修复了计费源头（统一切到 total_cost_usd），但 fallback 场景的 estimate_cost 仍然用二元组 (input_price, output_price) 计算，完全不知道缓存价格。DeepSeek V4 Pro 缓存命中只要 $0.0145/M（97% off），但定价表看不出来。

同时 PRICING 只有 25 个模型，缺 Kimi/Minimax/豆包/LongCat/MiMo/百度等。

## Decision

- PRICING 从 `dict[str, tuple]` 重构为 `dict[str, ModelPrice]`（含 input, cache_read, output, cache_write）
- 扩展到 45 个模型
- estimate_cost 从 `float` 改为 `(cost, saved, hit_rate)` 三元组
- record_cost 自动计算 cache_saved

## Why

- 不同模型缓存折扣差距极大（DeepSeek 97% vs Anthropic 90%），不区分缓存价格会导致费用估算严重失真
- cache_saved 字段在 cost.db 中始终为 0，因为没人算——现在自动算
- 模型数量少会导致新 provider 的费用无法追踪

## Consequences

- pricing.json 成为热加载数据源
- 所有调用 estimate_cost 的地方需适配三元组返回值
- 前端费用卡片展示缓存节省金额
