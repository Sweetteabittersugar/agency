---
name: init
description: "项目初始化。当用户说新建项目、初始化、创建项目、搭架子时使用。"
---

# Init — 项目初始化

## 使用场景
- 从零开始创建新项目
- 为新项目配置开发环境
- 为已有项目补全开发规范

## 初始化流程

### 1. 收集需求
- 项目类型（Web/CLI/库/脚本）
- 技术栈（Python/Go/TS 等）
- 是否需要 agency-kit 集成

### 2. 创建骨架
- 目录结构
- 包管理文件（pyproject.toml / go.mod / package.json）
- .gitignore
- README.md 模板

### 3. 配置规范
- 从 rules/ 中选择适用的规范
- 配置 lint 工具（ruff / golangci-lint / eslint）
- 配置 CI（从 .github/workflows/ 模板复制）

### 4. 验证
- 初始化 git 仓库
- 运行 lint 检查
- 确认目录结构完整
