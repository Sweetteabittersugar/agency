# Hooks 使用指南

## 什么是 Hooks

Hooks 是 Claude Code 在特定时机自动执行的脚本。agency-kit 提供 4 个 hook：

| Hook | 触发时机 | 功能 |
|------|----------|------|
| `SessionStart.sh` | 会话启动 | 环境检查、日志初始化 |
| `PostToolUse.sh` | 每次工具调用后 | 操作日志、日志轮转 |
| `PreCompact.sh` | 上下文压缩前 | 关键信息保存 |
| `Stop.sh` | 会话结束 | 临时文件清理、日志归档 |

## 安装后验证

```bash
# 检查 hook 是否可执行
ls -la ~/.claude/hooks/*.sh

# 查看 SessionStart 日志
cat ~/.claude/hooks/session-start.log

# 查看 PostToolUse 日志
cat ~/.claude/hooks/post-tool-use.log
```

## 自定义 Hooks

### 添加新的 Hook

1. 在 `hooks/` 下创建脚本（`#!/usr/bin/env bash`）
2. 添加执行权限：`chmod +x hooks/your-hook.sh`
3. 在 Claude Code 的 `settings.json` 中注册

### 常用自定义示例

#### 自动 Git 提交记录
```bash
#!/usr/bin/env bash
# 会话结束前自动记录未提交的改动
echo "[$(date -Iseconds)] Uncommitted changes:" >> .claude/git-log.txt
git status --short >> .claude/git-log.txt
```

#### 文件修改通知
```bash
#!/usr/bin/env bash
# 修改关键配置文件时弹通知
if echo "$CLAUDE_TOOL_INPUT" | grep -q "config.yaml"; then
    echo "⚠ config.yaml was modified" >> .claude/warnings.log
fi
```

## 日志管理

PostToolUse.sh 内置了日志轮转——超过 1MB 自动截断到 1000 行。

手动清理：
```bash
rm ~/.claude/hooks/*.log
```

## 扩展点

所有 hook 脚本末尾都有 `# === 扩展点 ===` 注释标记的位置，可以在那里添加自定义逻辑，无需修改脚本主体。
