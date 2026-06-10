# TROUBLESHOOTING.md — 常见问题

## 安装

### "cp: cannot create directory" 权限不足
```bash
# 检查目标目录权限
ls -la ~/.claude/
# 手动创建目录后重试
mkdir -p ~/.claude/agents ~/.claude/skills ~/.claude/commands ~/.claude/hooks ~/.claude/rules
./install.sh
```

### install.sh 在 Windows Git Bash 中路径错误
```bash
# 确保在 Git Bash 中运行，不要用 CMD 或 PowerShell 运行 .sh
# 或者改用 PowerShell 版本：
.\install.ps1
```

## Agent

### Agent 没有自动触发
- 检查 `~/.claude/agents/` 下文件是否存在
- 确认 CLAUDE.md 或 AGENTS.md 已正确加载
- 检查 agent 文件的 YAML frontmatter 格式是否正确

### @status / @cost 命令无效
```bash
# 检查 maestro 脚本是否可执行
python maestro/dispatch.py --list
python maestro/cost-tracker.py

# 确认 Python 3.10+ 可用
python --version
```

## Maestro

### dispatch.py 报 ModuleNotFoundError
```bash
# 确保在项目根目录执行
cd $PROJECT_ROOT
python maestro/dispatch.py --status
```

### cost-tracker.py 报数据库错误
```bash
# 检查 cost.db 权限
ls -la maestro/cost.db
# 如损坏，删除后重建（费用数据会丢失）
rm maestro/cost.db
python maestro/cost-tracker.py
```

## Hooks

### SessionStart.sh 不执行
- 确认文件有执行权限：`chmod +x hooks/SessionStart.sh`
- 检查 shebang 路径：`head -1 hooks/SessionStart.sh`（应为 `#!/usr/bin/env bash`）
- 查看日志：`cat ~/.claude/.hooks/*.log`

### PostToolUse.sh 日志过大
- PostToolUse.sh 内置了日志轮转（>1MB 自动截断到 1000 行）
- 如需要手动清理：`rm ~/.claude/.hooks/post-tool-use.log`

## 性能

### 项目文件太多导致 Claude Code 加载慢
- 只安装需要的模块，不必全装
- 手动复制特定 agent/skill/rule 到目标目录

## 反馈

如果以上没有解决你的问题，请提交 Issue：
https://github.com/Sweetteabittersugar/agency/issues

## Agent 路由问题

### Agent 总是分错
1. 使用"不对，换一个"按钮纠正路由
2. 系统会从纠正中学习，后续命中率会提升
3. 如果频繁分错，可能是 Agent description 不够清晰

### 路由返回"general-worker"
1. 系统对任务意图置信度不够高，走了兜底策略
2. 尝试更具体地描述你的需求
3. 或手动指定 Agent

## 性能问题

### 页面加载慢
1. 清除浏览器缓存
2. 检查 sessions/ 目录大小，删除旧会话
3. 关闭不用的 Worktree

### Agent 响应慢
1. 检查 API Provider 状态
2. 查看仪表盘的费用 Tab 确认是否有异常延迟
3. 减少同时运行的 Agent 数量（切换为单面板）

## 数据问题

### 刷新后对话丢失
1. 检查 maestro/sessions/ 目录是否存在
2. 确认磁盘空间充足
3. 检查浏览器控制台是否有 localStorage 错误

### 费用数据不更新
1. 确认 cost.db 文件存在且可写
2. 检查 maestro/logs/ 目录权限
