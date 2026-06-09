# Agent + Skill 体系全面优化方案

> 2026-06-09 | 基于：内部审计 + 行业调研 + SWEBOK + Claude Code 生态

---

## 一、现状诊断

### 核心数据

| 指标 | 当前 | 问题 |
|------|------|------|
| Agent 总数 | 31 | 文档称 24，数量不准 |
| 有 Skill 绑定的 Agent | 6 (19%) | 25 个 Agent 裸奔 |
| 被引用的 Skill | 10/60 (17%) | 83% 的 Skill 闲置 |
| 有 category 的 Skill | 47/60 (78%) | 22% 无分类 |
| Agent 无 category 字段 | 31/31 (100%) | 全部扁平，无法分类路由 |
| router.md | 10 行 | 路由核心几乎为空 |
| 安全 Agent | 1 个 | 严重不足 |

### 三大根因

1. **Agent 和 Skill 是两套独立系统**——各长各的，没有打通
2. **无分类体系**——31 Agent 扁平列表，路由靠关键词碰运气
3. **文档腐败**——CLAUDE.md/AGENTS.md 与实际 agent.yaml 不同步

---

## 二、分类体系 — 对齐 SWEBOK V4

SWEBOK V4 定义了 18 个知识领域。我们的分类对齐其中 10 个最相关的，外加 2 个 AI 原生领域。

### Agent 分类（12 大类）

| 分类 ID | 分类名 | SWEBOK 对齐 | 当前 Agent | 应增/减 |
|---------|--------|------------|-----------|---------|
| `architecture` | 架构设计 | KA2 Architecture | architect | +1 (api-designer) |
| `implementation` | 编码实现 | KA3 Design + KA4 Construction | coder, build-error-resolver, performance-optimizer | +3 (lang specialists) |
| `review` | 审查验证 | KA12 Quality | code-reviewer, critic | 合并 4 个语言审查者 |
| `testing` | 测试质量 | KA5 Testing | test-runner, e2e-runner, tdd-guide, test-generator, verifier | 合并 test-generator→tdd-guide |
| `security` | 安全防护 | KA13 Security ✨ | security-reviewer | +3 (pentest/secret/incident) |
| `devops` | 运维部署 | KA6 Operations ✨ + KA7 Maintenance | devops, release-manager | +1 (observability) |
| `data` | 数据工程 | KA16 Computing Foundations | — | +2 (data-engineer, db-optimizer) |
| `frontend` | 前端交互 | KA14 Professional Practice | designer | +1 (a11y) |
| `orchestration` | 编排调度 | 无直接对应(AI 原生) | orchestrator, router, planner, lead, ceo | 合并 ceo→lead |
| `documentation` | 文档知识 | KA7 Maintenance | doc-updater, memory-keeper | +1 (knowledge-synthesizer) |
| `exploration` | 探查搜索 | 无直接对应(AI 原生) | explorer, debugger | 保持 |
| `utility` | 通用工具 | KA15 Economics + KA10 Process | cost-analyst, general-worker | 保持 |

### 分类后的 Agent 名单（32 → 33）

```
architecture/    architect, api-designer
implementation/  coder, python-pro, golang-pro, typescript-pro, backend-developer, build-error-resolver, performance-optimizer
review/          code-reviewer, critic
testing/         test-runner, e2e-runner, tdd-guide, verifier
security/        security-reviewer, pentester, secret-scanner, incident-responder
devops/          devops, release-manager, observability-engineer
data/            data-engineer, database-optimizer
frontend/        designer, a11y-expert
orchestration/   orchestrator, router, planner, lead
documentation/   doc-updater, memory-keeper, knowledge-synthesizer
exploration/     explorer, debugger
utility/         cost-analyst, general-worker
```

### 删除（2）
| Agent | 理由 |
|-------|------|
| python-reviewer | 合并进 code-reviewer（审查逻辑相同，语言知识在 skill 中） |
| go-reviewer | 同上 |
| typescript-reviewer | 同上 |
| webnovel-writer | 非软件工程领域，移出核心（保留文件但不注册路由） |
| ceo | 与 lead 职责重叠，合并 |
| test-generator | 与 tdd-guide 重叠，合并 |

