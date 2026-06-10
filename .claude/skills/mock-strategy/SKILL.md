---
name: mock-strategy
description: Mock 策略 —— 测试替身选择、外部依赖模拟、Mock 过度使用的危害与边界
category: 测试
loading: on-demand
triggers:
  keywords: ["mock", "打桩", "模拟", "测试替身", "stub", "fake", "fixture"]
---

# Mock 策略

## 概述
提供测试替身（Test Double）的系统化使用指南，帮助区分 Mock、Stub、Fake、Spy 的适用场景，避免 Mock 滥用导致的测试脆弱性。

## 使用场景
- 单元测试中需要隔离外部依赖（数据库、HTTP、消息队列）
- 测试第三方 API 集成但不想每次都真实调用
- 模拟难以触发的异常路径（超时、500 错误、限流）
- 评审测试代码中的 Mock 使用是否合理

## 核心原则
1. **Mock 越少越好**：Mock 是必要的恶，不是美德。优先真对象（值对象、简单 POJO）、Fake（内存实现）、再考虑 Mock。
2. **Mock 边界不是实现细节**：Mock 只对外部依赖的接口做，不 Mock 自己的类或函数。Mock 实现细节导致测试绑定于代码结构。
3. **使用 Fake 替代 Mock**：对于可控制的依赖（如 Repository），优先实现内存版 Fake 而非 Mock。Fake 更稳定可复用。
4. **不 Mock 你不拥有的接口**：第三方 SDK 的接口可能随版本变化。封装一层适配器，Mock 适配器而非 Mock 第三方接口。
5. **验证行为而非调用次数**：Mock 验证应聚焦"是否正确调用了"而非"调用了几次"。过度计数验证使测试脆弱。

## 测试替身分类
- **Dummy**：只传参不使用的占位对象
- **Stub**：返回预设值的简单替身
- **Spy**：记录调用信息，事后验证
- **Mock**：预设期望，自动验证
- **Fake**：有实际业务逻辑的轻量实现（如内存数据库）

## 检查清单
- [ ] Mock 是否仅限于外部依赖边界的接口？
- [ ] 是否优先使用 Fake 或 Stub 而非 Mock？
- [ ] 是否有不合理的调用次数验证（`expect().toHaveBeenCalledTimes(3)`）？
- [ ] 是否 Mock 了自己拥有的类而非仅外部接口？
- [ ] Mock 数据是否模拟了真实场景（包括异常场景）？
