---
name: self-healing
description: 任务失败时自动重试 + 换策略 — 分析失败原因，选择替代方案重新执行
category: resilience
loading: on-demand
triggers:
  keywords: ["自愈", "重试", "self-heal", "换策略", "fallback", "自动修复", "恢复"]
---

# 自愈引擎

## 用途
当 Agent 任务执行失败时，自动分析失败原因，选择合适的替代策略重试，最大限度减少人工干预。

## 失败分类与策略映射

### Error 1: 语法/编译错误
- **识别**: SyntaxError, CompileError, TypeScript error TS2xxx
- **策略**: 
  1. 检查最近修改文件的语法 (`ast.parse` / `tsc --noEmit`)
  2. 回退最后一次编辑，重新生成
  3. 用更简单的实现替代复杂表达式

### Error 2: 导入/依赖错误
- **识别**: ModuleNotFoundError, ImportError, Cannot find module
- **策略**:
  1. 检查文件路径是否正确（大小写、扩展名）
  2. 运行 `pip install` / `npm install`
  3. 检查 `sys.path` / `node_modules`

### Error 3: 运行时异常
- **识别**: 非语法/导入类异常 (TypeError, ValueError, HTTPError 等)
- **策略**:
  1. 检查输入数据类型/范围
  2. 添加防御性检查 (null/undefined)
  3. 降级到更健壮的实现

### Error 4: 超时
- **识别**: TimeoutError, 任务执行超过预期时间 2x
- **策略**:
  1. 减少处理范围（仅处理核心部分）
  2. 切换到更快的模型 (sonnet → haiku)
  3. 拆分为更小的子任务

### Error 5: API/网络错误
- **识别**: ConnectionError, HTTP 5xx, RateLimitError
- **策略**:
  1. 等待 2s → 5s → 15s 指数退避重试
  2. 切换 API provider (deepseek → anthropic → openai)
  3. 使用缓存结果（如有）

## 重试策略

### 同策略重试 (Same Strategy)
- 适用: 网络/超时类瞬时错误
- 次数: 最多 3 次
- 间隔: 指数退避 (2s, 5s, 15s)

### 换策略重试 (Strategy Switch)
- 适用: 逻辑/语法类错误
- 次数: 最多 2 次策略切换
- 策略池: 简化实现 → 拆分任务 → 换 Agent → 换模型

### 升级 (Escalation)
- 触发: 所有重试均失败
- 行为: 报告给 human-in-the-loop，附带所有失败记录

## 核心规则
- 每次重试前记录失败原因和选择策略（写入 `maestro/agency.log`）
- 不无限重试 — 总计不超过 5 次尝试（3 次同策略 + 2 次换策略）
- 修改文件前创建备份 (`.bak` 后缀)
- 成本敏感：换策略重试时优先选择更便宜的替代方案
- 与 Profile 联动：minimal 不启用，standard 启用 3 次同策略，full 启用完整自愈

## 输出格式

```json
{
  "original_error": "ModuleNotFoundError: No module named 'requests'",
  "error_type": "import_error",
  "attempts": [
    {"attempt": 1, "strategy": "same", "action": "pip install requests", "result": "success"},
  ],
  "healed": true,
  "final_status": "resolved"
}
```
