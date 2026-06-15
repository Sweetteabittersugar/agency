# Session Flow — 会话工作流速查卡

> AI 每次会话开始时读这个。30 秒过一遍。

## 开始时

```
1. /cost                           — 看当前花费
2. 读 .context/handoff.md          — 上次状态
3. 读 .context/BACKLOG.md          — 有待做的吗
```

## 任务分派

| 任务类型 | 怎么做 | 为什么 |
|---------|--------|--------|
| 搜索/读文件/审查 | **subagent**（Haiku 自动） | 脏活不占主上下文 |
| 3+文件写操作 | **orchestrator → 并行 agent** | 各自干净上下文 |
| 单文件修 bug | **主 agent 直做** | 无协调开销 |
| 调试根因 | **主 agent** | 需要连续上下文 |

## 压缩节奏

```
~100K token → /compact（50% 规则，不是等 400K）
compact 前 30 秒 → 更新 handoff.md + decisions/
compact 后 → 读 handoff.md 恢复状态
```

## 结束时

```
1. /cost                           — 看花费
2. 更新 .context/handoff.md        — 状态/下一步
3. 完成项移到 BACKLOG 已完成区
```

## 底线

- 用户指令永远不压缩
- 精确值（端口/阈值/版本）必须写文件再 compact
- 改代码前先读 decisions/ 和 mistakes/
