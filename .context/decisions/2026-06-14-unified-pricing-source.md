# Decision: 统一切到 Claude total_cost_usd

**Date**: 2026-06-14
**Status**: accepted
**Supersedes**: (none — new decision)

## Context

Agency 有两套计费逻辑：chat.py 用 Claude 报的 `total_cost_usd`（API 实际扣费），ws_chat.py 用 `estimate_cost()` 自己算（PRICING 字典手动维护）。后者参数还传错了（model 名当 project_root 传），导致 ws_chat 的费用全部丢失。

## Decision

**Claude Code 的 `result.total_cost_usd` 是唯一计费源头。`estimate_cost()` 降级为纯 fallback——只在读历史 JSONL（无 Claude 进程）时使用。**

## Why

- Claude 报的是 API 实际扣费金额，天然准确，包含缓存折扣
- 自己用 PRICING 字典算是重复劳动，且手动维护必然滞后于官方调价
- 两套逻辑打架会导致聚合统计时出现两套不一致的数字

## Consequences

- ws_chat.py 不再调用 estimate_cost，改为读 done_data['cost']
- record_cost 参数按签名对齐（project_root, time_str, model, ...）
- 新增 is_estimated 标记，区分 API 真实值和 fallback 估算
