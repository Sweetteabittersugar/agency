# Agency — Agent 路由

> 32 个 Agent，四层架构。自动路由，按需派发。

## 快速路由

| 任务 | Agent | 模型 |
|------|-------|------|
| 写代码/修Bug/重构 | coder | sonnet |
| 代码审查 | code-reviewer | sonnet |
| 安全审计 | security-reviewer | sonnet |
| 架构设计/技术选型 | architect | opus |
| 规划/方案设计 | planner | sonnet |
| 多Agent编排/复杂拆解 | orchestrator | opus |
| 搜索/定位/查文件 | explorer | haiku |
| 调试/排查根因 | debugger | sonnet |
| TDD/测试先行 | tdd-guide | sonnet |
| 测试执行/分析 | test-runner | sonnet |
| E2E/浏览器测试 | e2e-runner | sonnet |
| 部署/CI/CD | devops | sonnet |
| 发布/版本管理 | release-manager | sonnet |
| 文档更新 | doc-updater | haiku |
| 性能优化 | performance-optimizer | sonnet |
| 费用分析 | cost-analyst | haiku |
| 不确定类型→先分类 | router | haiku |
| 通用杂务 | general-worker | haiku |

## 模型策略

- **Opus**：架构、决策、终审
- **Sonnet**：实现、审查、测试
- **Haiku**：搜索、摘要、分类

## 规则

- 不确定路由 → router 先分类
- 代码改完 → 自动 code-reviewer
- 安全相关 → 必须 security-reviewer
- 轻活直调 Agent，重活(3+文件)走 dispatch
- @status | @cost | @tracker

详见 AGENTS.md（路由矩阵）
