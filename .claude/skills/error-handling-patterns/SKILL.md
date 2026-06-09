---
name: error-handling-patterns
description: 每个异常必须显式处理，不静默吞掉异常
category: coding
loading: on-demand
triggers:
  keywords: ["错误处理","异常","try","catch"]
---

# 错误处理模式

## 用途
规范异常处理流程，确保每一处错误都有明确的处理逻辑，杜绝静默吞异常导致难以排查的 bug。

## 核心规则
- 每个 try 块必须有对应的 catch/except，且必须记录日志或向上抛出
- 空 catch 块（`except: pass` / `catch {}`）绝对禁止
- 在系统边界处（API入口、数据库操作、文件IO）统一捕获并转换异常
- 错误消息包含足够上下文：操作名、关键参数、原始错误类型
- 面向用户的错误消息通用友好，详细堆栈仅记录到服务端日志
