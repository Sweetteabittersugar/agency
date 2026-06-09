---
name: health-check-patterns
description: 存活探针、就绪探针、自定义健康指标
category: devops
loading: on-demand
triggers:
  keywords: ["健康检查","health","探针","监控"]
---

# 健康检查模式

## 用途
实现可靠的健康检查端点，确保负载均衡和编排系统能正确判断服务状态。

## 核心规则
- `/healthz` 存活探针：只检查进程是否存活，轻量且不依赖外部服务
- `/readyz` 就绪探针：检查依赖服务（数据库、Redis、外部API）是否可达
- 健康检查端点独立于业务端口，不被限流
- 拉取式检查（pull），不依赖服务主动上报
- 健康检查返回 JSON，含 `status`、`timestamp`、`checks` 详细信息
