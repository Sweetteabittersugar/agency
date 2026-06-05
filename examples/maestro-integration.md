# Maestro 集成示例

展示如何将 agency-kit 的 Maestro 调度引擎集成到你现有的 Claude Code 项目中。

## 最小集成

只需两个核心脚本即可启用 Agent 调度：

### 文件清单
```
your-project/
├── maestro/
│   ├── dispatch.py      # Agent 任务调度器
│   └── gateway.py       # 结果网关（提取摘要）
├── agents/              # Agent 定义文件
│   └── coder.md         # 至少一个 Agent
├── AGENTS.md            # 路由矩阵
└── CLAUDE.md            # 入口指令（引用 maestro）
```

### 1. 复制核心脚本

```bash
# 从 agency-kit 复制
cp agency-kit/maestro/dispatch.py your-project/maestro/
cp agency-kit/maestro/gateway.py your-project/maestro/
cp agency-kit/maestro/sandbox.py your-project/maestro/  # 可选：隔离执行
```

### 2. 创建最小 Agent

```bash
mkdir -p your-project/agents
```

`agents/coder.md`:
```markdown
# Coder — 代码执行者

## 角色
我是代码执行者，负责写代码、改代码、重构。

## 核心能力
- 编写新功能
- 修复 bug
- 代码重构
- 文件操作

## 输出格式
STATUS: [done|failed|need_input]
（详细结果）
## 用户摘要
（精简摘要）
```

### 3. 配置 CLAUDE.md

在项目 `CLAUDE.md` 中添加：

```markdown
## Agent 调度

派任务前运行 `python maestro/cleanup-agents.py` 清理闲置进程
@agent名 按 AGENTS.md 执行

### 路由矩阵
| 关键词 | Agent |
|--------|-------|
| 写/改/重构/代码 | @coder |
| 查/搜/找/分析 | @explorer |
| 通用/配置/杂务 | @general-worker |

### 派发命令
@coder <task>        → python maestro/dispatch.py --agent coder --task "<task>"
@status              → python maestro/dispatch.py --status
@result <task_id>    → python maestro/gateway.py <task_id>
```

### 4. 验证

```bash
# 测试调度
python maestro/dispatch.py --agent coder --task "echo hello"

# 查看状态
python maestro/dispatch.py --status

# 查看结果（用返回的 task_id）
python maestro/gateway.py <task_id>
```

## 完整集成

复制所有 Maestro 脚本以获得完整功能：

```bash
cp -r agency-kit/maestro/ your-project/maestro/
```

### 完整文件清单
```
maestro/
├── dispatch.py          # Agent 任务调度器（核心）
├── gateway.py           # 结果网关
├── sandbox.py           # 隔离执行沙箱
├── cost-tracker.py      # 费用实时追踪
├── cost-analyzer.py     # 费用深度分析（每日 22:00 自动）
├── task-tracker.py      # 任务看板
├── task-board.json      # 任务看板数据
├── cost.db              # 费用数据库（自动创建）
├── agents.json          # Agent 配置注册表
├── cleanup-agents.py    # 闲置进程清理
├── cost-writer.py       # 费用写入（API 调用时触发）
├── notif-proxy.py       # 通知代理（飞书等）
└── transcript-parser.py # 对话记录解析
```

### 额外功能

| 功能 | 命令 | 依赖 |
|------|------|------|
| 费用追踪 | `@cost` / `@cost --days 7` | cost-tracker.py + cost.db |
| 深度分析 | `@cost --analyze` | cost-analyzer.py + cost.db |
| 任务看板 | `@tracker` / `@tracker --list` | task-tracker.py + task-board.json |
| 实时看板 | `@cost --live` | cost-tracker.py |
| 进程清理 | `python maestro/cleanup-agents.py` | cleanup-agents.py |
| 费用写入 | 自动（API 调用时触发） | cost-writer.py |

## 自定义 Agent 配置

编辑 `maestro/agents.json`：

```json
{
  "coder": {
    "file": "agents/coder.md",
    "model": "deepseek-v4-pro",
    "timeout": 600,
    "description": "代码执行者"
  },
  "explorer": {
    "file": "agents/explorer.md",
    "model": "haiku",
    "timeout": 300,
    "description": "代码探索员"
  },
  "reviewer": {
    "file": "agents/code-reviewer.md",
    "model": "sonnet",
    "timeout": 900,
    "description": "代码审查员"
  },
  "my-custom-agent": {
    "file": "agents/my-agent.md",
    "model": "sonnet",
    "timeout": 600,
    "description": "我的自定义 Agent"
  }
}
```

## Cron 定时任务

在 `.claude/scheduled_tasks.json` 中配置定时任务：

```json
{
  "tasks": [
    {
      "name": "每日费用分析",
      "schedule": "0 22 * * *",
      "command": "python maestro/cost-analyzer.py",
      "enabled": true
    },
    {
      "name": "闲置进程清理",
      "schedule": "*/30 * * * *",
      "command": "python maestro/cleanup-agents.py",
      "enabled": true
    },
    {
      "name": "工作日志整理",
      "schedule": "0 22 * * *",
      "command": "python maestro/daily-log.py",
      "enabled": true
    }
  ]
}
```

## Hook 集成

在 `.claude/settings.json` 的 hooks 中集成：

```json
{
  "hooks": {
    "SessionStart": [
      {
        "command": "bash hooks/SessionStart.sh"
      }
    ],
    "PostToolUse": [
      {
        "command": "python maestro/cost-writer.py",
        "matcher": "anthropic:.*"
      }
    ],
    "Stop": [
      {
        "command": "bash hooks/Stop.sh"
      }
    ],
    "PreCompact": [
      {
        "command": "bash hooks/PreCompact.sh"
      }
    ]
  }
}
```

## 渐进式采用路线

```
第1天: 最小集成（dispatch.py + gateway.py + 1 个 Agent）
  → 能调度任务，Agent 能执行

第3天: 添加 cost-tracker.py + cost-writer.py
  → 能看到费用

第7天: 添加 task-tracker.py + task-board.json
  → 能跟踪任务进度

第14天: 添加 cost-analyzer.py + 定时任务
  → 自动化费用分析和优化建议

第30天: 添加更多 Agent + 自定义规范
  → 完整的个性化工作流
```
