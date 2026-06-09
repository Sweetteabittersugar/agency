---
name: mock-factory
description: 自动生成 Mock 数据，覆盖边界值
category: testing
loading: on-demand
triggers:
  keywords: ["mock","模拟数据","假数据","fixture"]
---

# Mock 工厂

## 用途
统一 Mock 数据生成方式，确保测试数据覆盖正常值和边界值，避免手工编写重复 fixture。

## 核心规则
- 为每个核心数据模型建立 Mock 工厂函数（`make_user(**overrides)`）
- Mock 数据必须覆盖：正常值、空值、最大值、最小值、超长字符串
- 工厂函数支持 partial override，测试只需传入关注的字段
- Mock 对象结构与真实数据模型一致，类型不对齐时报错
- 避免在测试中直接构造原始 dict/object，统一走工厂
