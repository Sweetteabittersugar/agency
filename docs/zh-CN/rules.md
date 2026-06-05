# Rules 自定义指南

## Rules 是什么

Rules 是始终生效的工程规范。Claude Code 在每次对话中自动加载 `rules/` 下的所有 `.md` 文件。agency-kit 预设了 29 个规范文件，覆盖：

- **通用规范**（`rules/common/`）：代码风格、安全、测试、Git、Agent 编排等
- **语言规范**（`rules/python/`、`rules/golang/`、`rules/typescript/`）：各语言特定的编码标准

## 添加自定义 Rule

### 1. 创建文件

```bash
# 通用规范放在 common/
touch rules/common/my-rule.md

# 语言规范放在对应目录
touch rules/python/my-python-rule.md
```

### 2. Rule 格式

```markdown
# Rule 名称

## 适用范围
- 哪些项目/文件/语言

## 规则内容
1. 具体规则 1 — 为什么
2. 具体规则 2 — 为什么

## 示例
# 好的做法
...

# 避免的做法
...
```

### 3. 更新索引

在 `RULES.md` 中添加新规则的条目。

## Rule 优先级

1. **security.md** — 最高优先级，任何时候不能违反
2. **maestro.md** — Agent 调度时必须遵守
3. **语言规范** — 写对应语言时自动应用
4. **coding-style.md** — 写代码时遵守
5. **git-workflow.md** — 提交时遵守

## 实际例子

### 添加 "数据库命名规范"

```markdown
# 数据库命名规范

## 适用范围
所有涉及数据库操作的项目

## 规则
1. 表名用复数：`users` 而非 `user`
2. 主键统一用 `id`
3. 外键格式：`{table}_id`，如 `user_id`
4. 时间字段：`created_at`、`updated_at`（UTC）

## 示例
-- 好的
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 避免
CREATE TABLE user (
    userId INT PRIMARY KEY,
    email TEXT
);
```

## 注意事项

- Rule 文件不要过大（<300 行），一个文件聚焦一个主题
- 避免和现有 common rules 重复
- 规则要可执行——给出"做什么"和"怎么做"
