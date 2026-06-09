# AGENTS.md — Agent 路由矩阵与使用指南

> agency-kit 的核心编排层。收到任务 → 路由矩阵判断 → 自动选择最佳 Agent。

## 路由矩阵

> 33 个 Agent，按 12 大类组织。路由先定类再选 Agent：高置信度直派 / 中置信度列候选 / 低置信度反问。

### 架构设计
| 关键词 | Agent | 说明 |
|--------|-------|------|
| 系统设计/架构设计/技术选型/接口设计 | `architect` | 软件架构师，只出方案不写代码 |
| API设计/REST/GraphQL/gRPC/接口规范 | `api-designer` | API 架构设计与规范制定 |

### 编码实现
| 关键词 | Agent | 说明 |
|--------|-------|------|
| 写/改/重构/代码/实现/开发/死代码/清理/简化 | `coder` | 直接写代码，含代码清理 |
| 构建报错/编译失败/依赖冲突 | `build-error-resolver` | 构建错误增量修复 |
| 性能/瓶颈/优化/慢查询 | `performance-optimizer` | 性能瓶颈分析与优化 |

### 审查验证
| 关键词 | Agent | 说明 |
|--------|-------|------|
| 审查/review/检查（通用） | `code-reviewer` | 多维度通用代码审查（含各语言） |
| 评估输出/质量检查/输出审查 | `critic` | 三维评估 Agent 输出，放行或打回 |

### 测试质量
| 关键词 | Agent | 说明 |
|--------|-------|------|
| 测试/验证/跑/确认/test/测试策略/边界用例/回归 | `test-runner` | 执行测试、测试策略，报告结果 |
| TDD/测试先行/红绿重构/生成测试/写测试用例 | `tdd-guide` | TDD 五步循环向导（含测试生成） |
| E2E/端到端/Playwright/浏览器测试 | `e2e-runner` | Playwright 端到端测试 |
| 验证改动/检查修复/确认修复 | `verifier` | 独立验证改动是否解决问题 |

### 安全防护
| 关键词 | Agent | 说明 |
|--------|-------|------|
| 安全/审计/漏洞 | `security-reviewer` | 深度安全审查 |
| 渗透/攻击/红队/攻防 | `pentester` | 安全渗透测试 |
| 密钥/泄露/敏感信息/扫描 | `secret-scanner` | 密钥泄露检测与轮换建议 |
| 事故/应急/on-call/宕机 | `incident-responder` | 事故响应与根因分析 |

### 运维部署
| 关键词 | Agent | 说明 |
|--------|-------|------|
| CI/CD/Docker/部署/环境 | `devops` | CI/CD 与基础设施 |
| 发版/发布/CHANGELOG/版本管理 | `release-manager` | 版本管理与发布检查 |
| 监控/日志/追踪/可观测/告警 | `observability-engineer` | 监控/日志/分布式追踪 |

### 数据工程
| 关键词 | Agent | 说明 |
|--------|-------|------|
| ETL/数据管道/数仓/数据清洗 | `data-engineer` | 数据管道与 ETL 工程 |
| 数据库/SQL/Schema/索引/查询优化 | `database-optimizer` | SQL 性能与 Schema 优化 |

### 前端交互
| 关键词 | Agent | 说明 |
|--------|-------|------|
| 界面设计/UI设计/UX设计/交互设计 | `designer` | UI/UX 设计，可生成原型 |
| 无障碍/WCAG/ARIA/a11y/包容性 | `a11y-expert` | WCAG 无障碍审计 |

### 编排调度
| 关键词 | Agent | 说明 |
|--------|-------|------|
| 调度/编排/多Agent协作/拆解任务 | `orchestrator` | 复杂任务拆解与多Agent协作 |
| 路由/意图识别/agent选择 | `router` | 智能路由，成本优化 |
| 规划/设计/方案/计划 | `planner` | 先规划再执行 |
| 带队/领导/统筹 | `lead` | 多 Agent 任务领导者 |

