# Agent 使用说明

## 路由规则

当你发送消息时，系统根据关键词自动选择最合适的 Agent：

| 你说的 | 调用的 Agent |
|--------|-------------|
| "帮我写一个..."、"重构..."、"实现..." | `coder` |
| "查一下..."、"找..."、"搜索..." | `explorer` |
| "审查这个代码"、"review" | `code-reviewer` |
| "安全审计"、"检查漏洞" | `security-reviewer` |
| "测试"、"验证"、"跑一下" | `test-runner` |
| "规划"、"设计架构"、"方案" | `planner` |
| "写小说"、"章节"、"大纲" | `webnovel-writer` |
| "查费用"、"@cost" | `cost-analyst` |
| 整理文件、配置、杂务 | `general-worker` |

## 任务级别

- **轻活**（单文件、搜索、简单编辑）→ 直接执行
- **重活**（3+ 文件、重构、功能开发）→ Maestro 调度

## 自定义 Agent

在 `agents/` 下（或按层级放入 L3_decision/L2_specialist/L1_executor/L0_utility）新建 `.md` 文件，格式：

```markdown
# Agent 名称 — 描述

## 角色
（职责说明）

## 核心能力
- 能力1
- 能力2

## 输出格式
...
```

然后在 `AGENTS.md` 的路由矩阵中添加条目即可。
