---
name: changelog-guard
description: 代码变更时自动检测并提醒更新 CHANGELOG.md，确保版本记录不遗漏
category: maintenance
loading: on-demand
triggers:
  keywords: ["changelog", "变更日志", "版本记录", "更新日志", "release note"]
---

# CHANGELOG 守卫

## 用途
在代码发生版本级变更时，自动检测是否需要更新 CHANGELOG.md，提醒（或在 full profile 下自动）更新。

## 触发条件
以下类型的变更需要同步更新 CHANGELOG：

| 变更类型 | 示例 | 必须 CHANGELOG |
|---------|------|:---:|
| 新功能 | `feat:` commit | 是 |
| 破坏性变更 | 改 API 签名、删公共接口 | 是 |
| 重大重构 | 架构调整、模块拆分 | 是 |
| 配置变更 | CI/CD 修改、依赖升级 | 建议 |
| Bug 修复 | `fix:` commit | 建议（用户可见的 bug 必须） |
| 性能优化 | 30%+ 性能提升 | 建议 |
| 文档更新 | `docs:` commit | 否 |
| 小修小补 | 格式化、注释、typo | 否 |

## CHANGELOG.md 格式

遵循 [Keep a Changelog](https://keepachangelog.com/) 规范：

```markdown
## [version] - YYYY-MM-DD
### Added
- 新增功能说明
### Changed
- 变更说明（原有行为的修改）
### Deprecated
- 即将移除的功能
### Removed
- 已移除的功能
### Fixed
- Bug 修复说明
### Security
- 安全相关修复
```

## 检查逻辑

### 1. 变更级别判定
- 扫描 `git diff` 中的文件变更
- 分析 commit message 类型
- 判定是否需要 CHANGELOG 条目

### 2. 已有条目检查
- 读取 CHANGELOG.md 当前版本区块
- 检查是否已包含本次变更的描述
- 验证条目格式合规

### 3. 版本号验证
- 读取 `VERSION` 文件或 `pyproject.toml` 版本
- 检查 CHANGELOG 最新版本号是否匹配
- 不匹配 → 警告

## 核心规则
- 检测到需要 CHANGELOG 但未更新 → full profile 自动生成条目，standard 提醒，minimal 忽略
- 自动生成的条目使用以下格式：`- <commit description> (@<agent-name>)`
- CHANGELOG.md 不存在时 → 自动创建模板
- 合并冲突时 → 标记冲突区域，请求人工解决
- 每次版本发布 (`release-manager` 触发) 时强制校验

## 输出格式

```json
{
  "needs_update": true,
  "current_version": "0.1.0",
  "changelog_version": "0.1.0",
  "missing_entries": [
    {"type": "Added", "description": "Profile 三级制度", "commit": "feat: profiles"},
    {"type": "Changed", "description": "Agent-Skill 绑定系统", "commit": "feat: agent-skill"}
  ],
  "suggested_block": "## [0.2.0] - 2026-06-09\n### Added\n- Profile 三级制度\n- 8 个差异化 Skill\n...",
  "auto_updated": false
}
```
