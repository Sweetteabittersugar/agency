---
name: test-data-generator
description: 使用 faker 生成随机但确定的测试数据
category: testing
loading: on-demand
triggers:
  keywords: ["测试数据","生成数据","faker","数据工厂"]
---

# 测试数据生成器

## 用途
利用 faker 类库生成大量逼真测试数据，支持设定 seed 保证可重复性。

## 核心规则
- 所有测试数据通过 faker 生成，固定 seed（如 `Faker.seed(42)`）
- 数据集大小可配置，批量生成至少覆盖 100 条记录
- 关联数据保持引用完整性（外键、唯一约束等）
- 边界异常数据（超长、SQL 注入字符串、XSS payload）混入数据集
- 生成脚本独立存放，CI 中可复用
