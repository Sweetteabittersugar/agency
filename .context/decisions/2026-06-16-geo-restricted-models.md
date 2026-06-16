# Decision: 涨价模型加 US-only 标注

**Date**: 2026-06-16
**Context**: 2026-06-12 美国商务部禁止 Anthropic Fable 5 / Mythos 5 对非美国用户提供。同时 GLM-5.2 (2026-06-15) 和 MiniMax M3 (2026-06-01) 成为有竞争力的替代品。

**Decision**: 
- models.py PRICING 中 Fable 5 / Mythos 5 标注 `⚠️ US-ONLY: 国内 DeepSeek 路由不可达`
- 不改动路由逻辑（两个模型永远不会被选中除非用户手动指定）
- 等待 API 定价确认后更新 GLM-5.2 估算值

**Why**: 
- 用户通过 DeepSeek 路由接入，Fable/Mythos 不可达
- 标注防止有人选了这两个模型后发现不可用
- GLM-5.2 的 Coding Plan 免费订阅可能成为性价比最优方案

**Consequences**:
- pricing.json 同步更新
- 后续需关注：美国出口管制是否会扩展到更多模型
