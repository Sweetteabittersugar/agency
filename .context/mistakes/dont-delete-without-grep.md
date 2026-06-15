# Mistake: 删除代码前不 grep 导致 import 断链

**Date**: 2026-06-13
**Source**: lessons.md

## 症状
删了一个语义函数，忘了它内部有 `import threading`。该 import 被其他模块依赖，服务挂掉。

## 根因
删代码前没有检查引用链。

## 预防
```bash
# 删任何函数/类/import 前
grep -rn "function_name\|import_name" --include="*.py" .
```

## 检测
- PreToolUse hook 拦截删除操作
- CI 中 `python -c "import <module>"` 验证所有入口可导入
