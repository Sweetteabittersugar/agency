---
name: cost
description: "成本追踪。当用户提到费用、成本、用量、账单、@cost 时使用。"
---

# Cost — 成本追踪

追踪和分析 AI API 调用费用，提供多维度的成本可视化和优化建议。

## 使用场景

- 查看当日 API 费用：`@cost`
- 查看最近 N 天趋势：`@cost --days 7`
- 实时监控模式：`@cost --live`
- 深度分析报告：`@cost --analyze`
- 费用异常检测：自动（每日 22:00）

## 支持的查询维度

### 按模型
统计各模型的调用次数、token 消耗、费用占比。

### 按日期
每日费用趋势图，识别费用峰值日期。

### 按 Agent
按 Agent（reasonix、explorer、test 等）统计费用，发现异常 Agent。

### 按项目
如果多个项目共用同一 API key，可按项目标签拆分费用。

## 异常告警规则

### 黄色告警（关注）
| 条件 | 阈值 | 说明 |
|------|------|------|
| 单日总费用 | > $5.00 | 当日费用偏高 |
| reasonix 单次平均 token | 超昨日 2 倍 | 任务可能携带过多上下文 |
| 主会话入向 token | > 50,000 | 上下文逐步膨胀 |

### 红色告警（需处理）
| 条件 | 阈值 | 说明 |
|------|------|------|
| 单次调用费用 | > $0.50 | 单次 API 调用异常昂贵 |
| Opus 处理小任务 | 平均 < 2,000 tokens | 大材小用，浪费额度 |
| explorer/test 使用 sonnet | 任何次数 | 简单任务误用昂贵模型 |

## 费用优化建议模板

cost-analyzer.py 每日 22:00 自动生成优化建议：

1. **切换模型** — 主会话长任务委托给 reasonix agent，减少 main_claude 上下文膨胀
2. **降级任务** — explorer/test 强制使用 haiku，确认 dispatch 未错误覆盖 model 参数
3. **压缩上下文** — 主会话入向 > 80K 时降低压缩阈值或手动 /compact
4. **拆分大任务** — reasonix 单次超 50K tokens 时拆分复杂任务为多步骤

## 与脚本的配合

### cost-tracker.py — 实时追踪
```
python maestro/cost-tracker.py              # 今日汇总
python maestro/cost-tracker.py --days 7     # 最近 N 天
python maestro/cost-tracker.py --live       # 实时看板（5秒刷新）
```

输出：通道明细表 + 日均 + 预估月费 + 异常告警

### cost-analyzer.py — 深度分析（每日 22:00 自动）
```
python maestro/cost-analyzer.py             # 分析今日数据
python maestro/cost-analyzer.py 2026-06-04  # 分析指定日期
```

输出：通道分布 + reasonix 异常 + 模型误用 + 主会话 token + 综合建议

## 模型性价比参考表

| 模型 | 输入 $/1M tokens | 输出 $/1M tokens | 适用场景 | 性价比 |
|------|------------------|-------------------|----------|--------|
| deepseek-v4-flash | $0.14 | $0.28 | 简单搜索、轻量任务 | 最高 |
| deepseek-v4-pro | $0.435 | $0.87 | 主力开发、代码生成 | 高 |
| haiku | $0.25 | $1.25 | 搜索、探索、测试 | 高 |
| deepseek-v3 | $0.27 | $1.10 | 通用中文任务 | 高 |
| deepseek-r1 | $0.55 | $2.19 | 复杂推理 | 中 |
| sonnet | $3.00 | $15.00 | 复杂编码、审查 | 中 |
| mimo-v2-pro | $1.00 | $3.00 | 多模态任务 | 中 |
| opus | $15.00 | $75.00 | 创作、深度推理 | 低 |

> 定价参考日期：2026-05-31（DeepSeek V4 永久降价 75% 后）

## 选模型原则

1. **简单任务用便宜模型** — 搜索、探索、format 检查 → haiku 或 deepseek-v4-flash
2. **主力开发用性价比王者** — 代码生成、重构 → deepseek-v4-pro
3. **复杂审查用 sonnet** — 安全审计、代码审查 → sonnet
4. **深度创作才用 opus** — 小说写作、架构设计 → opus
5. **多模态用 mimo** — 图像理解、PDF 分析 → mimo-v2-pro

## 常用命令速查

| 命令 | 功能 |
|------|------|
| `@cost` | 今日费用汇总 |
| `@cost --days 7` | 最近 7 天趋势 |
| `@cost --days 30` | 月费用报告 |
| `@cost --live` | 实时看板（Ctrl+C 退出） |
| `@cost --analyze` | 完整分析报告（同 cost-analyzer.py） |
