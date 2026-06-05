# Skills 开发指南

## Skills 是什么

Skills 是可复用的工作流。每个 skill 是一个 `SKILL.md` 文件，包含名称、描述、使用场景和操作步骤。用户通过特定关键词触发。

## 内置 Skills

| Skill | 触发方式 | 功能 |
|-------|----------|------|
| `design` | `/design` 或"设计模式" | 四阶段需求澄清 |
| `cost` | `@cost` 或"查费用" | API 成本追踪 |
| `compress` | `/compress` 或自动触发 | 上下文压缩 |
| `docx` | Word 文档相关任务 | DOCX 创建与编辑 |
| `pdf` | PDF 相关任务 | PDF 操作 |
| `xlsx` | Excel 相关任务 | XLSX 创建与分析 |

## 创建自定义 Skill

### 1. 创建目录和文件

```bash
mkdir -p skills/my-skill
touch skills/my-skill/SKILL.md
```

### 2. SKILL.md 格式

```markdown
---
name: my-skill
description: "一句话描述。当用户提到 X、Y、Z 时使用。"
---

# Skill 名称

## 使用场景
- 什么时候该用
- 什么时候不该用
- 触发关键词

## 前置条件
- 需要的环境/依赖
- 需要的权限

## 工作流
1. 步骤 1 — 做什么
2. 步骤 2 — 做什么
3. 步骤 3 — 做什么

## 输出
- 产出什么
- 保存到哪里

## 示例
（一个具体的使用例子）
```

### 3. 例子：代码格式化 Skill

```markdown
---
name: format
description: "代码格式化。当用户提到格式化、format、美化代码时使用。"
---

# Format — 代码格式化

## 使用场景
- 代码提交前格式化
- 统一团队代码风格
- 修复缩进和空格问题

## 工作流
1. 识别文件语言（.py → black, .go → gofmt, .js → prettier）
2. 运行对应格式化工具
3. 确认格式化结果
4. 如有 CI 配置，更新配置

## 输出
- 格式化后的文件
- 变更摘要（哪些文件被修改）
```

## Skill vs Command vs Agent

- **Skill**：工作流，多个步骤，可以跨多个文件
- **Command**：快捷指令，通常是单行命令
- **Agent**：智能代理，有独立角色和判断能力

简单来说：Skill 告诉模型"怎么做一件事"，Agent 是一个能"自己决定怎么做"的角色。
