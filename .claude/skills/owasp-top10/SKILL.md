---
name: owasp-top10
description: OWASP Top 10 逐项检查，风险评级和修复建议
category: security
loading: on-demand
triggers:
  keywords: ["owasp","安全审计","安全扫描","安全漏洞"]
---

# OWASP Top 10

## 用途
按 OWASP Top 10 清单逐项审计应用安全，给出风险评级和修复方案。

## 核心规则
- 逐项对照 OWASP Top 10（2021版）检查：访问控制失效、加密失效、注入、不安全设计等
- 每项按 Critical/High/Medium/Low 评级
- Critical 问题必须立即修复，不允许推迟
- 提供每项的具体修复代码示例
- 安全审计结果记录到文档，作为发布前的必过门槛
