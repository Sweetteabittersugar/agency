---
name: component-patterns
description: 组合优于继承、受控/非受控、状态提升的组件模式
category: frontend
loading: on-demand
triggers:
  keywords: ["组件","component","React","Vue","组合"]
---

# 组件模式

## 用途
规范 UI 组件的设计和组织方式，确保可复用、可测试、易维护。

## 核心规则
- 组合优于继承：通过 `children` / `slots` 组合而非层级继承
- 受控组件：状态由父组件管理；非受控：内部状态自管理。同一组件库内保持一致
- 状态提升：多个组件共享的状态上移最近的公共祖先
- 组件单一职责：展示组件不处理数据获取，逻辑组件不负责渲染样式
- 每个组件文件夹含组件源码+测试+样式+类型定义
