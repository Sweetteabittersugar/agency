---
name: memory-leak-detection
description: heap 分析、引用追踪、常见泄漏模式识别
category: performance
loading: on-demand
triggers:
  keywords: ["内存泄漏","heap","OOM","内存"]
---

# 内存泄漏检测

## 用途
识别和修复内存泄漏，防止应用因 OOM 崩溃。

## 核心规则
- 使用 heap snapshot 对比定位增长对象，不凭直觉猜测
- 常见泄漏源：未清理的定时器、事件监听器、闭包引用、全局缓存膨胀
- 事件监听器在组件销毁时强制解绑（`removeEventListener` / `off`）
- 长时间运行的缓存设上限（LRU），防止无限膨胀
- Node.js 关注 EventEmitter 的 max listeners 警告
