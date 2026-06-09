---
name: profiling-guide
description: CPU/内存/IO profiling 工具使用指南
category: performance
loading: on-demand
triggers:
  keywords: ["profiling","性能分析","CPU","瓶颈"]
---

# 性能剖析指南

## 用途
使用 profiling 工具定位 CPU、内存和 IO 瓶颈，用数据指导优化。

## 核心规则
- CPU 瓶颈用 `pprof` / `py-spy` / Chrome DevTools 火焰图定位
- 内存瓶颈用 heap snapshot 或 `tracemalloc` 找出分配热点
- IO 瓶颈通过分布式追踪（Jaeger/Zipkin）定位慢调用链
- 优化前先 profile，优化后再 profile，用数据对比验证
- 不凭直觉做性能优化，所有优化决策有 profile 数据支撑
