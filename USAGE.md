# Agency 使用指南

## 我该怎么开始？

### 我只有 API Key
（配 .env → python maestro/web.py → 浏览器打开）

```bash
pip install pyyaml requests
echo "DEEPSEEK_API_KEY=sk-xxxx" > .env
python maestro/web.py
# → http://localhost:8800
```

### 我已经有 Claude Code
（cp agents/L1_executor/xxx.md ~/.claude/agents/ → 直接用）

```bash
git clone https://github.com/Sweetteabittersugar/agency.git
cd agency
./install.sh        # macOS / Linux / Git Bash
# 或
.\install.ps1       # Windows PowerShell
# 安装过程选 2（项目安装）或 1（全局安装）
```

### 我想在命令行用
（python maestro/main.py "任务" → 自动路由）

```bash
python maestro/main.py "写一个快排函数"
```

---

## 我想做什么？

用场景驱动，每个场景说清楚用什么 Agent、怎么用：

### 写代码
- **简单实现** → @coder 或直接说"帮我写..."
- **修复构建错误** → @build-error-resolver
- **清理旧代码** → @refactor-cleaner
- **TDD 开发** → @tdd-guide 或 TDD 流水线

### 审查代码
- **通用审查** → @code-reviewer
- **Python 专项** → @python-reviewer
- **Go 专项** → @go-reviewer
- **前端专项** → @typescript-reviewer
- **安全检查** → @security-reviewer
- **数据库审查** → @database-reviewer

### 测试
- **跑测试** → @test-runner
- **TDD 向导** → @tdd-guide
- **E2E 测试** → @e2e-runner
- **QA 策略** → @qa

### 规划与决策
- **技术方案** → @planner
- **产品需求** → @ceo
- **成本分析** → @cost-analyst
- **性能优化** → @performance-optimizer

### 搜索与探索
- **找文件/查代码** → @explorer

### 运维与发布
- **CI/CD 配置** → @devops
- **版本发布** → @release-manager
- **文档更新** → @doc-updater

### 复杂任务
- **拆解大任务** → @orchestrator
- **全流程开发** → gstack 发布管道
- **代码审查全流程** → Plan-Build-Review 流水线

### 创作
- **写小说** → @webnovel-writer
- **杂务** → @general-worker

---

## 24 个 Agent 速查表

| Agent | 一句话 | 什么时候用 | 命令行 | Web |
|-------|--------|-----------|--------|-----|
| coder | 写代码、修复、重构 | 任何编码任务 | @coder | 直接输入 |
| code-reviewer | 通用代码审查 | 审查代码质量 | @code-reviewer | "审查这段代码" |
| python-reviewer | Python 专项审查 | Django/FastAPI/Flask | @python-reviewer | "审查 Python 代码" |
| go-reviewer | Go 专项审查 | goroutine/接口设计 | @go-reviewer | "审查 Go 代码" |
| typescript-reviewer | TS/React 审查 | 前端/Node.js | @typescript-reviewer | "审查前端代码" |
| security-reviewer | 安全检查 | 安全审计 | @security-reviewer | "安全检查" |
| database-reviewer | 数据库审查 | SQL/Schema/索引 | @database-reviewer | "审查数据库" |
| test-runner | 跑测试 | 执行测试套件 | @test-runner | "跑测试" |
| tdd-guide | TDD 向导 | 测试驱动开发 | @tdd-guide | "TDD 开发" |
| e2e-runner | 端到端测试 | Playwright E2E | @e2e-runner | "写 E2E 测试" |
| qa | QA 策略 | 测试计划设计 | @qa | "设计测试策略" |
| planner | 技术规划 | 架构设计/方案 | @planner | "设计方案" |
| ceo | 产品决策 | 需求定义/优先级 | @ceo | "定义需求" |
| cost-analyst | 成本分析 | API 费用追踪 | @cost-analyst | "分析费用" |
| performance-optimizer | 性能优化 | 瓶颈分析 | @performance-optimizer | "优化性能" |
| explorer | 代码搜索 | 找文件/查引用 | @explorer | "搜索..." |
| build-error-resolver | 修复构建 | 编译/依赖错误 | @build-error-resolver | "构建报错" |
| refactor-cleaner | 清理代码 | 死代码/重复 | @refactor-cleaner | "清理代码" |
| doc-updater | 更新文档 | README/CHANGELOG | @doc-updater | "更新文档" |
| devops | CI/CD | Docker/部署 | @devops | "配置部署" |
| release-manager | 发布管理 | 版本/CHANGELOG | @release-manager | "准备发布" |
| orchestrator | 总调度 | 复杂任务拆解 | @orchestrator | "拆解任务" |
| general-worker | 通用杂务 | 整理/配置 | @general-worker | 自动路由 |
| webnovel-writer | 小说创作 | 世界观/章节 | @webnovel-writer | "写小说" |

