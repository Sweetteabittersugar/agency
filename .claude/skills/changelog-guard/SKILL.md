---
name: changelog-guard
description: 变更日志管理 —— Conventional Commits、SemVer、CHANGELOG 格式与自动生成
category: documentation
loading: on-demand
triggers:
  keywords: ["changelog", "变更记录", "版本记录", "发布说明", "CHANGELOG"]
---

# 这是什么

变更日志是向用户和开发者传达每个版本中发生了什么变化的文档。好的 CHANGELOG 让人快速了解新功能、Bug 修复和破坏性变更。

# 何时使用

- 每次发布新版本时
- 用户问「这个版本改了什么」时
- 判断是否升级依赖的参考依据
- 团队内部追溯某次改动何时发布
- CI/CD 流水线中自动生成发布说明

# 核心规则

1. **为人类写，不为机器写**：虽然格式可以标准化，但内容必须人能读懂。一个非技术用户应该能理解这个版本的变化。
2. **每个版本独立一节**：按时间倒序排列，最新版本在最上面。版本号明确，发布日期精确到日。
3. **分类组织**：按改动类型分组，用户能快速定位关注的内容。
4. **记录影响用户的变化**：内部重构、代码风格调整、CI 配置变更等不影响用户行为的改动不需要出现在 CHANGELOG 中。
5. **破坏性变更醒目标记**：不向后兼容的变化必须用醒目的标记，让用户在升级前知晓。

# 工作流程

1. **提交规范化**
   - 所有提交遵循 Conventional Commits 格式
   - 格式：`<type>(<scope>): <description>`
   - Type：feat（新功能）、fix（Bug 修复）、docs（文档）、refactor（重构）、test（测试）、chore（杂务）、perf（性能优化）
   - 破坏性变更在 footer 中加 `BREAKING CHANGE:` 前缀或在 type 后加 `!`

2. **CHANGELOG 格式**
   - 遵循 Keep a Changelog 规范
   - 按类别分组：Added、Changed、Deprecated、Removed、Fixed、Security
   - 每个条目一句话描述变化和影响

3. **版本号管理**
   - 遵循 SemVer（语义化版本）：`MAJOR.MINOR.PATCH`
   - MAJOR：不兼容的 API 变更
   - MINOR：向后兼容的新功能
   - PATCH：向后兼容的 Bug 修复
   - 预发布版本：`1.0.0-alpha.1`、`1.0.0-beta.2`
   - 构建元数据：`1.0.0+20240609`

4. **自动生成**
   - CI/CD 中集成 changelog 生成工具
   - 从 git 历史中提取 Conventional Commits 消息
   - 手动补充和润色自动生成的内容
   - CHANGELOG 作为发布流程的一部分自动更新

5. **发布前检查**
   - 版本号是否正确递增
   - 所有条目是否分类正确
   - 破坏性变更是否有迁移说明
   - 日期是否填写
   - 与上一个版本相比是否有遗漏

# CHANGELOG 条目模板

```markdown
## [1.2.0] - 2026-06-09

### Added
- 新增批处理接口，支持一次请求处理多个资源

### Changed
- 默认分页大小从 20 调整为 50

### Deprecated
- `/v1/query` 端点已弃用，将在 2.0.0 移除。请迁移到 `/v2/search`

### Removed
- 移除对 Python 3.7 的支持

### Fixed
- 修复并发写入时偶发的数据丢失问题

### Security
- 修复认证令牌的时序攻击漏洞
```

# Semantic Versioning 详解

## 版本号递增规则

| 变更类型 | SemVer 字段 | 示例 |
|----------|-------------|------|
| Bug 修复（向后兼容） | PATCH | 1.2.3 → 1.2.4 |
| 新功能（向后兼容） | MINOR | 1.2.3 → 1.3.0 |
| 破坏性变更 | MAJOR | 1.2.3 → 2.0.0 |

## 破坏性变更示例

- 删除公开 API 或方法
- 修改函数签名（增加必需参数、修改返回类型）
- 修改配置文件的默认值且影响行为
- 不再支持某个平台或语言版本
- 修改数据结构格式（用户需要迁移数据）

## 非破坏性变更示例

- 新增可选参数
- 新增公开 API
- 放宽输入校验
- 性能优化（不改变行为）
- 新增错误码

# 发布说明写作原则

- 用用户视角描述变化，而非开发者视角
- 说明「新功能能做什么」而非「我们做了什么」
- Bug 修复说明「修复了什么问题」而非「改了哪行代码」
- 如果一个变化需要用户操作（迁移、配置更新），写清楚步骤

# 参考标准

- Keep a Changelog v1.1.0 —— CHANGELOG 格式规范
- Semantic Versioning 2.0.0 —— 版本号规范
- Conventional Commits 1.0.0 —— 提交消息规范
- GNU 变更日志风格 —— 传统 CHANGELOG 格式
- OpenAPI 的弃用策略 —— API 级别的变更通知
