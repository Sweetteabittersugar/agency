---
name: ci-pipeline
description: GitHub Actions / GitLab CI 分阶段构建、缓存优化
category: devops
loading: on-demand
triggers:
  keywords: ["CI","pipeline","GitHub Actions","构建"]
---

# CI 管道

## 用途
设计高效 CI 管道，分阶段构建、合理缓存、快速反馈。

## 核心规则
- 管道分阶段：lint → test → build → deploy，前阶段失败不执行后阶段
- 缓存 node_modules、pip cache、Gradle cache，避免每次从头下载
- 并行运行无依赖的 job（lint + unit test）
- 主干分支 push 自动触发完整管道，PR 触发轻量验证
- 构建失败时 CI 输出必须有失败原因摘要，不全屏日志
