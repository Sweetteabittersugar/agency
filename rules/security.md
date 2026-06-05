# 安全规范

> 所有代码提交前必须通过以下安全检查。安全问题为最高优先级，发现后立即修复。

---

## 密钥管理

**绝对禁止**在源代码中硬编码任何密钥、密码、Token 或证书。

```python
# 错误：硬编码密钥
api_key = "sk-xxxxxxxxxxxxxxxxxxxx"

# 正确：从环境变量读取
import os
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY 未配置")
```

```javascript
// 错误：硬编码密钥
const apiKey = "sk-xxxxxxxxxxxxxxxxxxxx";

// 正确：从环境变量读取
const apiKey = process.env.OPENAI_API_KEY;
if (!apiKey) {
    throw new Error("OPENAI_API_KEY 未配置");
}
```

- 使用 `.env` 文件管理本地密钥，确保 `.env` 已加入 `.gitignore`
- CI/CD 中通过平台提供的 Secret 管理功能注入密钥
- 发现密钥泄露后，立即轮换并撤销旧密钥

---

## 输入校验

**所有用户输入必须在系统边界处验证**，不信任任何外部数据。

- 校验类型、长度、格式、范围
- 使用白名单而非黑名单
- 使用成熟的校验库（Python: Pydantic；JS: Zod）

```python
from pydantic import BaseModel, EmailStr, Field

class CreateUserRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    age: int = Field(..., ge=0, le=150)
```

---

## SQL 注入防护

**始终使用参数化查询**，绝不拼接 SQL 字符串。

```python
# 错误：字符串拼接
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# 正确：参数化查询
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

- ORM（SQLAlchemy、Django ORM、Prisma）默认提供参数化保护
- 动态表名/列名无法参数化时，使用白名单映射

---

## XSS 防护

- 输出到 HTML 前对所有用户内容做转义处理
- 使用模板引擎的自动转义功能（Jinja2、React JSX）
- 设置 Content-Security-Policy 响应头

```javascript
// 错误：直接插入用户内容
element.innerHTML = userInput;

// 正确：使用 textContent 或转义
element.textContent = userInput;
```

---

## 错误处理

- **禁止**在错误消息中暴露堆栈跟踪、数据库结构、内部路径等敏感信息
- 面向用户的错误消息应通用且友好
- 详细错误信息仅记录到服务端日志

```python
# 错误：暴露内部细节
return {"error": str(e), "traceback": traceback.format_exc()}

# 正确：用户友好消息
logger.error(f"数据库查询失败: {e}", exc_info=True)
return {"error": "操作失败，请稍后重试"}
```

---

## 提交前安全检查清单

每次 `git commit` 前逐项确认：

- [ ] 无硬编码密钥、密码、Token
- [ ] 所有用户输入有校验逻辑
- [ ] 数据库查询使用参数化（无字符串拼接 SQL）
- [ ] 用户内容输出前已转义（XSS 防护）
- [ ] 错误消息不泄露内部信息
- [ ] `.env` 和含密钥的文件已在 `.gitignore` 中
- [ ] 第三方依赖无已知高危漏洞（`pip audit` / `npm audit`）
- [ ] 敏感操作有权限校验（认证 + 授权）