### 文档知识
| 关键词 | Agent | 说明 |
|--------|-------|------|
| 更新文档/README/CHANGELOG | `doc-updater` | 代码改完文档跟着改 |
| 压缩上下文/摘要/记忆管理 | `memory-keeper` | 长任务摘要，上下文压缩 |
| 知识聚合/跨会话/研究综述 | `knowledge-synthesizer` | 跨会话知识聚合与梳理 |

### 探查搜索
| 关键词 | Agent | 说明 |
|--------|-------|------|
| 查/搜/找/定位/分析/grep | `explorer` | 只读搜索，不修改文件 |
| 调试/debug/排查bug/根因分析 | `debugger` | 证据驱动诊断，不修复只诊断 |

### 通用工具
| 关键词 | Agent | 说明 |
|--------|-------|------|
| 通用/整理/配置/杂务 | `general-worker` | 非专业领域任务 |
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

### 现有 Agent 清单（33 个，12 大类）

| 分类 | Agent 文件 | 说明 | 适合模型 |
|------|-----------|------|----------|
| 架构设计 | `architect.md` | 软件架构师，只出方案不写代码 | opus |
| 架构设计 | `api-designer.md` | API 架构设计与规范 | sonnet |
| 编码实现 | `coder.md` | 代码执行者+清理员 | deepseek-v4 / sonnet |
| 编码实现 | `build-error-resolver.md` | 构建错误修复 | sonnet |
| 编码实现 | `performance-optimizer.md` | 性能优化师 | sonnet |
| 审查验证 | `code-reviewer.md` | 代码审查员（通用） | sonnet |
| 审查验证 | `critic.md` | 输出评估员 | sonnet |
| 测试质量 | `test-runner.md` | 测试执行员+策略 | haiku |
| 测试质量 | `tdd-guide.md` | TDD 向导（含测试生成） | sonnet |
| 测试质量 | `e2e-runner.md` | E2E 测试专家 | sonnet |
| 测试质量 | `verifier.md` | 实施验证员 | sonnet |
| 安全防护 | `security-reviewer.md` | 安全审计员 | sonnet |
| 安全防护 | `pentester.md` | 安全渗透测试专家 | sonnet |
| 安全防护 | `secret-scanner.md` | 密钥泄露检测 | haiku |
| 安全防护 | `incident-responder.md` | 事故响应专家 | sonnet |
| 运维部署 | `devops.md` | DevOps 工程师 | sonnet |
| 运维部署 | `release-manager.md` | 发布经理 | haiku |
| 运维部署 | `observability-engineer.md` | 可观测性工程师 | sonnet |
| 数据工程 | `data-engineer.md` | 数据工程师 | sonnet |
| 数据工程 | `database-optimizer.md` | 数据库优化师 | sonnet |
| 前端交互 | `designer.md` | UI/UX 设计师 | sonnet |
| 前端交互 | `a11y-expert.md` | 无障碍审计专家 | sonnet |
| 编排调度 | `orchestrator.md` | 总调度 | sonnet |
| 编排调度 | `router.md` | 智能路由器 | haiku |
| 编排调度 | `planner.md` | 规划架构师 | sonnet / opus |
| 编排调度 | `lead.md` | 任务领导者 | sonnet |
| 文档知识 | `doc-updater.md` | 文档更新员 | haiku |
| 文档知识 | `memory-keeper.md` | 记忆管理者 | haiku |
| 文档知识 | `knowledge-synthesizer.md` | 知识合成师 | haiku |
| 探查搜索 | `explorer.md` | 代码探索员 | haiku |
| 探查搜索 | `debugger.md` | 调试专家 | sonnet |
| 通用工具 | `general-worker.md` | 通用执行者 | sonnet |
| 通用工具 | `cost-analyst.md` | 费用分析师 | haiku |

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
