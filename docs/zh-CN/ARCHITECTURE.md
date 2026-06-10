# 架构说明

> 解释"这个项目是怎么设计的、为什么这样设计"。适用于想深入理解或二次开发的用户。

## 设计原则

### 1. 分层可插拔

agency-kit 不是全家桶。它是四层结构，每层独立可用：

```
第 0 层：单个 Agent     ← 复制一个 .md 文件即可
第 1 层：Agent 矩阵     ← 19 个 Agent，关键词自动路由
第 2 层：规范 + 自动化  ← Rules + Hooks + Commands + Skills
第 3 层：Maestro 引擎   ← 任务调度 + 进程隔离 + 成本追踪
```

**下层不依赖上层。** 用第 0 层的人不需要知道第 3 层的存在。

这种设计来自实际使用经验：一个新人 clone 项目后，不应该被 100+ 个文件吓跑。他可以先复制一个 agent 试试，好用再装全部，再好用再上 Maestro。

### 2. 按需注入

31 个 Agent 按 L3/L2/L1/L0 四层装在 `agents/` 目录里，但当前任务只需要 `coder` -- 只有 `coder.md` 的 prompt 被注入到 Claude Code 上下文。这就是为什么"多"不等于"慢"。

底层机制：Claude Code 启动时读取 `.claude/agents/` 下的所有 `.md` 文件，根据 `CLAUDE.md` 中的路由规则（或 `AGENTS.md` 中的路由矩阵）匹配当前任务，只注入选中的 agent prompt。未匹配的 agent 零开销。

### 3. 纯文本，零锁定

所有配置是 Markdown / YAML / JSON / Bash / PowerShell。没有数据库 schema（除了 `cost.db` 是运行时生成的费用数据），没有私有格式，没有编译产物。

你可以：
- 随时手动改任何 agent 的 prompt
- 随时删除 `agents/` 子目录下某个文件来卸载它
- 用 `git diff` 看清每次改动
- 用任何编辑器打开和修改

卸载只需删除对应的 `.claude/` 目录下的文件。没有注册表、没有残留。

### 4. 中文原生

Agent 的思维语言就是中文。不是因为"翻译层"把英文 prompt 翻成了中文，而是从一开始就用中文设计角色和工作流。这在实际使用中带来两个好处：

- 中文用户发出的中文指令，agent 用中文思考，不存在翻译损耗
- 代码注释和文档生成也是中文为主，符合中文团队习惯

## 项目结构

```
agency-kit/
├── AGENTS.md              # Agent 路由矩阵（核心编排）
├── agent.yaml             # Agent 注册表（结构化元数据）
├── CLAUDE.md              # Claude Code 启动入口
├── GETTING-STARTED.md     # 5 分钟入门
├── install.sh / install.ps1  # 安装脚本
│
├── agents/                # 31 个 Agent（L3/L2/L1/L0 四层）
│   ├── L3_decision/       # 决策层 (Opus)
│   ├── L2_specialist/     # 专业层 (Sonnet)
│   ├── L1_executor/       # 执行层 (Sonnet/Haiku)
│   └── L0_utility/        # 工具层 (Haiku)
│
├── rules/                 # 工程规范
│   ├── architecture.md    # 项目结构规范
│   ├── maestro.md         # Agent 调度规则
│   ├── security.md        # 安全规范
│   ├── coding-style.md    # 代码风格
│   ├── git-workflow.md    # Git 工作流
│   ├── common/            # 通用最佳实践（跨语言）
│   ├── python/            # Python 规范
│   ├── golang/            # Go 规范
│   └── typescript/        # TypeScript 规范
│
├── skills/                # 工作流技能
│   ├── design/SKILL.md    # 设计模式
│   ├── compress/SKILL.md  # 上下文压缩
│   └── cost/SKILL.md      # 费用查询
│
├── commands/              # 快捷命令
│   ├── status.md          # @status
│   ├── cost.md            # @cost
│   ├── track.md           # @tracker
│   └── compress.md        # /compress
│
├── hooks/                 # 自动化钩子
│   ├── SessionStart.sh    # 会话启动
│   ├── PostToolUse.sh     # 工具使用后
│   ├── PreCompact.sh      # 压缩前
│   └── Stop.sh            # 会话结束
│
├── maestro/               # 多 Agent 调度引擎
│   ├── dispatch.py        # 任务分发
│   ├── sandbox.py         # 进程隔离
│   ├── gateway.py         # 结果网关
│   ├── cost-tracker.py    # 实时费用追踪
│   ├── cost-analyzer.py   # 费用趋势分析
│   ├── task-tracker.py    # 任务看板
│   ├── transcript-parser.py  # 对话解析
│   ├── cleanup-agents.py  # 闲置进程清理
│   └── agents.json        # Maestro Agent 注册
│
├── tests/                 # 测试
├── docs/zh-CN/            # 中文文档
├── examples/              # 扩展示例
├── .codex/ .cursor/ .gemini/  # 其他 AI 工具适配
└── scripts/               # 辅助脚本
```

