# Agent Context Protocol

> 每个 Agent（包括你自己）在改动项目前必须读这个文件。

## 会话开始（必做）

1. **读 handoff** → `.context/handoff.md` 了解上次状态
2. **读 backlog** → `.context/BACKLOG.md` 看有什么待做的
3. **读决策日志** → `ls .context/decisions/` 找相关决策
4. **读错误日志** → `.context/mistakes/` 避免重复踩坑

## 会话中（随时）

- **想到新功能/改进但没空做** → 立即写 `.context/BACKLOG.md`（不要靠脑子记）
- **做了架构级决策** → 写 `.context/decisions/YYYY-MM-DD-<slug>.md`
- **踩了坑** → 写 `.context/mistakes/<slug>.md`

## 会话结束（必做）

1. **更新 handoff** → `.context/handoff.md`（状态、已知问题、下一步）
2. **更新 backlog** → 把本次完成的事项移到"已完成"

## 决策格式

```markdown
# Decision: <一句话总结>

**Date**: YYYY-MM-DD
**Status**: proposed | accepted | deprecated | superseded
**Supersedes**: (link to old decision, or "none")

## Context
为什么需要做这个决策？什么触发了它？

## Decision
做了什么选择？

## Why
为什么选 A 不选 B？考虑过哪些替代方案？

## Consequences
这个决策会导致什么后续影响？
```

## Handoff 格式

```markdown
# Handoff — YYYY-MM-DD HH:MM

## 上次做了什么
- 

## 当前状态
- Branch: 
- 未提交改动: 
- 已知问题: 

## 下一步
- 

## 关键上下文
- （任何接手的人需要知道的）
```

## 关键规则

- **不要猜测之前为什么这样做** → 去 `.context/decisions/` 查
- **不要在没读 decisions 的情况下推翻已有设计** → 如果确实要改，写新 decision supersede 旧的
- **不要把决策放在脑子里** → 写下来，下一个 Agent 看不到你脑子里的事