### 新增（3）
| Agent | 理由 |
|-------|------|
| api-designer | REST/GraphQL API 设计，行业标配 |
| pentester | 安全渗透测试，补安全领域短板 |
| observability-engineer | 监控/日志/分布式追踪，补 DevOps 短板 |
| data-engineer | ETL/数据管道，补数据领域空白 |
| a11y-expert | WCAG 无障碍审计 |
| knowledge-synthesizer | 跨会话知识聚合，对齐 Memory Keeper |

---

## 三、Skill 体系 — 三层架构 + SWEBOK 知识注入

### 3.1 架构：三层 Skill

```
Layer A: 核心 Skill (required)    → agent 启动必装，提示词级注入
Layer B: 专业 Skill (on-demand)   → trigger 匹配时加载
Layer C: 工具 Skill (never)       → 用户手动调用，不自动加载
```

### 3.2 Skill 按 SWEBOK 知识领域重组

当前 60 个 Skill，优化后 48 个（删 12 重叠 + 重分类）

#### KA2 架构设计
| Skill | 层级 | 说明 |
|-------|------|------|
| `architecture-patterns` | B | 分层/微服务/事件驱动等模式选择指南 |
| `api-design` | B | RESTful/GraphQL/gRPC API 设计规范 |
| `database-design` | B | 数据库范式/索引/分片设计 |
| `adr-template` | B | 架构决策记录模板和评审流程 |

#### KA3/4 设计与构造
| Skill | 层级 | 说明 |
|-------|------|------|
| `code-standards` | A | 命名/格式/注释规范（已有，保留） |
| `error-handling-patterns` | B | 异常处理/重试/降级模式（已有） |
| `refactoring-patterns` | B | 提取方法/移动字段/简化条件（已有） |
| `search-first` | A | 先搜索再动手（已有，保留） |
| `dependency-management` | B | 依赖版本锁定/审计（已有） |

#### KA5 测试
| Skill | 层级 | 说明 |
|-------|------|------|
| `unit-test-patterns` | B | 单元测试 AAA 模式/边界值（已有） |
| `integration-test-patterns` | B | API 测试/数据库测试 fixture（已有） |
| `e2e-test-patterns` | B | Playwright/Cypress 页面对象模式（已有） |
| `mock-factory` | B | Mock/Stub/Fake 生成策略（已有） |
| `test-data-generator` | B | 测试数据工厂/faker 模式（已有） |
| `regression-checklist` | B | 回归测试检查表（已有） |
| `mutation-testing` | C | 变异测试评估测试质量（新增） |

#### KA13 安全 ✨
| Skill | 层级 | 说明 |
|-------|------|------|
| `pre-commit-guard` | A | 提交前密钥扫描/敏感文件检查（已有） |
| `dependency-audit` | B | CVE 扫描 + 许可证审计（已有） |
| `secret-detection` | B | 密钥模式检测+轮换建议（已有） |
| `owasp-top10` | B | OWASP 十大漏洞检查指南（已有） |
| `injection-analysis` | B | SQL/命令/模板注入检测（已有） |
| `authz-patterns` | B | OAuth2/JWT/RBAC 认证授权模式（已有） |
| `threat-modeling` | C | STRIDE 威胁建模流程（新增） |

#### KA6 运维
| Skill | 层级 | 说明 |
|-------|------|------|
| `ci-pipeline` | B | CI/CD 流水线模板（已有） |
| `deployment-checklist` | B | 部署前检查表（已有） |
| `docker-patterns` | B | Dockerfile 最佳实践（已有） |
| `health-check-patterns` | B | 健康检查端点/探针模式（已有） |
| `rollback-plan` | B | 回滚策略和数据兼容性（已有） |
| `infrastructure-as-code` | C | Terraform/Pulumi 模式（新增） |

#### KA12 质量
| Skill | 层级 | 说明 |
|-------|------|------|
| `multi-perspective-review` | A | 正确性/安全/可维护三维审查（已有） |
| `code-review-checklist` | B | 结构化审查清单（新增） |
| `complexity-analysis` | C | 圈复杂度/认知复杂度评估（新增） |

#### 前端领域
| Skill | 层级 | 说明 |
|-------|------|------|
| `component-patterns` | B | 组合/渲染属性/状态提升（已有） |
| `responsive-design` | B | 断点/弹性布局/图片适配（已有） |
| `browser-compat` | B | CanIUse 查询/渐进增强（已有） |
| `a11y-audit` | B | WCAG 2.2/ARIA/键盘导航（已有） |
| `style-guide` | B | 设计令牌/CSS 变量/主题（已有） |
| `performance-budget` | B | Core Web Vitals 性能预算（新增） |

