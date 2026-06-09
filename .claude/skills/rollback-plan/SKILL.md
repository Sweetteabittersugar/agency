---
name: rollback-plan
description: 数据库回滚、代码回滚、灰度切流的回滚方案
category: devops
loading: on-demand
triggers:
  keywords: ["回滚","rollback","灰度","紧急修复"]
---

# 回滚方案

## 用途
为每次发布准备可执行回滚方案，确保出现问题时快速恢复。

## 核心规则
- 每次发布前明确回滚触发条件：错误率 > x%、P99 延迟 > y ms、超过 z 分钟
- 代码回滚：保留上一个版本的镜像/Docker tag，一键切换
- 数据库回滚：对应 migration 的 down 脚本已测试
- 灰度发布：先切 5% 流量观察 5 分钟，逐步放量
- 回滚后必须复盘，记录时间线和根因
