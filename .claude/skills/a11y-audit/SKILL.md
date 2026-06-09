---
name: a11y-audit
description: WCAG 2.2 审计、ARIA 标签规范、键盘导航支持
category: frontend
loading: on-demand
triggers:
  keywords: ["无障碍","a11y","WCAG","ARIA"]
---

# 无障碍审计

## 用途
确保 Web 内容对所有用户（包括使用辅助技术的人）可访问。

## 核心规则
- 所有交互元素可通过键盘操作（Tab/Enter/Escape），tabindex 合理
- 图片必须有有意义的 `alt` 文本，装饰性图片设 `alt=""`
- 表单控件绑定 `<label>`，使用 `aria-describedby` 关联错误提示
- 色彩对比度不低于 4.5:1（正文）/ 3:1（大文本）
- 页面有跳转到主内容区的 skip link
