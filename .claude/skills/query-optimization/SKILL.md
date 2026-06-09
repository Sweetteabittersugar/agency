---
name: query-optimization
description: EXPLAIN 分析、索引建议、慢查询定位
category: performance
loading: on-demand
triggers:
  keywords: ["查询优化","慢查询","索引","SQL性能"]
---

# 查询优化

## 用途
分析和优化数据库查询性能，定位慢查询并给出索引和重构建议。

## 核心规则
- 新 SQL 查询上线前必须过 EXPLAIN，确认执行计划合理
- 为高频查询字段建立索引，避免全表扫描
- 避免 SELECT *，只取需要的列
- N+1 查询通过 eager loading（prefetch_related / include）解决
- 定期分析慢查询日志，TOP 10 必须纳入优化计划
