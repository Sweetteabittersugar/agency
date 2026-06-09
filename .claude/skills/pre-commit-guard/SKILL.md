---
name: pre-commit-guard
description: 提交前安全检查 — 密钥泄露、敏感信息、调试代码、文件大小、gitignore 完整性
category: security
loading: on-demand
triggers:
  keywords: ["提交前", "pre-commit", "提交检查", "commit检查", "推送前", "pre-push"]
---

# 提交前守卫

## 用途
在 `git commit` 执行前自动运行一系列安全检查，防止敏感信息、调试代码、临时文件被提交到仓库。

## 检查项 (按优先级排序)

### P0 — 阻断级 (CRITICAL)
不通过则拒绝提交：

#### 1. 密钥泄露检测
扫描所有 staged 文件中的密钥模式：
```
正则匹配:
- OpenAI: sk-[a-zA-Z0-9]{32,}
- Anthropic: sk-ant-[a-zA-Z0-9]{32,}
- GitHub: ghp_[a-zA-Z0-9]{36,}
- AWS: AKIA[0-9A-Z]{16}
- Generic: ['\"]?(?:api[_-]?key|secret|token|password)['\"]?\s*[:=]\s*['\"][^'\"]{8,}
```

#### 2. 调试代码检测
扫描以下模式：
- `console.log(` (JS/TS)
- `print(` 不在日志模块中的使用 (Python)
- `debugger;` (JS/TS)
- `TODO` / `FIXME` / `HACK` (如果有 --strict 标记)
- `@pytest.mark.skip` 或 `it.skip(` (跳过的测试)

#### 3. 大文件检测
- 单个文件 > 1MB 警告
- 单个文件 > 10MB 阻断
- staged 总变更 > 50MB 警告

### P1 — 警告级 (WARN)
通过但提醒：

#### 4. 敏感路径检测
- `.env` 文件是否在 staged 中（应在 gitignore）
- `node_modules/` 子文件
- `__pycache__/` 子文件
- `*.pyc` 文件

#### 5. gitignore 完整性
- 检查 `.gitignore` 是否存在
- 验证常见敏感模式已覆盖：`.env`, `node_modules/`, `__pycache__/`, `*.pyc`, `dist/`, `build/`

### P2 — 建议级 (INFO)

#### 6. 代码风格
- Python: 是否通过 black/isort
- JS/TS: 是否通过 prettier
- 文件名是否符合项目规范

#### 7. 测试状态
- 是否有跳过的测试
- 覆盖率是否下降

## 核心规则
- P0 问题 → 拒绝提交，列出具体文件和行号
- P1 问题 → 警告，允许 `--no-verify` 跳过
- P2 问题 → 信息提示，不阻止提交
- 检查结果输出到终端 + 写入 `.claude/commit-check.log`
- 可通过 `AGENCY_NO_PRECOMMIT=1` 环境变量完全跳过

## 输出格式

```json
{
  "passed": false,
  "blockers": [
    {"file": "src/api.py", "line": 42, "issue": "疑似硬编码 API key", "severity": "P0"}
  ],
  "warnings": [
    {"file": "src/old.ts", "line": 15, "issue": "console.log 残留", "severity": "P1"}
  ],
  "info": [
    {"issue": "建议运行 black 格式化 3 个文件", "severity": "P2"}
  ],
  "verdict": "BLOCKED — 1 个阻断级问题需要修复"
}
```
