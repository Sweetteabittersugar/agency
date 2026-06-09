---
name: authz-patterns
description: JWT、OAuth2、RBAC、会话管理的最佳实践
category: security
loading: on-demand
triggers:
  keywords: ["认证","授权","JWT","OAuth","RBAC"]
---

# 认证授权模式

## 用途
规范认证和授权实现，防止权限绕过和会话劫持。

## 核心规则
- JWT 设置合理过期时间（access token 15min，refresh token 7d）
- 密码使用 bcrypt/argon2 哈希存储，不加自定义加密
- 敏感操作（删除、转账、权限变更）必须二次验证
- 权限检查在服务端执行，前端权限仅用于 UI 隐藏
- 登出时服务端失效 refresh token，不只清客户端