---

## 三种使用方式

### Web 界面（推荐新手）
1. 双击 start.bat 或 python maestro/web.py
2. 打开 http://localhost:8800
3. 右上角切换 [使用者/开发者]

**使用者模式**：
- 输入框直接说任务 → 自动路由 → 流式输出
- 想指定 Agent → @agent名 开头
- 复杂的 → @orchestrator 拆解分派

**开发者模式**：
- Agents 标签：看所有 Agent，编辑 prompt，测试
- Routes 标签：输入文字看匹配得分
- 流水线标签：选预设工作流一键执行
- Cost 标签：看费用统计
- Settings 标签：换模型、调参数

### 命令行
```bash
# 自动路由
python maestro/main.py "写一个快排函数"

# 指定 Agent
python maestro/run.py coder "写一个快排函数"

# 列出所有 Agent
python maestro/run.py --list

# 换模型
python maestro/main.py --model deepseek-reasoner "设计架构"
```

### Claude Code 集成
```bash
# 安装 Agent 到 Claude Code
./install.sh  # 选 2（项目安装）
# 然后在 Claude Code 中直接对话，Agent 自动生效
```

---

## 功能详解

### 自动路由
系统根据你的任务关键词自动选 Agent。右上角显示置信度：
- 高（>70%）：直接执行
- 中（50-70%）：可能触发语义匹配
- 低（<50%）：显示备选 Agent 让你选

### @agent 直调
想用哪个直接用：`@coder 写函数` `@planner 设计方案` `@qa 写测试计划`
支持简称：`@reviewer`=code-reviewer, `@test`=test-runner

### 多轮会话
每次对话保持上下文。点"新对话"重置。侧边栏可恢复历史。

### 流水线
预设 Agent 组合，一键顺序执行：
- Plan-Build-Review：规划→编码→审查
- TDD 循环：RED→GREEN→REFACTOR
- gstack 发布：CEO→开发→QA→发布
- 安全审查：审查→审计→修复
- 全栈开发：规划→前后端→测试→审查
- Bug 狩猎：搜索→定位→修复→测试→审查

### Agent 工厂
开发者模式 → Agents → "用 AI 创建 Agent"
描述需求 → AI 生成 Agent 定义 → 审阅保存 → 自动注册

### 多模型支持
Settings 里切换 DeepSeek / OpenAI / Ollama。模型映射可自定义。

### 导出
输出区底部：复制 MD / 下载 .md / 复制纯文本

---

## 常见问题

**Q: 路由选错了 Agent 怎么办？**
A: 手动 @agent名 指定，或点备选列表里的 Agent。

**Q: 怎么知道某个 Agent 能做什么？**
A: 开发者模式 → Agents → 点开卡片看完整 prompt。

**Q: 怎么创建自己的 Agent？**
A: 开发者模式 → Agents → "用 AI 创建 Agent" → 描述需求。

**Q: 支持其他模型吗？**
A: Settings → 选 OpenAI 兼容 / Ollama → 填 key 和 URL。

**Q: 怎么停掉正在生成的内容？**
A: 点红色停止按钮，或按 Esc。

**Q: 命令行怎么用？**
A: python maestro/main.py "你的任务"
