# NOW — agency

> 2026-07-10 | 项目结构基线

## 当前状态

- 独立 Git 仓库，定位为 Python 工具包与 Web UI 组合项目。
- 本次只补项目状态入口，不改写产品进度或现有未提交内容。
- `maestro/`、`memory/`、`tasks/` 和本地配置存在运行时引用，暂不迁移。

## 结构重点

- 源码、测试、文档和脚本入口已存在。
- `.pytest_cache/`、`.ruff_cache/`、`*.egg-info` 属于可重建产物。
- 运行目录迁入 `.runtime/` 前必须先完成引用审计和回滚设计。

## 验证

```powershell
git status --short
python -m pytest
```
