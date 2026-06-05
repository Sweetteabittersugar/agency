# 贡献指南

> 感谢你对 agency-kit 的关注！这份指南会帮你了解如何参与贡献。

## 参与方式

| 方式 | 适合人群 | 说明 |
|------|----------|------|
| **提交 Issue** | 所有人 | 报告 bug、建议功能、提出问题 |
| **提交 PR** | 开发者 | 修复代码、新增功能、改进文档 |
| **贡献 Agent** | 进阶用户 | 提交新的专业子代理 |
| **贡献 Skill** | 进阶用户 | 提交新的工作流技能 |
| **贡献 Command** | 进阶用户 | 提交新的快捷命令 |
| **贡献 Rule** | 进阶用户 | 提交新的工程规范 |

## 开发环境搭建

**前提条件**：Python 3.10+、Git、Claude Code（已安装并配置）、Git Bash（Windows）或 bash（macOS/Linux）

```bash
git clone https://github.com/Sweetteabittersugar/agency.git
cd agency
./install.sh        # macOS / Linux / Git Bash（或 .\install.ps1 for Windows）
python -m pytest tests/ -v   # 验证安装
```

## Agent 贡献格式

放置在 `agents/` 下，为 Markdown 文件。**必须包含 YAML frontmatter**：

```markdown
---
name: your-agent-name
description: 一句话描述 Agent 的职责
model: sonnet
tools: Read, Write, Edit, Bash, Glob, Grep
---

# Agent 名称 — 一句话描述

## 角色
这个 agent 是什么、负责什么

## 核心能力
- 能力项 1
- 能力项 2

## 使用场景
- 什么时候用 / 什么时候不用

## 输出格式
STATUS 行 + 详细结果 + ## 用户摘要
```

**要求**：文件名 `agent-name.md`（英文小写，连字符分隔）；frontmatter 中 `name`、`description`、`model` 必填；至少包含角色、使用场景、输出格式三个章节；保持 200 行以内。

## Skill 贡献格式

放置在 `skills/` 下，每个 skill 为一个子目录：

```
skills/your-skill/
├── skill.md          ← 入口：名称、触发条件、执行流程
└── ...               ← 辅助文件（可选）
```

`skill.md` 需包含：触发条件、执行流程、输出规范（STATUS + 用户摘要）。

## Command 贡献格式

放置在 `commands/` 下，为一个 Markdown 文件。文件名即命令名（如 `status.md` 对应 `@status`）。内容简洁列出所有用法变体：

```markdown
- `@command` → 基本用法
- `@command --flag` → 带参数用法
- `python maestro/xxx.py` → 直接调用方式
```

## Rule 贡献格式

放置在 `rules/` 下，为一个 Markdown 文件。通用规范放根目录，语言特定规范放对应子目录（`rules/python/` 等）。开头注明所属层级和简要说明：

```markdown
# 规范标题 — 简要说明

> Layer N: 所属层级 | 说明

## 具体规则
- 规则 1
- 规则 2
```

## Commit 规范

本项目遵循约定式提交（Conventional Commits）：

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 新增压缩前钩子` |
| `fix` | Bug 修复 | `fix: 修复 cost-tracker 时区错误` |
| `refactor` | 重构 | `refactor: 提取 dispatch 路由逻辑` |
| `docs` | 文档 | `docs: 补充 Agent 贡献格式说明` |
| `test` | 测试 | `test: 添加 sandbox 隔离测试` |
| `chore` | 杂务 | `chore: 更新 .gitignore` |
| `perf` | 性能优化 | `perf: 减少 dispatch.py 启动时间` |
| `ci` | CI/CD | `ci: 添加自动测试流水线` |

## PR 流程

1. **Fork 仓库**，从 `main` 分支创建功能分支
2. **开发 + 测试**：确保 `python -m pytest tests/ -v` 通过
3. **提交**：遵循 Commit 规范，保持提交历史清晰
4. **创建 PR**：标题遵循约定式提交格式；描述中包含做了什么、为什么这样做、测试情况；关联相关 Issue（如有）
5. **代码审查**：维护者会在 3 个工作日内审查
6. **合并**：审查通过后由维护者合并

## 代码风格要求

- **Python**：遵循 PEP 8，使用 `black` + `isort` + `ruff`
- **Shell**：遵循 ShellCheck 规范，使用 `#!/usr/bin/env bash`
- **Markdown**：中文与英文/数字之间加空格

## 行为准则

参与本项目即表示同意遵守[贡献者行为准则](CODE_OF_CONDUCT.md)。

---

再次感谢你的贡献！如有疑问，欢迎在 Issue 中提出。
