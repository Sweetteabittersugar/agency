---
name: injection-analysis
description: SQL注入、命令注入、XSS攻击面分析
category: security
loading: on-demand
triggers:
  keywords: ["注入","SQL注入","XSS","命令注入"]
---

# 注入分析

## 用途
检测并修复 SQL 注入、命令注入、XSS 等注入类安全漏洞。

## 核心规则
- SQL 查询必须使用参数化（`?` / `%s` / `$1`），不拼接用户输入
- 动态表名/列名无法参数化时，使用白名单映射
- 用户输入渲染到 HTML 前必须转义（`textContent` 或模板引擎自动转义）
- 避免 `eval` / `exec` / `Runtime.exec` 拼接用户输入
- 所有外部输入（URL 参数、表单、Header）视为不可信
