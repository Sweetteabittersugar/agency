# agency-kit

> Claude Code 中文原生配置平台 —— Agent 调度、成本追踪、创作工作流，全部日常生产验证。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-green)](VERSION)

```bash
# 方式一：一行安装（推荐）
git clone https://github.com/Sweetteabittersugar/agency-kit.git && cd agency-kit && ./install.sh

# 方式二：npm
npm install -g agency-kit

# 方式三：只要一个 Agent（30 秒，无需安装脚本）
cp agents/coder.md ~/.claude/agents/
```
**Agent 层不需要任何 API key。** 装上就能用。只有 Maestro 调度引擎（可选）需要 DeepSeek key。

## 这是什么

**agency-kit** 是一套 Claude Code 配置增强系统。它不是另一个 AI 工具——它是让你现有的 Claude Code 获得以下能力的**插件层**：

```
你的 Claude Code
    │
    ├── agents/   ← 19 个专业子代理（自动分派任务）
    ├── skills/   ← 7 个工作流技能（设计/调试/发布/翻译/成本/压缩）
    ├── commands/ ← 4 个快捷命令（状态/费用/追踪/压缩）
    ├── hooks/    ← 4 个自动化钩子（启动/结束/压缩前后）
    ├── rules/    ← 8+ 套工程规范（架构/安全/风格/Git + 多语言）
    └── maestro/  ← 多智能体调度引擎（独有）
```

## 为什么选它

| | 只用 Claude Code | 用 ECC | **用 agency-kit** |
|---|---|---|---|
| 语言 | 英文 | 英文 | **中文原生** |
| Agent 调度 | 手动 | 手动 | **自动路由矩阵（19个Agent）** |
| 成本追踪 | 无 | 无 | **内置，按模型/日期/Agent** |
| 创作支持 | 无 | 无 | **小说/设计模式** |
| 上下文管理 | 手动 | 基础 | **按需注入，不暴胀** |
| 生产验证 | — | 模板级 | **每日实际使用** |

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/Sweetteabittersugar/agency-kit.git
cd agency-kit

# 安装（自动链接到 Claude Code）
./install.sh        # macOS / Linux / Git Bash
# 或
.\install.ps1       # Windows PowerShell
```

安装后，`.claude/` 目录下会自动出现 `agents/`、`skills/`、`commands/`、`hooks/`、`rules/`。

### 10 秒验证

在 Claude Code 中测试：

```
@status          # 查看 Agent 状态
@cost            # 查看 API 费用
/design          # 进入设计模式
```

## 核心模块

### Agents（19 个专业子代理）

| 类别 | Agent | 职责 |
|------|-------|------|
| **开发** | `coder` | 直接写代码、重构、修复 |
| | `build-error-resolver` | 编译/构建错误增量修复 |
| | `refactor-cleaner` | 死代码、重复代码安全删除 |
| **审查** | `code-reviewer` | 四维度通用代码审查 |
| | `python-reviewer` | Python/Django/FastAPI 专项 |
| | `go-reviewer` | Go 并发安全/接口设计 |
| | `typescript-reviewer` | TS/React/Node.js 专项 |
| | `security-reviewer` | 安全漏洞深度检测 |
| | `database-reviewer` | SQL 性能/Schema 审查 |
| **测试** | `test-runner` | 测试执行与失败分析 |
| | `tdd-guide` | TDD 五步循环向导 |
| | `e2e-runner` | Playwright 端到端测试 |
| **规划** | `planner` | 需求分析/架构设计/任务拆分 |
| | `cost-analyst` | API 费用多维分析 |
| | `performance-optimizer` | 性能瓶颈分析与优化 |
| **其他** | `explorer` | 代码库搜索与结构分析 |
| | `doc-updater` | 文档自动同步 |
| | `general-worker` | 通用杂务处理 |
| | `webnovel-writer` | 小说世界观/章节创作 |

### Maestro — 多智能体调度引擎（独有）

这是 agency-kit 的核心差异化能力：

```
你的任务 → 路由矩阵 → 自动选择 Agent → 沙箱执行 → 结果网关 → 你看到摘要
                              ↓
                         成本追踪（实时）
                              ↓
                         任务看板（持久化）
