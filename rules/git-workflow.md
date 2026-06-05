# Git 工作流规范

> 保持提交历史清晰、可追溯、可回滚。以下规则适用于所有项目。

---

## Commit 格式

遵循 Conventional Commits 规范：

```
<type>: <description>

<optional body>
```

### Type 类型

| Type | 用途 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 添加用户登录接口` |
| `fix` | Bug 修复 | `fix: 修复分页计数偏差` |
| `refactor` | 重构（不改变行为） | `refactor: 提取公共校验逻辑` |
| `docs` | 文档更新 | `docs: 补充 API 错误码说明` |
| `test` | 测试相关 | `test: 增加订单模块单元测试` |
| `chore` | 杂务（依赖、构建、配置） | `chore: 升级 Django 到 5.0` |
| `perf` | 性能优化 | `perf: 优化列表页查询` |
| `ci` | CI/CD 变更 | `ci: 添加代码扫描步骤` |

### 格式要求

- Subject 用中文或英文，项目内保持一致
- Subject 不超过 72 字符
- Body 说明**为什么**改动、设计决策和权衡
- 与 issue 关联时在 body 中引用 `#issue编号`

---

## 分支策略

- `master` / `main`：生产就绪代码，禁止直接提交
- `dev` / `develop`：开发集成分支（可选）
- 功能分支：`feat/<描述>`，从 `master` 分出
- 修复分支：`fix/<描述>`，从 `master` 分出
- 分支名用小写英文，单词用 `-` 连接

---

## PR 工作流

1. 从 `master` 创建功能/修复分支
2. 在分支上开发，保持 commit 原子化
3. **提交前**：本地跑完测试和 lint
4. Push 分支到远端：`git push -u origin feat/xxx`
5. 创建 PR，填写：
   - 改动摘要
   - 测试说明
   - 关联 issue
6. 至少一人 Review 通过后才能合并
7. 合并后删除远端分支

---

## 提交前检查清单

- [ ] Commit message 符合 `<type>: <description>` 格式
- [ ] 无调试代码（`console.log`、`print`、注释掉的代码）
- [ ] 无敏感信息（密钥、密码、内部路径）
- [ ] 相关测试已通过
- [ ] 无意外提交的文件（检查 `git status`）
- [ ] 不在 `master`/`main` 分支上直接提交

---

## 常用操作

```bash
# 撤销最近一次 commit（保留改动）
git reset --soft HEAD~1

# 修改最近一次 commit message
git commit --amend -m "new message"

# 将多个 commit 合并为一个
git rebase -i HEAD~3

# 暂存当前改动
git stash push -m "WIP: 用户模块重构中"
```
