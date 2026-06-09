---
name: cost-aware-pipeline
description: 调用 API 前估算成本、模型降级策略、预算告警
category: meta
loading: on-demand
triggers:
  keywords: ["成本","费用","预算","省钱","haiku"]
---

# 成本感知管道

## 用途
在 AI 辅助工作流中嵌入成本意识，自动选择性价比最优的模型和执行策略。

## 核心规则
- 每次调用 LLM API 前，按 token 估算成本，超预算时降级模型（Sonnet → Haiku）
- 简单任务（搜索、替换、格式化）永远用轻量模型或规则引擎，不走大模型
- 设置每日/每月预算上限，接近阈值时自动降级并告警
- 定期分析 API 调用日志，识别可优化的高频低成本任务
- 成本数据记录到追踪系统，每周生成按模块/agent 的消费报告
