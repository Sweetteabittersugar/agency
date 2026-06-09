---
name: code-standards
description: 遵循项目现有代码风格，不加个人偏好
category: coding
loading: on-demand
triggers:
  keywords: ["代码规范","风格","格式","lint"]
---

# 代码规范

## 用途
确保所有代码改动遵循项目现有风格约定，不引入个人偏好，维持代码库整体一致性。

## 核心规则
- 新代码的缩进、命名、注释风格必须与相邻已有代码一致
- 查看项目已有的 `.editorconfig`、`prettier.config`、`pyproject.toml` 等配置
- 不擅自改变既有文件的格式化风格
- 变量/函数命名遵循项目惯用模式（snake_case 还是 camelCase）
- 提交前运行项目配置的 lint 工具（如 ruff、eslint）