## Agent 工作机制

### Agent 文件格式

每个 Agent 是一个带 YAML frontmatter 的 Markdown 文件：

```markdown
---
name: coder
description: 直接写代码的软件工程师
tools: ["Read", "Write", "Bash", "Glob", "Grep"]
model: sonnet
---

# Coder Agent

## 角色
...

## 工作流
...

## 输出格式
STATUS: DONE
## 用户摘要
<结果>
```

- `name`：agent 标识符
- `description`：一句话描述
- `tools`：允许使用的工具列表
- `model`：推荐模型（sonnet / haiku / opus / deepseek）

路由矩阵（`AGENTS.md`）和注册表（`agent.yaml`）各自维护一份 agent 索引，前者面向人类阅读，后者面向程序解析。

### 独立模式（无 Maestro）

```
用户: "帮我重构这个函数"
  -- 路由矩阵匹配关键词"重构"
  -- 选中 coder agent
  -- coder.md 的 prompt 被注入当前对话
  -- coder 按自己定义的角色和工作流直接在对话中执行
  -- 结果直接返回给用户
```

独立使用时，Agent 就是一段被注入的 prompt。没有中间层，没有额外开销。

### Maestro 模式（调度引擎）

```
用户: "重构整个模块"（重活，3+ 文件）
  -- 路由矩阵判断为"重活"
  -- dispatch.py 创建任务 → 写入 maestro/tasks/
  -- sandbox.py 启动 Agent 进程（独立上下文）
  -- Agent 按任务描述执行
  -- 完成后写入 maestro/results/
  -- gateway.py 提取 STATUS + 用户摘要
  -- 向用户展示精简结果
```

重活走 dispatch 的原因：
- 不阻塞主对话（异步执行）
- 进程隔离（Agent 崩溃不影响主会话）
- 可追踪（任务看板记录每个任务的状态和耗时）
- 可计费（每次调用的 token 消耗和费用）

## 为什么不是 ECC 路线

ECC（everything-claude-code）把所有内容打包成一个插件，安装产生 373 个文件操作，全家桶加载占用 60K-140K 上下文。

我们的选择：

| | ECC 路线 | agency-kit |
|---|---|---|
| 安装方式 | 插件安装，黑盒 | 文件复制，可审计 |
| 加载策略 | 全家桶全量注入 | 按需注入，按匹配规则 |
| 配置格式 | 编译产物 | 纯文本 (md/yaml/json/sh) |
| 语言 | 英文 prompt | 中文原生设计 |
| 卸载 | 插件卸载（可能有残留） | 删除目录即可 |
| 粒度控制 | 全有或全无 | 从单文件到全套，四层可选 |

核心差异：**用户控制粒度。** 你可以只装一个 agent，也可以装全套。这是设计上的首要考量。

## 扩展指南

### 添加一个 Agent

1. 在 `agents/` 下（或按层级放入子目录）创建 `xxx.md`（遵循 YAML frontmatter + 正文格式）
2. 在 `agent.yaml` 的 `agents:` 下注册
3. 在 `AGENTS.md` 的路由矩阵中添加条目
4. 如需 Maestro 调度，在 `maestro/agents.json` 中注册
5. 参考 `examples/custom-agent.md`

### 添加一个 Rule

1. 创建 `rules/xxx.md`
2. 在 `RULES.md` 索引中注册
3. 参考 `examples/custom-rule.md`

### 添加一个 Skill

1. 创建 `skills/xxx/SKILL.md`
2. 格式见 `docs/zh-CN/skills.md`

### 适配其他 AI 工具

已有适配目录，放入对应格式的 agent/rules 文件即可：
- `.codex/` — Codex / MIMO CLI
- `.cursor/` — Cursor IDE
- `.gemini/` — Gemini CLI

每个适配目录只需包含该工具能理解的格式的配置文件，不需要完整复制。

## 扩展阅读

- `AGENTS.md` — Agent 路由矩阵与使用指南
- `agent.yaml` — Agent 注册表（结构化元数据）
- `docs/zh-CN/maestro.md` — Maestro 调度引擎详解
- `docs/zh-CN/agents.md` — Agent 开发指南
- `docs/zh-CN/rules.md` — 规范体系说明
- `examples/maestro-integration.md` — Maestro 集成示例
