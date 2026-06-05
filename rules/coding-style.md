# 代码风格规范

> 保持代码一致、可读、可维护。以下规则适用于所有语言，具体语言工具链见各语言子规则。

---

## 不可变性优先

始终创建新对象，**绝不修改已有对象**。不可变数据避免了隐蔽的副作用，简化调试，支持安全的并发。

```python
# 错误：直接修改原对象
def update_user(user, name):
    user.name = name  # 副作用！
    return user

# 正确：返回新对象
def update_user(user, name):
    return {**user, "name": name}
```

```javascript
// 错误：修改原对象
function updateUser(user, name) {
    user.name = name;  // 副作用！
    return user;
}

// 正确：返回新对象
function updateUser(user, name) {
    return { ...user, name };
}
```

---

## 文件组织

- **小文件优先**：200-400 行为理想范围，最多 800 行
- **高内聚低耦合**：每个文件只做一件事
- **按功能/领域组织**，而非按文件类型
- 超过 800 行时考虑拆分

---

## 函数设计

- 函数保持简短：**不超过 50 行**
- 单一职责：一个函数只做一件事
- 嵌套层级不超过 4 层
- 参数不超过 5 个，超过时考虑封装为对象

---

## 命名规范

| 语言 | 变量/函数 | 类/组件 | 常量 | 文件名 |
|------|----------|---------|------|--------|
| Python | `snake_case` | `PascalCase` | `UPPER_SNAKE` | `snake_case.py` |
| JavaScript/TypeScript | `camelCase` | `PascalCase` | `UPPER_SNAKE` | `kebab-case.ts` |
| Go (exported) | `PascalCase` | `PascalCase` | `PascalCase` | `snake_case.go` |
| Go (unexported) | `camelCase` | `camelCase` | — | — |

命名原则：
- 见名知意，避免单字母（循环变量除外）
- 布尔值用 `is_`/`has_`/`can_` 前缀
- 函数用动词开头（`get_`, `create_`, `delete_`, `handle_`）

---

## 错误处理

- **显式处理每一个错误**，绝不静默吞掉异常
- 在系统边界捕获异常并转换为有意义的消息
- 记录足够的上下文信息用于排查

```python
# 错误：吞掉异常
try:
    result = risky_operation()
except Exception:
    pass

# 正确：显式处理
try:
    result = risky_operation()
except ValueError as e:
    logger.error(f"参数无效: {e}")
    raise
except ConnectionError as e:
    logger.error(f"连接失败: {e}")
    return fallback_value
```

---

## 代码质量检查清单

提交前确认：

- [ ] 代码可读性强，命名清晰
- [ ] 函数短小（<50 行），职责单一
- [ ] 文件聚焦（<800 行）
- [ ] 嵌套不超过 4 层
- [ ] 无不必要的硬编码（使用常量或配置）
- [ ] 遵循不可变模式，无原地修改
- [ ] 错误都已显式处理，无静默吞异常
- [ ] 代码已格式化（Python: black/isort；JS: prettier；Go: gofmt）
