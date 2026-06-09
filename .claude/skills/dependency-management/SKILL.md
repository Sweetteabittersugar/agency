---
name: dependency-management
description: 最小依赖原则、版本锁定、安全审计
category: coding
loading: on-demand
triggers:
  keywords: ["依赖","package","npm","pip","升级"]
---

# 依赖管理

## 用途
管理项目依赖，防止依赖膨胀、版本冲突和安全漏洞引入。

## 核心规则
- 新增依赖前先检查是否已有替代方案或标准库可替代
- 锁定精确版本（`package-lock.json`、`poetry.lock`），不使用 `^` 或 `~` 范围
- 升级依赖前查看 CHANGELOG，确认无破坏性变更
- 定期运行 `npm audit` / `pip audit` 扫描已知漏洞
- 为每个依赖记录引入理由，便于后续清理
