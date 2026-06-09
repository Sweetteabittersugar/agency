# AGENTS.md — Agent 路由矩阵与使用指南

> agency-kit 的核心编排层。收到任务 → 路由矩阵判断 → 自动选择最佳 Agent。

## 路由矩阵

| 关键词 | Agent | 说明 |
|--------|-------|------|
| 写/改/重构/代码/实现/开发/死代码/清理/简化 | `coder` | 直接写代码，含代码清理，不反问不转派 |
| 查/搜/找/定位/分析/grep | `explorer` | 只读搜索，不修改文件 |
| 审查/review/检查（通用） | `code-reviewer` | 四维度通用代码审查 |
| 审查 Python/Django/FastAPI | `python-reviewer` | Python 生态专项审查 |
| 审查 Go | `go-reviewer` | Go 生态专项审查 |
| 审查 TypeScript/React/Node | `typescript-reviewer` | TS/JS 生态专项审查 |
| 安全/审计/漏洞 | `security-reviewer` | 深度安全审查 |
| 数据库/SQL/Schema/索引 | `database-reviewer` | SQL 性能与 Schema 审查 |
| 测试/验证/跑/确认/test/测试策略/边界用例/回归 | `test-runner` | 执行测试、测试策略、边界用例，报告结果 |
| TDD/测试先行/红绿重构 | `tdd-guide` | TDD 五步循环向导 |
| E2E/端到端/Playwright/浏览器测试 | `e2e-runner` | Playwright 端到端测试 |
| 构建报错/编译失败/依赖冲突 | `build-error-resolver` | 构建错误增量修复 |
| 写小说/章节/大纲/人物/世界观 | `webnovel-writer` | 创作工作流 |
| 更新文档/README/CHANGELOG | `doc-updater` | 代码改完文档跟着改 |
| 通用/整理/配置/杂务 | `general-worker` | 非专业领域任务 |
| 规划/设计/架构/方案 | `planner` | 先规划再执行 |
| 查费用/用量/成本/@cost | `cost-analyst` | API 费用分析 |
| 性能/瓶颈/优化/慢查询 | `performance-optimizer` | 性能瓶颈分析与优化 |
| 调度/编排/多Agent协作/拆解任务 | `orchestrator` | 复杂任务拆解与多Agent协作 |
| 产品决策/功能范围/优先级/验收 | `ceo` | 产品决策与验收 |
| CI/CD/Docker/部署/环境 | `devops` | CI/CD 与基础设施 |
| 发版/发布/CHANGELOG/版本管理 | `release-manager` | 版本管理与发布检查 |
| 系统设计/架构设计/技术选型/接口设计 | `architect` | 软件架构师，只出方案不写代码 |
| 调试/debug/排查bug/根因分析 | `debugger` | 证据驱动诊断，不修复只诊断 |
| 验证改动/检查修复/确认修复 | `verifier` | 独立验证改动是否解决问题 |
| 界面设计/UI设计/UX设计/交互设计 | `designer` | UI/UX 设计，可生成原型 |
| 生成测试/写测试用例/单元测试生成 | `test-generator` | 自动生成测试，不运行 |
| 评估输出/质量检查/输出审查 | `critic` | 三维评估 Agent 输出，放行或打回 |
| 压缩上下文/摘要/记忆管理 | `memory-keeper` | 长任务摘要，上下文压缩 |
| 路由/意图识别/agent选择 | `router` | 智能路由，成本优化 |
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
| `coder.md` | 代码执行者+清理员 | 生产 | deepseek-v4 / sonnet |
| `code-reviewer.md` | 代码审查员（通用） | 生产 | sonnet |
| `python-reviewer.md` | Python 审查员 | 生产 | sonnet |
| `go-reviewer.md` | Go 审查员 | 生产 | sonnet |
| `typescript-reviewer.md` | TypeScript 审查员 | 生产 | sonnet |
| `security-reviewer.md` | 安全审计员 | 生产 | sonnet |
| `database-reviewer.md` | 数据库审查员 | 生产 | sonnet |
| `explorer.md` | 代码探索员 | 生产 | haiku |
| `test-runner.md` | 测试执行员+策略 | 生产 | haiku |
| `tdd-guide.md` | TDD 向导 | 生产 | sonnet |
| `e2e-runner.md` | E2E 测试专家 | 生产 | sonnet |
| `build-error-resolver.md` | 构建错误修复 | 生产 | sonnet |
| `general-worker.md` | 通用执行者 | 生产 | sonnet |
| `webnovel-writer.md` | 小说作家 | 生产 | opus |
| `planner.md` | 规划架构师 | 生产 | sonnet / opus |
| `cost-analyst.md` | 费用分析师 | 生产 | haiku |
| `doc-updater.md` | 文档更新员 | 生产 | haiku |
| `performance-optimizer.md` | 性能优化师 | 生产 | sonnet |
| `orchestrator.md` | 总调度 | 生产 | sonnet |
| `ceo.md` | 产品决策者 | 生产 | sonnet |
| `devops.md` | DevOps 工程师 | 生产 | sonnet |
| `release-manager.md` | 发布经理 | 生产 | haiku |
| `lead.md` | 任务领导者 | 生产 | sonnet |
| `architect.md` | 软件架构师 | 新增 | opus |
| `debugger.md` | 调试专家 | 新增 | sonnet |
| `verifier.md` | 实施验证员 | 新增 | sonnet |
| `designer.md` | UI/UX 设计师 | 新增 | sonnet |
| `test-generator.md` | 测试生成器 | 新增 | sonnet |
| `critic.md` | 输出评估员 | 新增 | sonnet |
| `memory-keeper.md` | 记忆管理者 | 新增 | haiku |
| `router.md` | 智能路由器 | 新增 | haiku |

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
