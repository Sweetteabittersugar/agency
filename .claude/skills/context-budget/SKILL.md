---
name: context-budget
description: Token 预算分配 — 为 System/History/Task/Output 各段设定 token 上限，防止上下文溢出
category: optimization
loading: on-demand
triggers:
  keywords: ["token", "预算", "上下文", "context", "budget", "窗口", "压缩"]
---

# Token 预算分配

## 用途
在 Agent 执行任务前，根据 Profile 级别和任务复杂度，分配各段 token 预算。确保总用量不超模型上下文窗口，并在接近上限时触发压缩。

## 预算模型

### 分区定义
```
总窗口 = System + History + Task + Output + Reserve
```

| 分区 | 用途 | minimal (3K) | standard (8K) | full (20K) |
|------|------|-------------|---------------|------------|
| System | 系统提示词 | 800 (27%) | 2000 (25%) | 4000 (20%) |
| History | 对话历史 | 500 (17%) | 2000 (25%) | 6000 (30%) |
| Task | 当前任务 | 1200 (40%) | 3000 (38%) | 7000 (35%) |
| Output | 预留输出 | 300 (10%) | 600 (7%) | 2000 (10%) |
| Reserve | 安全余量 | 200 (6%) | 400 (5%) | 1000 (5%) |

### Profile 对应的模型上下文窗口

| Profile | 模型 | 窗口大小 |
|---------|------|---------|
| minimal | haiku | 8K |
| standard | sonnet | 32K |
| full | sonnet/opus | 200K |

## 核心规则

### 1. 预算检查
每次 Agent 调用前检查：
- 当前 System prompt 长度是否在预算内
- 历史消息累计 token 是否接近 History 预算
- Task 描述长度是否在 Task 预算内

### 2. 溢出处理
- History 接近上限 (90%) → 触发压缩（保留最近 3 轮 + 摘要前文）
- System 固定不压缩
- Task 超预算 → 分片或提示用户精简

### 3. 实时监控
- 输出过程中监控 Output 累计 token
- 接近 Output 预算 (80%) 时提示 Agent 精简输出
- 超过 Output 预算 → 截断并警告

### 4. 与 Profile 联动
- minimal: 严格预算，任何分区超 90% 即告警
- standard: 弹性预算，允许临时超 10%
- full: 宽松预算，仅总窗口超 90% 时告警

## Token 估算公式
```
英文: tokens ≈ chars / 4
中文: tokens ≈ chars / 2
代码: tokens ≈ chars / 3
```

## 输出格式

```json
{
  "profile": "standard",
  "total_window": 32000,
  "allocated": {
    "system": {"budget": 2000, "used": 1800, "percent": 90.0},
    "history": {"budget": 2000, "used": 1200, "percent": 60.0},
    "task": {"budget": 3000, "used": 1500, "percent": 50.0},
    "output": {"budget": 600, "used": 0, "percent": 0.0},
    "reserve": {"budget": 400, "used": 0, "percent": 0.0}
  },
  "status": "ok",
  "warnings": []
}
```
