# AGENTS.md — Agent 路由矩阵与使用指南

> everythingclaudecode 的核心编排层。收到任务 → 路由矩阵判断 → 自动选择最佳 Agent。

## 路由矩阵

| 关键词 | Agent | 说明 |
|--------|-------|------|
| 写/改/重构/代码/实现/开发 | `coder` | 直接写代码，不反问不转派 |
| 查/搜/找/定位/分析/grep | `explorer` | 只读搜索，不修改文件 |
| 审查/review/检查（通用） | `code-reviewer` | 四维度通用代码审查 |
| 审查 Python/Django/FastAPI | `python-reviewer` | Python 生态专项审查 |
| 审查 Go | `go-reviewer` | Go 生态专项审查 |
| 审查 TypeScript/React/Node | `typescript-reviewer` | TS/JS 生态专项审查 |
| 安全/审计/漏洞 | `security-reviewer` | 深度安全审查 |
| 测试/验证/跑/确认/test | `test-runner` | 执行测试，报告结果 |
| 构建报错/编译失败/依赖冲突 | `build-error-resolver` | 构建错误增量修复 |
| 写小说/章节/大纲/人物/世界观 | `webnovel-writer` | 创作工作流 |
| 清理死代码/重复/未用依赖 | `refactor-cleaner` | 安全删除，不做功能重构 |
| 更新文档/README/CHANGELOG | `doc-updater` | 代码改完文档跟着改 |
| 通用/整理/配置/杂务 | `general-worker` | 非专业领域任务 |
| 规划/设计/架构/方案 | `planner` | 先规划再执行 |
| 查费用/用量/成本/@cost | `cost-analyst` | API 费用分析 |
| 模糊/复合意图 | 反问用户 | 不猜测，先澄清 |

## 任务分级

| 级别 | 标准 | 执行方式 |
|------|------|----------|
| **轻活** | 单文件读写、搜索、简单编辑、一句话回答 | Agent 工具直调 |
| **重活** | 3+ 文件写操作、worktree 隔离、代码重构、功能开发 | dispatch.py 调度 |

判断标准：涉及 3+ 文件的写操作或需要隔离执行环境 → 重活。

## Agent 规格

### 通用格式

每个 agent 文件 (`agents/*.md`) 遵循统一结构：

```markdown
# Agent 名称 — 一句话描述

## 角色
（这个 agent 是什么、负责什么）

## 核心能力 / 审查维度
- 能力项

## 使用场景
- 什么时候用 / 什么时候不用

## 输出格式
（STATUS + 详细结果 + 用户摘要）
```

### 现有 Agent 清单

| 文件 | Agent | 类型 | 适合模型 |
|------|-------|------|----------|
| `coder.md` | 代码执行者 | 生产 | deepseek-v4 / sonnet |
| `code-reviewer.md` | 代码审查员（通用） | 生产 | sonnet |
| `python-reviewer.md` | Python 审查员 | 生产 | sonnet |
| `go-reviewer.md` | Go 审查员 | 生产 | sonnet |
| `typescript-reviewer.md` | TypeScript 审查员 | 生产 | sonnet |
| `security-reviewer.md` | 安全审计员 | 生产 | sonnet |
| `explorer.md` | 代码探索员 | 生产 | haiku |
| `test-runner.md` | 测试执行员 | 生产 | haiku |
| `build-error-resolver.md` | 构建错误修复 | 生产 | sonnet |
| `general-worker.md` | 通用执行者 | 生产 | sonnet |
| `webnovel-writer.md` | 小说作家 | 生产 | opus |
| `planner.md` | 规划架构师 | 生产 | sonnet / opus |
| `cost-analyst.md` | 费用分析师 | 生产 | haiku |
| `doc-updater.md` | 文档更新员 | 生产 | haiku |
| `refactor-cleaner.md` | 代码清理员 | 生产 | sonnet |

## 混合派发策略

```
用户消息 → 意图解析
    ├── 单意图 + 轻活 → 直接 Agent
    ├── 单意图 + 重活 → dispatch.py
    ├── 多意图 + 独立 → 并行 Agent
    ├── 多意图 + 依赖 → 串行 Agent（pipeline）
    └── 无法分类 → 反问用户
```

## 结果网关

Agent 完成后的处理流程：

1. Agent 写入结果文件（STATUS + 详细结果 + 用户摘要）
2. 网关提取 STATUS 行和 `## 用户摘要` 段
3. 仅向用户展示精简摘要
4. 如需确认：显示 `[Agent名] 需要确认: <问题>`

## 添加新 Agent

1. 在 `agents/` 下创建 `your-agent.md`
2. 遵循通用格式
3. 在本文档的路由矩阵中添加条目
4. 在 `maestro/agents.json` 中注册（如使用 dispatch 系统）