```

| 脚本 | 功能 |
|------|------|
| `dispatch.py` | 任务分发引擎，支持 9 种 Agent 自动路由 |
| `sandbox.py` | 进程隔离执行环境 |
| `gateway.py` | 结果网关，提取摘要返回 |
| `cost-tracker.py` | 实时成本追踪 |
| `cost-analyzer.py` | 费用趋势分析 |
| `task-tracker.py` | 任务看板，状态追踪 |
| `transcript-parser.py` | 对话解析与知识提取 |
| `cleanup-agents.py` | 闲置进程自动清理 |

### Skills（7 个工作流技能）

| 技能 | 触发 | 功能 |
|------|------|------|
| `design` | `/design` 或"设计模式" | 四阶段需求澄清（目标→约束→方案→确认） |
| `debug` | "调试"、"排查"、"debug" | 系统化调试（复现→定位→修复→防复发） |
| `cost` | `@cost` 或"查费用" | API 成本追踪与报告 |
| `compress` | `/compress` 或自动触发 | 上下文压缩，保留关键信息 |
| `init` | "新建项目"、"初始化" | 项目骨架搭建与规范配置 |
| `release` | "发版"、"发布"、"release" | 版本管理与发布流程 |
| `translate` | "翻译"、"translate" | 技术文档中英互译 |

### Rules（8+ 套工程规范）

```
rules/
├── architecture.md      # 项目结构规范
├── maestro.md           # Agent 调度规则（路由矩阵）
├── security.md          # 安全规范
├── coding-style.md      # 代码风格规范
├── git-workflow.md      # Git 工作流
├── common/              # 通用最佳实践（8 维度）
├── python/              # Python 规范
├── golang/              # Go 规范
└── typescript/          # TypeScript 规范
```

### Hooks（4 个自动化钩子）

| 钩子 | 触发时机 | 功能 |
|------|----------|------|
| `SessionStart.sh` | 会话启动 | 环境检查、日志初始化 |
| `PostToolUse.sh` | 每次工具调用后 | 操作日志、日志轮转 |
| `PreCompact.sh` | 上下文压缩前 | 关键信息保存 |
| `Stop.sh` | 会话结束 | 临时文件清理、日志归档 |

## 目录结构

```
agency-kit/
├── README.md               # 本文件
├── README.en.md             # English README
├── AGENTS.md                # Agent 路由矩阵与使用指南
├── CLAUDE.md                # Claude Code 自动加载入口
├── LICENSE                  # MIT
├── VERSION                  # 版本号
├── package.json             # npm 包配置
├── install.sh / install.ps1 # 安装脚本
│
├── agents/                  # 子代理定义
├── skills/                  # 工作流技能
├── commands/                # 快捷命令
├── hooks/                   # 自动化钩子
├── rules/                   # 工程规范（通用 + 多语言）
├── maestro/                 # 多智能体调度引擎
├── scripts/                 # 工具脚本
├── docs/zh-CN/              # 中文文档
└── tests/                   # 测试
```

## 设计哲学

### "我们 vs 想法" 沙盘推演

收到任何想法/方案时，不直接执行也不直接反驳。动态切换三个阶段：

1. **建设者** — 先全力理解并补全想法逻辑链
2. **挑战者** — 针对加固后的想法做压力测试
3. **裁判官** — 盘点优势和裂缝，共同判定

核心：**我们 vs 想法**，不是 你 vs 我。

### 混合派发

轻活直接走 Agent 工具（减少调度开销），重活走 dispatch.py（隔离执行）。判断标准：涉及 3+ 文件的写操作或需要隔离环境 → 重活。

### 结果网关

Agent 完成后只向用户展示精简摘要，不转发内部思考链和工具调用。保持对话简洁，给用户打断窗口。

## 贡献

欢迎提交 Issue 和 PR。Agent/Skill/Command 的新增和修改请参考 `AGENTS.md` 中的格式规范。

## 致谢

- [everything-claude-code](https://github.com/affaan-m/ECC) — 项目形态参考，207K Stars 的开源标杆
- [Claude Code](https://claude.ai/code) — Anthropic 的 AI 编程工具

## License

MIT © 2026 Sweetteabittersugar