#### 性能领域
| Skill | 层级 | 说明 |
|-------|------|------|
| `caching-strategy` | B | CDN/Redis/浏览器缓存策略（已有） |
| `query-optimization` | B | SQL 执行计划/索引优化（已有） |
| `profiling-guide` | B | CPU/内存火焰图分析（已有） |
| `memory-leak-detection` | B | 内存泄漏检测和修复模式（已有） |
| `bundle-optimization` | C | Tree-shaking/代码分割/懒加载（已有） |

#### AI 原生（Agent 工程）
| Skill | 层级 | 说明 |
|-------|------|------|
| `pipeline-gate` | A | 五阶段门控（已有） |
| `self-healing` | A | 自动错误分类和恢复（已有） |
| `context-budget` | A | Token 预算分配和管理（已有） |
| `changelog-guard` | A | 版本变更记录（已有） |
| `web-fetch` | B | 多源搜索和交叉验证（已有） |
| `cost-aware-pipeline` | B | 成本感知模型选择（已有） |
| `verification-loop` | B | 验证循环和重试（已有） |
| `parallel-execution` | B | 并行任务编排（已有） |
| `regex-over-llm` | B | 确定性任务优先（已有） |

### 3.3 删除的 Skill（12 个）

| Skill | 理由 |
|-------|------|
| humanizer / humanizer-zh | 非软件工程技能，移出核心 |
| claude (CLI 指南) | 过于基础，合并进 code-standards |
| compress | 与 context-compression 重叠，合并 |
| cost | 与 cost-aware-pipeline 重叠 |
| design | 与 architecture-patterns 重叠 |
| handoff | 与 context-compression 重叠 |
| adversarial-review | 与 multi-perspective-review 合并 |
| output-quality-gate | 与 critic Agent 职责重叠 |
| skill-stocktake | 工具性脚本，非 Agent skill |
| update-config | 基础设施脚本 |
| paper-reading | 学术特定，太重(28KB)，移出核心 |
| docx/pdf/xlsx | 文档处理工具，保留但标记为 C 层工具 Skill |

---

## 四、Agent-Skill 绑定矩阵

### 4.1 全量绑定（31→33 Agent，每个至少 2 个 Skill）

| Agent | Required (A 层) | Optional (B 层) | Excluded |
|-------|----------------|-----------------|----------|
| **architect** | architecture-patterns, adr-template | api-design, database-design, web-fetch | — |
| **api-designer** | api-design | architecture-patterns, code-standards | — |
| **coder** | self-healing, code-standards, search-first | pre-commit-guard, context-budget, changelog-guard, refactoring-patterns | — |
| **python-pro** | self-healing, code-standards | profiling-guide, error-handling-patterns | — |
| **golang-pro** | self-healing, code-standards | profiling-guide, error-handling-patterns | — |
| **typescript-pro** | self-healing, code-standards | component-patterns, profiling-guide | — |
| **backend-developer** | self-healing, code-standards | api-design, database-design, caching-strategy | — |
| **build-error-resolver** | self-healing | profiling-guide, dependency-audit | — |
| **performance-optimizer** | profiling-guide | caching-strategy, query-optimization, memory-leak-detection, bundle-optimization | — |
| **code-reviewer** | multi-perspective-review, code-review-checklist | pre-commit-guard, dependency-audit, complexity-analysis | self-healing |
| **critic** | multi-perspective-review | verification-loop | self-healing |
| **test-runner** | unit-test-patterns | integration-test-patterns, e2e-test-patterns, mock-factory, regression-checklist, context-budget | changelog-guard |
| **e2e-runner** | e2e-test-patterns | regression-checklist, browser-compat | changelog-guard |
| **tdd-guide** | unit-test-patterns, mock-factory | test-data-generator, mutation-testing | — |
| **verifier** | verification-loop | regression-checklist, code-review-checklist | changelog-guard |
| **security-reviewer** | pre-commit-guard, dependency-audit, owasp-top10 | secret-detection, injection-analysis, authz-patterns, threat-modeling | changelog-guard |
| **pentester** | owasp-top10, threat-modeling | injection-analysis, authz-patterns, secret-detection | self-healing, changelog-guard |
| **secret-scanner** | secret-detection | pre-commit-guard, dependency-audit | self-healing |
| **incident-responder** | self-healing | rollback-plan, health-check-patterns, profiling-guide | — |
| **devops** | ci-pipeline, deployment-checklist | docker-patterns, health-check-patterns, rollback-plan, infrastructure-as-code | — |
| **release-manager** | changelog-guard, deployment-checklist | rollback-plan, dependency-audit | — |
| **observability-engineer** | health-check-patterns | profiling-guide, caching-strategy | — |
| **data-engineer** | error-handling-patterns | database-design, query-optimization | — |
| **database-optimizer** | query-optimization | database-design, caching-strategy | — |
| **designer** | component-patterns, responsive-design | browser-compat, a11y-audit, style-guide, performance-budget | — |
| **a11y-expert** | a11y-audit | browser-compat, component-patterns | — |
| **orchestrator** | pipeline-gate, context-budget, parallel-execution | self-healing, web-fetch, cost-aware-pipeline | — |
| **router** | search-first | — | — |
| **planner** | pipeline-gate | architecture-patterns, web-fetch, cost-aware-pipeline | — |
| **lead** | pipeline-gate, context-budget | parallel-execution, cost-aware-pipeline | — |
| **doc-updater** | changelog-guard | code-standards, adr-template | — |
| **memory-keeper** | context-budget | context-compression | — |
| **knowledge-synthesizer** | context-budget | web-fetch, adr-template | — |
| **explorer** | search-first, regex-over-llm | web-fetch | — |
| **debugger** | self-healing | profiling-guide, error-handling-patterns, memory-leak-detection | — |
| **cost-analyst** | cost-aware-pipeline | context-budget | — |
| **general-worker** | code-standards | search-first, refactoring-patterns | — |

