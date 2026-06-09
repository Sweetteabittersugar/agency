---
name: pipeline-gate
description: 五阶段管线阶段进入/退出条件检查，确保每个阶段的输出满足下一阶段的输入要求
category: orchestration
loading: on-demand
triggers:
  keywords: ["阶段检查", "gate", "管线", "pipeline", "进入条件", "退出条件", "阶段切换"]
---

# 阶段 Gate 检查

## 用途
在五阶段管线 (research → plan → implement → review → verify) 中，每个阶段进入/退出时执行条件检查，确保当前阶段输出满足下一阶段的输入要求。

## 五阶段 Gate 定义

### Gate 1: research → plan
- **进入条件**：任务描述非空，Agent 已完成路由分配
- **退出条件**：产出至少 1 份调研摘要（含文件清单、依赖关系、关键接口）
- **检查项**：
  - [ ] 相关文件路径已列出（绝对路径）
  - [ ] 依赖关系已梳理（上游/下游）
  - [ ] 关键接口/函数签名已标注
  - [ ] 已知风险点已记录

### Gate 2: plan → implement
- **进入条件**：research gate 已通过
- **退出条件**：产出可执行计划（含分阶段任务、Agent 分配、验收标准）
- **检查项**：
  - [ ] 任务已拆解为独立子任务
  - [ ] 每个子任务有明确的 Agent 分配
  - [ ] 并行/串行依赖明确标注
  - [ ] 验收标准可量化

### Gate 3: implement → review
- **进入条件**：plan gate 已通过，所有子任务执行完成
- **退出条件**：所有代码变更已提交，无语法/类型错误
- **检查项**：
  - [ ] 所有文件通过语法检查（Python: ast.parse / JS: 无 SyntaxError）
  - [ ] 无遗留的 TODO/FIXME 标记（或已转 issue）
  - [ ] 文件行数在规范范围内（<800 行）
  - [ ] Import/引用路径正确

### Gate 4: review → verify
- **进入条件**：implement gate 已通过
- **退出条件**：审查通过（无 CRITICAL / HIGH 问题未解决）
- **检查项**：
  - [ ] 安全审查已通过（无密钥泄露、注入风险）
  - [ ] 代码风格合规（命名、格式、不可变性）
  - [ ] 测试覆盖率 ≥ 80%
  - [ ] 性能回归检查无异常

### Gate 5: verify → done
- **进入条件**：review gate 已通过
- **退出条件**：所有验收标准通过
- **检查项**：
  - [ ] E2E 测试通过
  - [ ] CHANGELOG 已更新
  - [ ] 相关文档已同步
  - [ ] 构建/部署检查通过

## 核心规则
- 任何 gate 不通过 → 退回上一阶段，附带具体失败原因
- 每个 gate 最多重试 3 次，超过则上报 human-in-the-loop
- Gate 状态记录到 `maestro/tasks/` 下的任务元数据中
- Profile 级别影响 gate 严格程度：minimal 跳过 gate 4/5，standard 执行 gate 1-4，full 执行全部
