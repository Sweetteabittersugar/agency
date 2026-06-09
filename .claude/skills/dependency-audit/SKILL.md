---
name: dependency-audit
description: CVE扫描、许可证检查、供应链安全审计
category: security
loading: on-demand
triggers:
  keywords: ["依赖审计","CVE","漏洞扫描","供应链"]
---

# 依赖审计

## 用途
定期审查项目依赖的安全性，识别已知漏洞和许可证风险。

## 核心规则
- CI 中集成 `npm audit` / `pip audit` / `snyk`，发现 HIGH/CRITICAL 即阻断
- 每次 PR 自动扫描新增依赖的已知 CVE
- 检查依赖的许可证是否与项目协议兼容（GPL/AGPL 特别注意）
- 锁定依赖的完整性哈希，防止供应链投毒
- 定期审查直接依赖数量，超过 50 个时评估必要性
