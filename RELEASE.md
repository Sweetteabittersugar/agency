# 发布流程

## 版本号规则

遵循 [SemVer](https://semver.org/)：`MAJOR.MINOR.PATCH`

- **MAJOR**：不兼容的 API 变更
- **MINOR**：向后兼容的新功能
- **PATCH**：向后兼容的 bug 修复

## 发布前检查清单

- [ ] 所有测试通过：`pytest tests/ -v`
- [ ] Python 编译无错：`python -m compileall maestro/`
- [ ] JS 语法正确：`node --check webui/js/*.js`
- [ ] CHANGELOG.md 已更新
- [ ] VERSION 文件已更新

## 发布步骤

1. 更新版本号
   ```bash
   echo "0.2.0" > VERSION
   ```

2. 更新 CHANGELOG.md

3. 提交版本更新
   ```bash
   git add VERSION CHANGELOG.md
   git commit -m "chore: bump version to 0.2.0"
   ```

4. 打标签
   ```bash
   git tag -a v0.2.0 -m "v0.2.0: <简要描述>"
   ```

5. 推送
   ```bash
   git push origin main --tags
   ```

6. CI 自动执行：
   - 运行测试
   - 构建包
   - 发布到 PyPI
   - 创建 GitHub Release

## 回滚

如果发布有问题：
```bash
# 回滚 PyPI 无法撤回，只能发布新版本
# 回滚 Git tag
git tag -d v0.2.0
git push --delete origin v0.2.0
```
