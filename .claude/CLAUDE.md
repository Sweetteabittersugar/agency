# Agency Agent 路由

> 本项目有 32 个 Agent，分四层。此文件告诉 Claude Code 如何根据任务自动选择 Agent。

## 快速路由

| 任务类型 | Agent | 模型 |
|---------|-------|------|
| 写代码 / 修 Bug / 实现功能 | coder | sonnet |
| 代码审查 / 质量检查 | code-reviewer | sonnet |
| 安全审计 / 漏洞扫描 | security-reviewer | sonnet |
| 架构设计 / 技术选型 | architect | opus |
| 需求分析 / 实施规划 | planner | sonnet |
| 复杂多步任务 / 多 Agent 编排 | orchestrator | opus |
| 搜索代码 / 查找文件 | explorer | haiku |
| 调试 / 排查错误 | debugger | sonnet |
| 写测试 / TDD | tdd-guide | sonnet |
| 运行测试 / 分析结果 | test-runner | sonnet |
| E2E 测试 | e2e-runner | sonnet |
| DevOps / 部署 | devops | sonnet |
| 发布管理 | release-manager | sonnet |
| 文档生成 / 更新 | doc-updater | haiku |
| 性能优化 | performance-optimizer | sonnet |
| 构建错误修复 | build-error-resolver | sonnet |
| UI/UX 设计 | designer | sonnet |
| 费用分析 / 成本追踪 | cost-analyst | haiku |
| 不确定类型 → 先分类 | router | haiku |
| 通用杂务 | general-worker | haiku |

## 模型策略

- **Opus**：架构、决策、终审、复杂编排
- **Sonnet**：实现、审查、测试、调试
- **Haiku**：搜索、分类、摘要、简单查询

## 通用规则

- 不确定路由时 → 先走 router 做意图分类
- 代码修改后 → 自动触发 code-reviewer
- 安全相关 → 必须过 security-reviewer
- 所有 Agent 优先使用匹配的 Skill（见各 Agent 的 skills 字段）
- 成本敏感任务优先用 haiku
