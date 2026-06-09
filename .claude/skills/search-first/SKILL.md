---
name: search-first
description: 改代码前先搜索现有实现，避免重复造轮子
category: coding
loading: on-demand
triggers:
  keywords: ["搜索","查找","在哪","有没有"]
---

# 搜索优先

## 用途
在动手改代码之前，先搜索代码库中是否已有类似实现。

## 核心规则
- 用 grep/glob 先搜一遍，不要凭记忆
- 搜索文件名、函数名、关键代码片段
- 找到相似实现后，评估是否可以复用而非重写
- 如在多个文件中出现，优先提取为共享模块
