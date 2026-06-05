# Changelog

## [0.1.0] - 2026-06-05

### Features
- **24 个专业 Agent**：coder、code-reviewer、python/go/typescript-reviewer、security-reviewer、database-reviewer、test-runner、tdd-guide、e2e-runner、qa、planner、ceo、cost-analyst、performance-optimizer、explorer、build-error-resolver、refactor-cleaner、doc-updater、devops、release-manager、orchestrator、general-worker、webnovel-writer
- **7 个工作流技能**：design、debug、cost、compress、init、release、translate
- **4 个快捷命令**：status、cost、track、compress
- **4 个自动化钩子**：SessionStart、PostToolUse、PreCompact、Stop
- **29 条工程规范**：架构/安全/风格/Git + Python/Go/TypeScript 多语言
- **Maestro 多智能体调度引擎**：智能路由(加权+置信度+语义+缓存)、任务分发、成本追踪、结果网关
- **Web 管理界面**：使用者模式(智能路由+多轮会话+导出) + 开发者模式(Agent管理/路由测试/成本统计/多模型配置/流水线)
- **一键启动**：start.bat/start.sh
- **多模型支持**：DeepSeek / OpenAI 兼容 / Ollama
- **Agent 工厂**：用 AI 创建自定义 Agent
- **6 条预置流水线**：Plan-Build-Review / TDD / gstack 发布 / 安全审查 / 全栈开发 / Bug 狩猎
- **双语 README**：中文 + English

### Design Rationale
- 按需注入架构 —— Agent 虽多但不暴胀上下文
- Maestro 作为核心差异化，提供 ECC 不具备的智能调度和成本追踪
- 中文原生 + 英文 README，面向中文开发者社区
- 所有 Agent 和规则来自日常生产验证

### Notes & Caveats
- Maestro 调度系统依赖 Python 3.10+
- Web 界面需要 pyyaml + requests
- Hooks 脚本需要 Git Bash（Windows）或 bash（macOS/Linux）