### 4.2 覆盖效果

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| Agent 有 Skill 绑定 | 6/31 (19%) | 33/33 (100%) |
| Skill 被引用 | 10/60 (17%) | 40+/48 (83%+) |
| Agent 平均 Skill 数 | 0.3 | 4.5 |
| Excluded 规则 | 4 条 | 12 条 |

---

## 五、路由系统升级

### 5.1 router.md 重写要点

当前 10 行→改写为包含：
- 12 分类决策树（先定类，再选 Agent）
- 置信度阈值：高(>80%)直接派 / 中(50-80%)列候选 / 低(<50%)反问用户
- 任务复杂度判定（trivial→直派 / simple→单 Agent / normal→2-3 Agent / complex→orchestrator）
- 关键词不被单一 Agent 垄断（coder 关键词权重降权）
- 模型选择策略（Opus条件：≥2/4条件满足）

### 5.2 agent.yaml 增加 category 字段

```yaml
coder:
  category: implementation
  file: agents/coder.md
  model: sonnet
  ...
```

路由先按 category 缩小候选范围，再按关键词+语义精确匹配。

---

## 六、Prompt 质量标准化

### 6.1 模板规范

每个 Agent .md 须包含以下章节（PLANNER 已做到，推广到全部）：

```markdown
---
name: xxx
description: 一句话
category: xxx
model: sonnet
tools: [...]
skills: {required: [...], optional: [...], excluded: [...]}
---

## 你是
<一句话角色定义>

## 你能做
<3-5 个核心能力，带触发条件>

## 你不能做
<3-5 条明确边界>

## 工作流程
<3-5 步标准流程>

## 输出格式
<结构化输出规范（JSON/Markdown 模板）>

## 约束
- 硬约束（不可违反）
- 软约束（建议遵守）

## 示例
<1-2 个实际使用场景>
```

### 6.2 需要重写的 Agent

| Agent | 当前 | 问题 |
|-------|------|------|
| router | 10 行 | 几乎为空，缺路由逻辑 |
| critic | 很短 | 职责不清，与 code-reviewer 重叠表述不明确 |
| lead | 中等 | 提到异步但无工具支持 |
| general-worker | 很短 | 过于泛化 |
| cost-analyst | 中等 | 缺输出格式 |

### 6.3 Skill 瘦身标准

- A 层 Skill（必装）: <200 行，高密度指令
- B 层 Skill（按需）: <400 行，含完整模式
- C 层 Skill（工具）: 不限，工具性文档
- 每个 Skill 必须包含：Core Rules(3-5条) + 触发条件 + 输出规范

