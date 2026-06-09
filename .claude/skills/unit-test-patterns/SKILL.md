---
name: unit-test-patterns
description: AAA模式、边界值、Mock隔离的单元测试规范
category: testing
loading: on-demand
triggers:
  keywords: ["单元测试","unit test","测试函数","aaa"]
---

# 单元测试模式

## 用途
规范单元测试编写，确保测试结构统一、边界覆盖完整、Mock 隔离可靠。

## 核心规则
- 遵循 AAA 模式：Arrange（准备）、Act（执行）、Assert（断言），三段之间空行分隔
- 每个测试只测一个行为，函数名描述被测场景（`test_<函数>_<场景>_<预期>`）
- 边界值必测：空值、零值、最大/最小值、null/undefined
- 外部依赖（数据库、网络、文件系统）必须 Mock，保证测试可重复
- 测试数据和断言值硬编码，不通过计算动态生成
