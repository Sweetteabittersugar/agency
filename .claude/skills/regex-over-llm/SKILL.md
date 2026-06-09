---
name: regex-over-llm
description: 能用正则解决的问题不用 LLM，降低成本和延迟
category: meta
loading: on-demand
triggers:
  keywords: ["正则","regex","成本","简单匹配"]
---

# 正则优先于 LLM

## 用途
培养成本意识：能用确定性规则（正则、glob、字符串匹配）解决的问题，不调用 LLM。

## 核心规则
- 执行搜索/替换/提取操作前，先评估是否能用正则或 glob 完成
- 符合以下条件用正则：模式固定、不涉及语义理解、输入结构已知
- 正则不走 LLM API，直接调用系统工具（grep/ripgrep/sed）
- 编写正则时加注释说明意图，复杂 pattern 拆分为命名片段
- 定期回顾 LLM 调用日志，识别出可被正则替代的 pattern
