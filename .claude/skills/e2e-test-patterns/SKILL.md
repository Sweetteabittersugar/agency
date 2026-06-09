---
name: e2e-test-patterns
description: 用户视角端到端测试，关键路径用 Playwright
category: testing
loading: on-demand
triggers:
  keywords: ["e2e","端到端","playwright","浏览器测试"]
---

# E2E 测试模式

## 用途
从用户视角验证关键业务流程，确保前后端联通无误、UI 交互符合预期。

## 核心规则
- 只对核心业务路径写 E2E：注册/登录、下单/支付、关键 CRUD
- 使用 data-testid 选择器定位元素，不依赖 CSS class 或 XPath
- 每个 E2E 测试独立，不共享状态，测试前重置数据
- 加入显式等待（waitForSelector），不依赖固定 sleep
- 失败时截图 + 录屏，输出到 CI artifacts
