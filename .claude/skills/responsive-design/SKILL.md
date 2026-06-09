---
name: responsive-design
description: 断点策略、弹性布局、图片自适应适配
category: frontend
loading: on-demand
triggers:
  keywords: ["响应式","适配","移动端","media query"]
---

# 响应式设计

## 用途
确保 UI 在各种屏幕尺寸下可用、可读、可交互。

## 核心规则
- 移动优先设计：基础样式为小屏，通过 media query 向上增强
- 断点统一使用 4 档：mobile（<768）、tablet（768-1024）、desktop（1024-1440）、wide（>1440）
- 图片使用 `srcset` + 多倍分辨率，配合 `loading="lazy"`
- 字体和间距使用相对单位（rem/em/vw），不写死 px
- 点击区域不小于 44x44px（移动端触控友好）
