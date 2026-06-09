---
name: regression-checklist
description: 改动后必检项清单，覆盖常见遗漏点
category: testing
loading: on-demand
triggers:
  keywords: ["回归","检查清单","遗漏","副作用"]
---

# 回归检查清单

## 用途
每次代码改动后强制执行的检查清单，覆盖最容易遗漏的回归点。

## 核心规则
- 改动后立即运行相关模块的全部测试，不跳过
- 检查受影响的上游调用方是否兼容新接口
- 确认错误状态下的降级行为仍然生效
- 验证 API 响应结构未变更（新增字段可，删除/重命名字段不可）
- 检查 SQL 查询计划是否有退化（EXPLAIN 对比）
