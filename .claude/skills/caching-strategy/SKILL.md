---
name: caching-strategy
description: 多级缓存、失效策略、防止缓存穿透
category: performance
loading: on-demand
triggers:
  keywords: ["缓存","redis","失效","cache"]
---

# 缓存策略

## 用途
设计合理的多级缓存架构，平衡性能与数据一致性。

## 核心规则
- 热点数据优先缓存，过期时间按数据变更频率设置
- 缓存穿透用布隆过滤器或缓存空值防御
- 写操作时缓存失效（cache-aside），确保不返回脏数据
- 缓存键命名分层（`service:entity:id`），统一前缀便于管理
- 不过度缓存——先观察慢查询，只缓存真正瓶颈
