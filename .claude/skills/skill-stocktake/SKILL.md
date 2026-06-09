---
name: skill-stocktake
description: 定期审计 Skill 清单，标记冗余和过期项，建议合并
category: meta
loading: on-demand
triggers:
  keywords: ["skill盘点","审计skill","冗余","合并"]
---

# Skill 盘点

## 用途
定期审计所有已安装的 Skill，识别冗余、过期、低使用率的 Skill，提出清理和合并建议。

## 核心规则
- 每季度全量盘点一次，统计各 Skill 的触发次数和成功率
- 标记超过 30 天未触发的 Skill 为"休眠"，评估是否下架
- 功能重叠超过 70% 的两个 Skill 建议合并
- 每次盘点生成报告：活跃列表、休眠列表、建议合并列表、待删除列表
- 删除 Skill 前确认无其他 Skill 或规则引用它