当前超标 Skill：
- docx: 800+ 行 → 拆分为 cheatsheet(C层) + 核心规则(A层)
- paper-reading: 28KB → 移出核心体系

---

## 七、SWEBOK 知识注入

将 SWEBOK 18 个知识领域的核心概念作为 Skill 的 reference 知识库：

| SWEBOK KA | 注入方式 | 目标 Skill |
|-----------|---------|-----------|
| KA1 需求工程 | 需求分析模板、用户故事格式 | `adr-template` |
| KA2 架构设计 | 架构模式目录、质量属性场景 | `architecture-patterns` |
| KA4 软件构造 | 代码质量度量、复杂度阈值 | `code-standards` |
| KA5 测试 | 测试层级(triangle)、覆盖率目标 | 全部 test skill |
| KA8 配置管理 | 语义化版本、分支策略 | `changelog-guard` |
| KA9 工程管理 | 估算技术、风险管理 | `pipeline-gate` |
| KA10 过程 | Agile/Scrum/Kanban 模式 | `parallel-execution` |
| KA12 质量 | 质量模型(CISQ)、技术债务度量 | `code-review-checklist` |
| KA13 安全 | STRIDE 模型、纵深防御 | 全部 security skill |
| KA14 专业实践 | 职业道德、包容性设计 | `a11y-audit` |
| KA15 经济学 | 成本收益分析、决策框架 | `cost-aware-pipeline` |

---

## 八、Skill 自检与质量保障

### 8.1 新增 Skill 时的自动检查

| 检查项 | 触发时机 |
|--------|---------|
| fingerprint 冲突检测 | Skill 安装后 |
| trigger 关键词重叠告警 | Skill 安装后 |
| conflicts_with 交叉验证 | SessionStart |
| 必需 Skill 存在性 | Agent dispatch 前 |
| 每新增 1 个立即检查重复 | 实时（不等攒到 10 个） |

### 8.2 重复处理

1. 完全相同 → 自动合并保留新版
2. 有重叠但不同 → 警告 + 停用旧的
3. 人工声明冲突 → 写入冲突报告待处理

---

## 九、文档同步

| 文件 | 当前 | 改为 |
|------|------|------|
| CLAUDE.md | "24 个专业 Agent" | "33 个 Agent，按 12 大类组织" |
| AGENTS.md | 路由表含过时 Agent | 全量同步新分类体系 |
| profiles.json | 旧描述 | 更新为分类路由兼容 |

---

## 十、实施路线

### 第一批：分类基础设施（1 天）
1. agent.yaml 增加 category 字段（31→33 Agent）
2. 所有 Skill 补全 category
3. router.md 完全重写（10行→完整路由逻辑）
4. CLAUDE.md / AGENTS.md 同步更新

### 第二批：Skill 重组（1 天）
5. 删除 12 个重叠/过时 Skill
6. 新增 6 个缺失领域 Skill（threat-modeling, infrastructure-as-code 等）
7. 瘦身超标 Skill（docx 拆分等）
8. 所有 Skill 补全 Core Rules + 触发条件 + 输出规范

### 第三批：Agent-Skill 打通（1 天）
9. 全量 Agent-Skill 绑定（33 个 Agent × 4.5 Skill）
10. 合并重叠 Agent（删除 python/go/typescript-reviewer，删除 webnovel-writer/ceo/test-generator）
11. 新增领域 Agent（api-designer, pentester, observability-engineer, data-engineer, a11y-expert, knowledge-synthesizer）

### 第四批：Prompt 质量提升（1 天）
12. router/critic/lead/general-worker/cost-analyst 重写
13. 全部 33 Agent 按模板规范化
14. 核心 Skill 补充使用示例

---

## 十一、效果预估

| 维度 | 优化前 | 优化后 |
|------|--------|--------|
| Agent 路由准确率 | ~70%（关键词撞运气） | ~90%（分类+关键词+语义） |
| Skill 利用率 | 17% | >83% |
| Router 可用性 | 极差（10行） | 完整决策树 |
| 安全覆盖 | 1 Agent + 6 Skill | 4 Agent + 8 Skill |
| 领域覆盖 | 缺 ML/数据/i18n/云 | 全 12 领域覆盖 |
| 平均 Prompt 质量 | 参差不齐 | 全部模板化 |
| 文档同步 | 多处过时 | 全部对齐 agent.yaml |
