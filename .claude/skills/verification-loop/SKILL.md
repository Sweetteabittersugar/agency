---
name: verification-loop
description: 改动后立即验证，回归测试、pass@3 确认
category: meta
loading: on-demand
triggers:
  keywords: ["验证","确认","检查","verify","回归"]
---

# 验证闭环

## 用途
确保每次代码改动后都经过完整验证，不做"改完就跑"的假设验证。

## 核心规则
- 改动后自动运行相关测试套件，直到全部通过才标记完成
- 关键路径执行 pass@3：同一操作跑 3 次，3 次全通过才确认
- 手动验证步骤写成脚本化 checklist，消除人肉操作
- Lint / type-check / security scan 全部通过后才算验证完成
- 验证失败时自动回退到修改前状态，输出失败详情
