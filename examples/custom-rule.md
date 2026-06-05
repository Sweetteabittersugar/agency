# 自定义 Rule 示例

展示如何为 agency-kit 创建和注册自定义工程规范。

## 1. 创建 Rule 文件

在 `rules/` 下新建文件。如果是语言相关规范，在对应的语言子目录下创建：

```
rules/
├── common/          # 语言无关的通用规范
│   ├── coding-style.md
│   ├── testing.md
│   └── ...
├── python/          # Python 特定规范
│   ├── coding-style.md
│   └── ...
├── typescript/      # TypeScript 特定规范
├── golang/          # Go 特定规范
└── my-rule.md       # 自定义规则（语言无关）
```

## 2. Rule 格式规范

```markdown
# 规则名称 — 一句话说明

## 适用场景
什么情况下需要检查这个规则。

## 规则详情

### 规则 1：具体规则描述
必须做什么 / 禁止做什么。

```
// 反面示例（WRONG）
错误代码示例

// 正面示例（CORRECT）
正确代码示例
```

### 规则 2：具体规则描述
...

## 检查清单
- [ ] 检查项 1
- [ ] 检查项 2
- [ ] 检查项 3

## 例外情况
- 什么情况下可以不遵守
- 为什么不遵守（需要注释说明）
```

如果是语言扩展规范，文件开头添加引用声明：

```markdown
> This file extends [common/xxx.md](../common/xxx.md) with [语言] specific content.
```

## 3. 生效验证

规则文件创建后，Claude Code 在启动时自动加载 `rules/` 目录下的所有 `.md` 文件。

验证方式：

1. 启动新会话，在对话中问：`请列出当前项目加载的规范文件`
2. 确认你的新规则文件出现在列表中
3. 用一条会触发规则的请求测试，确认 Agent 按规则行事

## 完整示例：API 设计规范

### rules/api-design.md
```markdown
# API Design — RESTful API 设计规范

## 适用场景
任何涉及 HTTP API 接口设计、修改、审查的场景。

## 规则详情

### 规则 1：统一响应格式
所有 API 响应必须使用统一信封格式。

```
// WRONG - 直接返回数据
{
  "id": 1,
  "name": "Alice"
}

// CORRECT - 统一信封
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Alice"
  },
  "error": null,
  "meta": null
}
```

### 规则 2：错误响应格式
错误响应必须包含可操作的错误信息。

```
// WRONG - 仅返回状态码
HTTP 500 Internal Server Error

// CORRECT - 包含错误详情
{
  "success": false,
  "data": null,
  "error": {
    "code": "DB_CONNECTION_FAILED",
    "message": "无法连接到数据库，请稍后重试",
    "details": "connection refused at 10.0.0.1:5432"
  }
}
```

### 规则 3：版本化
所有 API 路径必须包含版本号。

```
// WRONG
GET /api/users

// CORRECT
GET /api/v1/users
```

### 规则 4：分页
列表接口必须支持分页。

```
// CORRECT
GET /api/v1/users?page=1&limit=20

// 响应包含 meta
{
  "success": true,
  "data": [...],
  "error": null,
  "meta": {
    "total": 150,
    "page": 1,
    "limit": 20,
    "total_pages": 8
  }
}
```

## 检查清单
- [ ] 所有响应使用统一信封格式
- [ ] 错误响应包含 error 字段（code + message）
- [ ] API 路径包含版本号
- [ ] 列表接口支持分页参数
- [ ] 不使用动词作为 URL 路径（使用 HTTP 方法）
- [ ] 资源名使用复数形式（/users 而非 /user）

## 例外情况
- 健康检查端点（/health、/ping）可以不使用信封格式
- WebSocket 端点不需要版本号
- 内部服务间调用可以不使用版本号（在注释中说明）
```

### 效果
创建后，当 Agent 设计或实现 API 时，会自动遵守以上规则：
- 响应自动包裹在 `{ success, data, error, meta }` 信封中
- 错误响应包含 `code` 和 `message`
- URL 自动带版本号
- 新增列表接口自动支持分页
