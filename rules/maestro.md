# Maestro Agent Dispatch Rules

当用户消息包含 @agent名 时，直接执行对应操作，不反问不确认。

## 命令映射

@agents              → python $PROJECT_ROOT/maestro/dispatch.py --list
@reasonix <task>     → python $PROJECT_ROOT/maestro/dispatch.py --agent reasonix --task "<task>"
@coder <task>        → python $PROJECT_ROOT/maestro/dispatch.py --agent coder --task "<task>"
@reviewer <task>     → python $PROJECT_ROOT/maestro/dispatch.py --agent reviewer --task "<task>"
@explorer <task>     → python $PROJECT_ROOT/maestro/dispatch.py --agent explorer --task "<task>"
@test <task>         → python $PROJECT_ROOT/maestro/dispatch.py --agent test --task "<task>"
@writer <task>       → python $PROJECT_ROOT/maestro/dispatch.py --agent writer --task "<task>"
@local <task>         → python $PROJECT_ROOT/maestro/dispatch.py --agent local --task "<task>"
@general-worker <task> → python $PROJECT_ROOT/maestro/dispatch.py --agent general-worker --task "<task>"
@docker_worker <task> → python $PROJECT_ROOT/maestro/dispatch.py --agent docker_worker --task "<task>"
@status              → python $PROJECT_ROOT/maestro/dispatch.py --status
@status <agent>      → python $PROJECT_ROOT/maestro/dispatch.py --status <agent>
@result <task_id>    → python $PROJECT_ROOT/maestro/gateway.py <task_id>
@raw <task_id>       → python $PROJECT_ROOT/maestro/gateway.py --raw <task_id>
@tracker             → python $PROJECT_ROOT/maestro/task-tracker.py
@tracker --list      → python $PROJECT_ROOT/maestro/task-tracker.py --list
@tracker --progress  → python $PROJECT_ROOT/maestro/task-tracker.py --progress
@tracker --task <id> → python $PROJECT_ROOT/maestro/task-tracker.py --task <id>
@tracker --sync      → python $PROJECT_ROOT/maestro/task-tracker.py --sync
@cost                → python $PROJECT_ROOT/maestro/cost-tracker.py
@cost --days 7       → python $PROJECT_ROOT/maestro/cost-tracker.py --days 7
@cost --live         → python $PROJECT_ROOT/maestro/cost-tracker.py --live


## 任务分级

| 级别 | 标准 | 走哪条路 |
|------|------|----------|
| 轻活 | 单文件读写、grep/glob搜索、简单编辑、查状态、一句话回答 | Agent 工具直调（general-purpose） |
| 重活 | 多文件修改、worktree隔离、代码重构、功能开发、大量文件操作、预估超3分钟 | dispatch.py（reasonix/coder/general-worker） |

判断标准：涉及3+文件的写操作，或需要隔离环境 → 重活，走 dispatch

## 规则
1. 识别到 @agent 指令后直接执行，不等用户确认
2. 将 dispatch.py 输出简洁告知用户
3. dispatch 是异步操作，告诉用户已派出即可
4. @status 时主动报告进度
5. 单 agent 派发为异步操作，告诉用户已派出即可
6. 轻活不要过 dispatch——直接用 Agent 工具派 general-purpose，减少调度开销
