# Changelog

## [0.1.0] - 2026-06-05

### Features
- **9 个专业 Agent**：coder、code-reviewer、explorer、test-runner、general-worker、webnovel-writer、planner、security-reviewer、cost-analyst
- **6 个工作流技能**：design（设计模式）、cost（成本追踪）、compress（上下文压缩）、docx/pdf/xlsx（文档技能）
- **4 个快捷命令**：status、cost、track、compress
- **4 个自动化钩子**：SessionStart、PostToolUse、PreCompact、Stop
- **8+ 套工程规范**：架构、安全、代码风格、Git 工作流 + Python/Go/TypeScript 多语言规范
- **Maestro 多智能体调度引擎**：dispatch（任务分发）、sandbox（进程隔离）、gateway（结果网关）、cost-tracker（成本追踪）、task-tracker（任务看板）
- **安装脚本**：install.sh（bash）+ install.ps1（PowerShell）
- **双语 README**：中文 + English

### Design Rationale
- 采用 ECC 项目形态（agents/skills/commands/hooks/rules 结构），已验证为 Claude Code 配置平台的最佳实践
- Maestro 作为核心差异化能力，提供 ECC 不具备的多智能体自动调度和成本追踪
- 中文原生 + 英文 README，面向中文开发者社区
- 所有 Agent 和规则来自日常生产验证，非模板级

### Notes & Caveats
- Maestro 调度系统依赖 Python 3.10+
- Hooks 脚本需要 Git Bash（Windows）或 bash（macOS/Linux）
- 首次安装后在 Claude Code 中运行 `@status` 验证
