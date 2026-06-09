---
name: database-migration
description: 增量迁移、回滚方案、零停机变更
category: coding
loading: on-demand
triggers:
  keywords: ["数据库迁移","schema变更","migration","回滚"]
---

# 数据库迁移

## 用途
规范数据库 schema 变更流程，确保增量可追溯、可回滚，最大限度地减少停机时间。

## 核心规则
- 每次迁移必须同时提供 up（正向）和 down（回滚）脚本
- 新增列必须设置默认值或允许 NULL，避免锁表
- 大表变更分批进行，每批处理不超过 10000 行
- 迁移前在 staging 环境完整验证，记录执行耗时
- 迁移脚本纳入版本控制，文件名带时间戳序号
