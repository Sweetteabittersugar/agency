---
name: style-guide
description: CSS变量、设计Token、暗色主题的样式管理指南
category: frontend
loading: on-demand
triggers:
  keywords: ["样式","CSS","设计系统","主题"]
---

# 样式指南

## 用途
统一样式管理方式，通过 CSS 变量和设计 Token 实现主题化，消除样式碎片化。

## 核心规则
- 定义全局设计 Token：颜色、字体、间距、圆角、阴影，存为 CSS 变量
- 暗色主题通过 CSS 变量覆盖实现，使用 `[data-theme="dark"]` 选择器
- 不在组件中写死颜色值（如 `#333`），必须引用 CSS 变量
- 样式文件组织：`tokens.css` → `global.css` → 组件级 `*.module.css`
- 所有新 UI 元素从现有设计 Token 中选择，不自行定义新色值
