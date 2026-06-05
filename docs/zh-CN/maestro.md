# Maestro — 多智能体调度系统

## 架构

```
用户任务
    │
    ▼
路由矩阵 (AGENTS.md)
    │
    ├── 轻活 → Agent 工具直调
    │
    └── 重活 → dispatch.py
                    │
                    ▼
              sandbox.py (隔离执行)
                    │
                    ▼
              gateway.py (结果提取)
                    │
                    ▼
              用户看到摘要
```

## 核心脚本

### dispatch.py — 任务分发引擎

```bash
# 列出所有 agent
python maestro/dispatch.py --list

# 查看状态
python maestro/dispatch.py --status

# 派发任务
python maestro/dispatch.py --agent coder --task "修复 bug"
```

### cost-tracker.py — 成本追踪

```bash
# 今日费用
python maestro/cost-tracker.py

# 最近 7 天
python maestro/cost-tracker.py --days 7

# 实时监控
python maestro/cost-tracker.py --live
```

### cost-analyzer.py — 费用分析

```bash
python maestro/cost-analyzer.py
```

输出按模型、日期、Agent 维度的费用趋势和异常告警。

### task-tracker.py — 任务看板

```bash
# 任务总览
python maestro/task-tracker.py

# 任务列表
python maestro/task-tracker.py --list

# 查看进度
python maestro/task-tracker.py --progress

# 指定任务
python maestro/task-tracker.py --task <id>
```

### cleanup-agents.py — 进程清理

```bash
python maestro/cleanup-agents.py
```

清理闲置的 agent 进程，释放资源。

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CLAUDE_PROJECT_DIR` | 项目根目录 | 当前工作目录 |
| `REASONIX_API_KEY` | DeepSeek API 密钥 | — |

## 扩展

在 `maestro/dispatch.py` 的 `AGENTS` 字典中添加新 agent 即可集成到调度系统。
