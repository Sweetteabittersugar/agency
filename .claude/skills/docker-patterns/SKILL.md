---
name: docker-patterns
description: 多阶段构建、健康检查、日志管理的最佳实践
category: devops
loading: on-demand
triggers:
  keywords: ["docker","容器","Dockerfile","镜像"]
---

# Docker 模式

## 用途
规范 Docker 镜像构建和容器运行，确保轻量、安全、可观测。

## 核心规则
- 使用多阶段构建分离编译环境和运行环境，减小镜像体积
- 基础镜像固定版本 tag，不使用 `latest`
- 容器内应用以非 root 用户运行
- 健康检查（HEALTHCHECK）覆盖所有服务端口
- 日志输出到 stdout/stderr，不做容器内轮转
