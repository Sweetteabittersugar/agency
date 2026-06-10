# Changelog

## [0.4.0] - 2026-06-10

### Features
- **多面板分屏布局**：单面板/双分屏/2×2 网格三种布局，分割条拖拽调整，每面板独立 Agent + 独立对话
- **Git Worktree 隔离**：Agent 在隔离工作目录运行，互不冲突。创建/删除/列表/清理 + 仪表盘管理 Tab
- **会话持久化**：JSONL 事件溯源模式，刷新页面不丢对话。超 2MB 自动快照压缩
- **Cmd+K 命令面板**：19 条命令模糊搜索，键盘导航，Ctrl+K 呼出
- **费用可视化仪表盘**：30 天趋势柱状图、Top Agent 消费排行、近 7 天明细，纯 CSS 无外部依赖
- **五层置信度门控路由**：关键词→语义→交叉验证→LLM→兜底，低置信不强分
- **路由反馈回路**：前端"不对换一个"按钮 + 纠正记录 API，系统从错误中学习

### Design Rationale
- 多面板是 32 Agent 卖点的必要条件——用户需要同时看多个 Agent 工作
- Worktree 是多面板并行的安全前提——没有隔离会互相踩文件
- 会话持久化解决"刷新丢状态"这个最高频的负面体验
- 五层门控解决路由致命问题：低置信分配 = 随机，宁可走通用 Agent 不高置信分错

### Changes
- **Agent 重组**：32 Agent 按 L3(决策)/L2(专业)/L1(执行)/L0(工具) 四层分目录，全补 skills/memory/maxTurns 字段
- **Agent 描述扩充**：从一句话升级为"触发场景+典型输入+负向关键词"，提升路由命中率
- **Skill-Agent 绑定**：每个 Agent 声明自己需要的 Skill，告别各自为政
- **启动版本检查**：PyPI 自动检测 + Web UI 横幅提醒 + 24h 缓存
- **CI 发布流水线**：打 tag → 测试 → 构建 → PyPI 发布 → GitHub Release 全自动
- **CI 加固**：合并 lint+test、pip 缓存、Bandit 安全扫描、ruff+mypy 类型检查、Conventional Commits 检查
- **仓库大清理**：根目录 9 文件迁移到 docs/scripts/、删除测试占位符/宣传文案/重复文件、.gitignore 补 11 项
- **工程基础设施**：.editorconfig、.pre-commit-config、RELEASE.md、REQUIREMENTS.md
- **CORS 安全头**：localhost 白名单 + OPTIONS 预检
- **可观测性**：HTTP 日志恢复、X-Request-Id 追踪、健康检查真实进程数
- **测试重写**：3 个测试文件 28 个过时测试 → 66 通过 0 失败

### Notes & Caveats
- 会话持久化使用 maestro/sessions/ 目录存储 JSONL，注意磁盘空间
- Worktree 会在 maestro/worktrees/ 下创建目录，每个约 2-10MB
- 路由反馈数据写入 maestro/routing_feedback.jsonl，定期检查避免过大
- mypy 类型检查设为允许失败（36% 函数缺注解），渐进补齐

---

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
