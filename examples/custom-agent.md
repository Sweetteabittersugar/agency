# 自定义 Agent 示例

展示如何为 agency-kit 创建和注册自定义 Agent。

## 1. 创建 Agent 文件

在 `agents/` 下（或按层级放入 L1_executor/ 等子目录）新建 `my-agent.md`，遵循统一格式：

```markdown
# My Agent — 一句话描述这个 Agent 做什么

## 角色
我是专门负责 [具体领域] 的 Agent。我只做 [范围]，不越界。

## 核心能力
- 能力 1：具体描述
- 能力 2：具体描述
- 能力 3：具体描述

## 使用场景
- 什么情况下用我
- 什么情况下不要用我（交给其他 Agent）

## 不做的事
- 不处理 [明确排除的范围]
- 不修改 [明确排除的文件类型]

## 输出格式
STATUS: [done|failed|need_input]
（详细结果）
## 用户摘要
（精简摘要，1-3 句话）
```

## 2. 注册到路由矩阵

在 `AGENTS.md` 的路由矩阵表格中添加一行：

```markdown
| [你的关键词] | `my-agent` | [简要说明] |
```

例如，新建一个专门做数据迁移的 Agent：

```markdown
| 迁移/数据/导入/导出 | `data-migrator` | 数据库迁移和导入导出 |
```

## 3. 注册到 Maestro 调度系统

如果使用 dispatch.py 调度，在 `maestro/agents.json` 中注册：

```json
{
  "my-agent": {
    "file": "agents/L1_executor/my-agent.md",
    "model": "sonnet",
    "timeout": 600,
    "description": "我的自定义 Agent"
  }
}
```

字段说明：
- `file` — Agent 定义文件的路径
- `model` — 推荐使用的模型（haiku / sonnet / opus / deepseek-v4-pro）
- `timeout` — 任务超时时间（秒）
- `description` — 简短描述

## 4. 验证

注册完成后验证：

```bash
# 查看 Agent 列表，确认新 Agent 出现在列表中
python maestro/dispatch.py --list

# 查看完整状态
@status

# 测试派发一个简单任务
python maestro/dispatch.py --agent my-agent --task "hello"
```

## 5. 进阶：添加专属命令

如果需要专属快捷命令，在 `commands/` 下创建同名的 `.md` 文件：

```markdown
# /my-command — 我的自定义命令

当用户输入 /my-command 或 @my-command 时触发，调用 my-agent 执行。
```

## 完整示例：data-migrator Agent

### agents/L1_executor/data-migrator.md
```markdown
# Data Migrator — 数据库迁移和导入导出

## 角色
专门处理数据库结构变更、数据导入导出、格式转换。

## 核心能力
- 生成数据库迁移脚本（SQL、Alembic、golang-migrate）
- 数据格式转换（CSV ↔ JSON ↔ Parquet）
- 大数据批量导入导出
- 迁移前后数据完整性校验

## 使用场景
- 需要新增/修改数据库表结构
- 需要从外部数据源导入数据
- 需要在不同格式间转换数据
- 迁移脚本的 dry-run 和回滚

## 不做的事
- 不处理业务逻辑（交给 coder）
- 不修改应用代码（交给 coder）
- 不创建新 API 接口（交给 coder）

## 输出格式
STATUS: [done|failed|need_input]
（迁移脚本内容或操作结果）
## 用户摘要
（迁移操作摘要）
```

### AGENTS.md 路由条目
```markdown
| 迁移/数据/导入/导出/DDL | `data-migrator` | 数据库迁移和导入导出 |
```

### agents.json 注册
```json
{
  "data-migrator": {
    "file": "agents/L1_executor/data-migrator.md",
    "model": "sonnet",
    "timeout": 900,
    "description": "数据库迁移和导入导出"
  }
}
```
