---
name: logging-standards
description: 分级日志、结构化输出、敏感信息脱敏
category: coding
loading: on-demand
triggers:
  keywords: ["日志","log","调试信息","print"]
---

# 日志规范

## 用途
统一日志输出格式和级别标准，确保生产环境日志可检索、可分析，并保护敏感数据不泄露。

## 核心规则
- 使用正确的日志级别：DEBUG 调试、INFO 关键流程、WARNING 可恢复异常、ERROR 需人工介入
- 生产环境禁止使用 `print` / `console.log`，必须通过日志框架输出
- 日志输出 JSON 结构化格式，每条含 `timestamp`、`level`、`message`、`context`
- 敏感字段（密码、token、身份证号）自动脱敏后再写入日志
- 关键操作入口（登录、支付、删除）必须打 INFO 日志
