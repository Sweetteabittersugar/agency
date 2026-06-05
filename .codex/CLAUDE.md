# everythingclaudecode for Codex CLI

Codex CLI 适配层。将 everythingclaudecode 的 agents/rules/skills 映射到 Codex 的 agent 系统。

## 概述

everythingclaudecode 原本为 Claude Code 设计，但大部分规范和 Agent 工作流可以通过适配层在 Codex CLI 中复用。

## Agent 映射

| ECC Agent | Codex Role | 说明 |
|-----------|-----------|------|
| coder | developer | 代码编写，直接让 Codex 执行 |
| code-reviewer | reviewer | 代码审查，Codex 自带审查能力 |
| explorer | developer (readonly) | 只读搜索，使用 Codex 的代码理解 |
| test-runner | developer | 测试执行，Codex 可以运行测试 |
| general-worker | developer | 通用任务 |
| planner | architect | 架构规划，Codex 支持 |
| security-reviewer | security | 安全审查 |
| cost-analyst | — | 费用分析，需保留 Python 脚本 |

## Rule 映射

everythingclaudecode 的规则文件（`rules/` 目录）可复制到 Codex 的配置中：

```
~/.codex/
├── rules/
│   ├── coding-style.md    ← rules/common/coding-style.md
│   ├── testing.md          ← rules/common/testing.md
│   ├── security.md         ← rules/common/security.md
│   └── git-workflow.md    ← rules/common/git-workflow.md
```

语言特定规则同样适用：
```
~/.codex/rules/
├── python/     ← rules/python/
├── typescript/ ← rules/typescript/
└── golang/     ← rules/golang/
```

## Skill 映射

| ECC Skill | Codex 等效 | 说明 |
|-----------|-----------|------|
| /design | Codex 内置规划 | Codex 有类似的逐步澄清流程 |
| /compress | Codex 自动管理 | Codex 自行管理上下文 |
| @cost | 需保留脚本 | 复制 maestro/cost-tracker.py 到项目 |
| @status | 需保留脚本 | 复制 maestro/dispatch.py --status |

## Maestro 调度引擎

Codex CLI 有自己的 Agent 调度机制，Maestro 的 dispatch.py 不能直接使用。

替代方案：
1. 保留 `maestro/cost-tracker.py` 和 `maestro/cost-analyzer.py` 用于费用追踪
2. 保留 `maestro/task-tracker.py` 用于任务看板
3. Agent 调度交给 Codex 自己的系统

## 安装步骤

```bash
# 1. 复制规则文件
cp -r everythingclaudecode/rules/common ~/.codex/rules/
cp -r everythingclaudecode/rules/python ~/.codex/rules/
cp -r everythingclaudecode/rules/typescript ~/.codex/rules/
cp -r everythingclaudecode/rules/golang ~/.codex/rules/

# 2. 复制费用追踪脚本（保留 Python 脚本部分）
mkdir -p your-project/maestro
cp everythingclaudecode/maestro/cost-tracker.py your-project/maestro/
cp everythingclaudecode/maestro/cost-analyzer.py your-project/maestro/

# 3. 在项目中引用规则
# 在项目的 CLAUDE.md 或 .codex.md 中添加：
# > 规则见 ~/.codex/rules/
```

## 限制

- Codex CLI 不支持 Claude Code 的 hooks 系统，SessionStart/PostToolUse 等 hook 不可用
- PreCompact hook 不可用（Codex 自行管理压缩）
- dispatch.py 调度不可用（使用 Codex 自己的任务系统）
- agents.json 配置不兼容（Agent 定义格式不同）
