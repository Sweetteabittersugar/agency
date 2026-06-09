---
name: integration-test-patterns
description: API测试、数据库测试、组件集成的集成测试规范
category: testing
loading: on-demand
triggers:
  keywords: ["集成测试","API测试","integration test"]
---

# 集成测试模式

## 用途
规范集成测试编写，确保组件间协作正确、外部依赖行为符合预期。

## 核心规则
- 集成测试使用真实（或容器化的）依赖，不做 Mock
- API 测试覆盖完整的请求-响应周期：状态码、响应体结构、错误码
- 数据库测试使用测试专用数据库，每次测试后回滚/清理数据
- 测试用例之间完全隔离，不依赖执行顺序
- 集成测试命名带 `Integration` 标记（或用 `@pytest.mark.integration`），与单元测试分开运行
