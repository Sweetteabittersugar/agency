---
name: debug
description: "系统化调试。当用户说调试、debug、修bug、排查、报错时使用。"
---

# Debug — 系统化调试

## 使用场景
- 代码报错，不知道原因
- 功能行为不符合预期
- 性能问题排查
- 测试失败分析

## 调试流程

### 1. 复现
- 获取确切的错误信息和堆栈
- 确认能稳定复现
- 最小化复现步骤

### 2. 定位
- 二分法缩小范围（注释代码、git bisect）
- 添加诊断日志（不是 print，是 structured logging）
- 检查假设——你认为的"不可能"往往就是问题

### 3. 修复
- 最小修改原则
- 修根因，不修症状
- 修完验证：原 bug 不再出现 + 现有测试全绿

### 4. 防止复发
- 加回归测试
- 加边界检查
- 记录为什么这个修复是正确的

## 常用命令
| 场景 | 命令 |
|------|------|
| Python 堆栈 | `python -m traceback` |
| Go race | `go test -race` |
| Node 内存 | `node --inspect` |
| Git bisect | `git bisect start; git bisect bad; git bisect good <commit>` |
