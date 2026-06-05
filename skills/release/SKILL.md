---
name: release
description: "发布管理。当用户说发版、发布、release、打tag、changelog时使用。"
---

# Release — 发布管理

## 使用场景
- 准备新版本发布
- 生成 CHANGELOG
- 打 Git tag
- 发布到 npm/PyPI

## 发布流程

### 1. 版本号确定
遵循 SemVer：
- MAJOR: 不兼容的 API 变更
- MINOR: 向后兼容的新功能
- PATCH: 向后兼容的 bug 修复

### 2. CHANGELOG 更新
- 从 git log 提取 feat/fix/refactor 提交
- 按类型分组
- 标注 BREAKING CHANGES

### 3. 发布前检查
- [ ] 所有测试通过
- [ ] lint 无警告
- [ ] CHANGELOG 已更新
- [ ] VERSION 文件已更新
- [ ] 无调试代码残留

### 4. 执行发布
```bash
git tag v$(cat VERSION)
git push --tags
# npm publish / poetry publish / 等
```
