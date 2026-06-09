---
name: claude
description: "项目规范查阅。当用户提到架构、规范、格式或需要查阅项目约定时使用。"
disable-model-invocation: true
---

# Claude — 项目规范

> 五层架构定义见 `CLAUDE.md`，工程红线见 `global.md`，全局规则见 Memory。

## 输出格式规范

### 简洁 ≠ 敷衍
"去掉套话"去掉的是：开场寒暄、过度总结、重复确认。**不是**去掉：推理链路、验证结果、错误处理、边界说明。

每次输出前自查：
- [ ] 改了什么文件？路径写全了没有？
- [ ] 为什么这样改？推理链路给出来。
- [ ] 改完有没有验证？验证结果贴出来。

### 代码输出
- Python 使用 snake_case，中文目录
- 配置用 YAML 或 JSON，标注 UTF-8
- 所有路径使用正斜杠 `/`
- 新增/修改文件写出完整路径

### 文档输出
- GitHub-flavored Markdown
- 表格 > 列表（结构清晰时）
- 代码块标注语言

### 对话输出
- 直接但不敷衍：给结论也给推理，给代码也给路径
- 不确定就标注，不编造
- 改动之后必须验证，验证结果必须可见

## 环境快照

```
OS:       Windows 11 Home China
Shell:    PowerShell 5.1 / Git Bash
Python:   3.10.0 (全局安装，无虚拟环境)
AI:       DeepSeek R1 (主力) / Claude Code
项目根:   D:\ai
```
