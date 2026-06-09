---
name: api-design
description: RESTful规范、版本管理、错误码统一
category: coding
loading: on-demand
triggers:
  keywords: ["API设计","接口设计","REST","端点"]
---

# API 设计

## 用途
指导 API 设计遵循 RESTful 规范，统一版本管理和错误码体系，确保接口一致性和可维护性。

## 核心规则
- URL 使用名词复数，层级不超过 3 层（如 `/api/v1/users/{id}/orders`）
- HTTP 方法语义正确：GET 查询、POST 创建、PUT 全量更新、PATCH 部分更新、DELETE 删除
- 统一响应格式：`{success, data, error, meta}`
- API 版本通过 URL 前缀管理（`/v1/`），破坏性变更必须升版本
- 错误码全局唯一，附带可读的 error message
