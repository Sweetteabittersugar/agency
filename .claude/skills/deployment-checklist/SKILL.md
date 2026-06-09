---
name: deployment-checklist
description: 发布前检查清单、回滚预案、监控就绪确认
category: devops
loading: on-demand
triggers:
  keywords: ["部署","发布","上线","检查清单"]
---

# 部署检查清单

## 用途
发布前的必检清单，确保每个环节就绪，避免上线事故。

## 核心规则
- 所有测试通过（单元+集成+E2E），覆盖率不低于基线
- 数据库迁移已在 staging 环境完整跑通，有回滚脚本
- 依赖审计无 HIGH/CRITICAL 漏洞
- 监控和告警规则已更新，关键指标皆有面板
- 回滚方案已就绪：代码回滚命令 + 数据回滚脚本 + 流量切换方案
