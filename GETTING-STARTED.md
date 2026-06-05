# 5 分钟入门

> **Agent 层不需要任何密钥。** 下载 → 复制 → 能用。只有可选的 Maestro 调度引擎需要 API key。

## 方式零：不装 Claude Code，直接跑（只需 Python + DeepSeek key）

如果你只是想用一个 Agent 干活，不需要 Claude Code，不需要安装脚本——更不需要手动指定 Agent：

```bash
# 1. 获取 DeepSeek API Key：https://platform.deepseek.com/api_keys
# 2. 安装依赖
pip install pyyaml requests
# 3. 写到 .env
echo "DEEPSEEK_API_KEY=sk-xxxx" > .env
# 4. 直接说任务，系统自动选 Agent
python maestro/main.py "写一个快排函数"
python maestro/main.py "分析这个目录结构"
python maestro/main.py --list-routes  # 看路由表
```

- 不需要 Claude Code
- 不需要手动指定用哪个 Agent（自动路由）
- 不需要 install.sh
- 只依赖 Python 3.10+ 和 `pip install pyyaml requests`
- 自动记录成本到 cost.db

可用 Agent：`coder`、`reviewer`、`explorer`、`planner`、`test-runner`、`general-worker` 等 19 个，全在 `agents/` 目录下。关键词匹配自动路由，无需手动选择。

## 你不需要装全部

### 第 0 层：只装一个 Agent（30 秒，需 Claude Code）

```bash
# 复制你需要的 agent 到 Claude Code 配置目录
cp agents/coder.md ~/.claude/agents/
```

现在在 Claude Code 中说"帮我写一个函数"——coder agent 会自动生效。

**不需要安装脚本。不需要 maestro。不需要任何配置。** 一个 .md 文件，立即可用。

其他 Agent 同理：
- `explorer.md` — 搜索代码库
- `code-reviewer.md` — 审查代码
- `tdd-guide.md` — 测试驱动开发
- 共 19 个，全在 `agents/` 目录下

### 第 1 层：装上整套 Agent + 路由（2 分钟）

```bash
# macOS / Linux / Git Bash
./install.sh
# 选择 2（安装到当前项目）

# 或 Windows PowerShell
.\install.ps1
```

19 个 Agent 全部到位。路由矩阵自动选择：
- "帮我写代码" -- `coder`
- "审查这段代码" -- `code-reviewer`
- "找个文件" -- `explorer`
- "写测试" -- `tdd-guide`
- "构建报错了" -- `build-error-resolver`
- "写小说" -- `webnovel-writer`

### 第 2 层：加上规范 + 自动化（同上一步）

`./install.sh` 同时装上了：
- **Rules**：写代码时自动遵守的规范（安全、代码风格、Git 工作流 + Python/Go/TypeScript 专项）
- **Hooks**：会话启动检查、上下文压缩、日志清理
- **Commands**：`@status`、`@cost`、`@tracker` 等快捷命令
- **Skills**：`/design`（设计模式）、`/compress`（压缩上下文）等工作流技能

### 第 3 层：启用 Maestro 调度引擎（10 分钟）

```bash
# 确保 Python 3.10+ 可用
python --version

# 在 maestro/agents.json 中确认 Agent 配置（已预配 15 个）
# 然后运行
python maestro/dispatch.py --list
```

Maestro 提供：
- 异步任务分发（不阻塞对话）
- 进程隔离执行（重活走独立沙箱）
- 成本追踪（按模型/日期/Agent）
- 任务看板（持久化，可查历史）

**大多数用户停在 1-2 层就够了。** Maestro 是给需要多 Agent 协作和成本管理的项目用的。

## 验证安装

在 Claude Code 中试试：

| 命令 | 做什么 |
|------|--------|
| `@status` | 查看 Agent 任务状态 |
| `@cost` | 查看 API 费用 |
| `/design` | 进入设计模式 |
| `@tracker` | 查看任务看板 |

## 装上后它怎么工作的

```
你说："帮我重构这个函数"
  -- 路由矩阵匹配关键词"重构"
  -- 选中 coder agent
  -- coder.md 的 prompt 被注入当前对话
  -- coder 按自己定义的角色和工作流执行
  -- 结果直接返回给你
```

轻活（单文件）直接用 Agent。重活（3+ 文件）走 Maestro 异步调度。你不需要手动分派——路由矩阵全自动。

## 创建你自己的 Agent

在 `agents/` 下新建一个 `.md` 文件：

```markdown
---
name: my-agent
description: 我的自定义 Agent
tools: ["Read", "Write", "Bash"]
model: sonnet
---

# My Agent

## 角色
你是一个...

## 工作流
1. ...
2. ...

## 输出格式
STATUS: DONE
## 用户摘要
<精简结果>
```

然后在 `agent.yaml` 中加一段注册信息，在 `AGENTS.md` 路由矩阵中加一行——完成。

完整的扩展指南见 `docs/zh-CN/agents.md`。

## 适配其他 AI 工具

已有适配目录，复制对应格式的 agent/rules 文件即可：

| 工具 | 目录 | 说明 |
|------|------|------|
| Claude Code | `.claude/` | 原生安装目标 |
| Codex / MIMO | `.codex/` | OpenAI Codex CLI |
| Cursor | `.cursor/` | Cursor IDE 规则 |
| Gemini | `.gemini/` | Gemini CLI 配置 |

## 下一步

- 读完本文 -- 你已经可以用了
- 想看所有命令 -- `COMMANDS-QUICK-REF.md`
- 想深入 Maestro -- `docs/zh-CN/maestro.md`
- 想出问题了 -- `TROUBLESHOOTING.md`
- 想了解架构 -- `docs/zh-CN/ARCHITECTURE.md`
- 想贡献代码 -- `CONTRIBUTING.md`
