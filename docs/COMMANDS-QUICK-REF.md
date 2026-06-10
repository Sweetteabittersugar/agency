# 命令快速参考

> 所有 Agent 命令、快捷命令、斜杠命令和 Maestro 脚本一览。

## Agent 命令

| 命令 | 功能 | 适用场景 |
|------|------|----------|
| `@coder` | 直接写代码，不转派不反问 | 代码实现、功能开发 |
| `@code-reviewer` | 四维度代码审查 | 代码写完后 |
| `@explorer` | 代码库搜索与结构分析 | 查找、定位、分析 |
| `@test-runner` | 测试执行与结果分析 | 测试、验证 |
| `@general-worker` | 通用杂务 | 整理、配置、转换 |
| `@webnovel-writer` | 小说创作 | 写作任务 |
| `@planner` | 实现规划与架构设计 | 复杂功能、架构决策 |
| `@security-reviewer` | 安全漏洞深度检测 | 敏感代码审查 |
| `@cost-analyst` | API 费用分析与优化 | 成本审查 |

## 快捷命令

| 命令 | 功能 | 变体 |
|------|------|------|
| `@agents` | 列出所有可用 Agent | — |
| `@status` | 查看 Agent 任务状态 | `@status <agent>` 查看指定 Agent |
| `@cost` | 查看今日 API 费用 | `@cost --days 7`、`@cost --live` |
| `@tracker` | 查看任务看板 | `@tracker --list`、`@tracker --progress`、`@tracker --task <id>`、`@tracker --sync` |
| `@result <task_id>` | 查看任务结果摘要 | — |
| `@raw <task_id>` | 查看任务原始输出 | — |

## 斜杠命令

| 命令 | 功能 | 说明 |
|------|------|------|
| `/design` | 进入设计模式 | 四阶段需求澄清（目标→约束→方案→确认） |
| `/compress` | 手动压缩上下文 | 保留关键决策和用户偏好 |

## Maestro 脚本命令

| 命令 | 功能 | 路径 |
|------|------|------|
| `python maestro/dispatch.py --agent <name> --task "<desc>"` | 派发任务到指定 Agent | 用于手动调度 |
| `python maestro/dispatch.py --status` | 查看最近任务 | 最近 10 个 |
| `python maestro/dispatch.py --list` | 列出所有 Agent | — |
| `python maestro/cost-tracker.py` | 完整费用报告 | 支持 `--days N` |
| `python maestro/cost-analyzer.py` | 费用趋势分析 | 图表输出 |
| `python maestro/task-tracker.py` | 任务看板管理 | 支持 `--list`、`--progress`、`--task <id>` |
| `python maestro/task-tracker.py --sync` | 同步僵尸任务 | 清理过期任务 |
| `python maestro/gateway.py <task_id>` | 结果网关 | 提取摘要返回 |
| `python maestro/gateway.py --raw <task_id>` | 查看原始结果 | 完整输出 |
| `python maestro/cleanup-agents.py` | 清理闲置进程 | 自动释放资源 |

## 使用提示

- **轻活**（单文件读写、搜索、简单查询）— 直接 @agent
- **重活**（3+ 文件写操作、需要隔离）— 使用 `python maestro/dispatch.py` 派发
- Maestro 命令需在项目根目录或 `PYTHONPATH` 中包含 `maestro/` 时执行
- 不确定用什么 Agent 时，直接描述任务即可——路由矩阵会自动选择

## 安装后的验证步骤

```bash
@status          # 确认 Agent 系统正常
@cost            # 确认成本追踪可用
/design          # 确认设计模式正常
python -m pytest tests/ -v   # 确认测试通过
```

## 相关文件

| 文件 | 内容 |
|------|------|
| `AGENTS.md` | Agent 路由矩阵与使用指南 |
| `CLAUDE.md` | Claude Code 自动加载入口 |
| `CONTRIBUTING.md` | 贡献指南 |
| `maestro/` | Maestro 脚本源码 |
