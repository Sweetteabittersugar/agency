# Decision: Token 估算加 Provider 修正系数

**Date**: 2026-06-15
**Status**: accepted
**Supersedes**: (replaces 统一的 len(task)//4 估算)

## Context

v2 实现了缓存感知定价，但命中率计算有致命精度问题：cache_hit_rate = cache_read / in_tokens。当 in_tokens 来自 API 时正确；来自 len(task)//4 估算时严重失真——同一中文句子 Claude 报 22 tokens，估算只给 4。

## Decision

- ModelPrice 加 tok_per_char 字段（每个模型的 tokenizer 系数）
- 新增 estimate_tokens() 替代全部 len(task)//4
- tokens_from_api 标记区分 API 真实值和估算值

## Why

不同 tokenizer 对同一文本的 token 数可差 3 倍（Claude 中文 ~0.8 tok/字 vs Qwen ~0.3 tok/字），用统一系数算命中率完全是垃圾数据。

## Consequences

- 45 个模型全部填充 tok_per_char（来源：极客公园 22 段平行文本实测）
- 前端命中率加 ~ 前缀表示估算值
