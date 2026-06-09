---
name: browser-compat
description: CanIUse 查询、Polyfill 策略、渐进增强方案
category: frontend
loading: on-demand
triggers:
  keywords: ["兼容","浏览器","polyfill","IE"]
---

# 浏览器兼容

## 用途
确保应用在目标浏览器范围内正常运行，通过渐进增强处理兼容性差异。

## 核心规则
- 使用新 API 前在 CanIUse 查询覆盖范围，低于 95% 需要 polyfill 或回退方案
- 通过 `browserslist` 声明目标浏览器（如 `> 0.5%, last 2 versions, not dead`）
- Polyfill 按需加载，使用 `polyfill.io` 或 `@babel/preset-env` 的 `useBuiltIns: "usage"`
- 渐进增强：核心功能全员可用，增强特性仅支持浏览器的用户可见
- CSS 实验性属性加前缀（Autoprefixer 自动处理）和 fallback 值
