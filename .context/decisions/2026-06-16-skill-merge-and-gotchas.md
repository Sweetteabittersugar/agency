# Decision: Skill 体系合并重复 + 加 gotchas + 补维度

**Date**: 2026-06-16
**Context**: 审计发现代码审查 skill 分裂为两套（agency/code-review 四维定性 vs ai/code-review-checklist 加权打分），多个 skill 缺乏 gotchas（负面约束），数据获取和运维诊断两个维度完全空白。

**Decision**:
1. 合并为全局 `~/.claude/skills/code-review/`（加权评分制）
2. 删除 agency 和 ai 项目级重复 skill
3. 核心 skill（debug/compress/init/cost/code-review）各加 2-3 条 `🚫` gotchas
4. 新建 `data-fetching` + `ops-diagnosis` 补齐 2 个空白维度

**Why**:
- arXiv 2604.11088 大规模研究：负面约束持续有帮助，正面指令可能默默有害
- Anthropic 官方建议：gotchas 是 skill 中信号密度最高的内容
- 审查标准分裂会导致不同项目行为不一致

**Consequences**:
- 全局 code-review 为唯一审查入口
- 新增 2 个 skill 覆盖 8/9 维度（runbooks 仍空白）
- 后续需：给 paper-reading/docx 等大 skill 也加 gotchas
