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

## 启动与连接

### 启动后页面空白
1. 按 F12 打开浏览器控制台，查看是否有红色报错
2. 确认 `python --version` >= 3.10
3. 重新安装依赖：`pip install -e .`
4. 清除浏览器缓存后重试

### 端口 8800 被占用
1. 检查占用进程：Windows `netstat -ano | findstr 8800` / macOS `lsof -i :8800`
2. 关闭占用进程，或设置环境变量 `AGENCY_PORT=8801` 换端口
3. 重启 Agency

### 浏览器打不开 localhost:8800
1. 确认 Agency 已启动（终端应有"🚀 Agency"输出）
2. 检查防火墙是否阻止了 Python
3. 尝试 `http://127.0.0.1:8800` 替代 localhost

## API 与模型

### API Key 配置后提示无效
1. 确认 Key 没有多余空格
2. 检查 Provider 选择是否正确（DeepSeek 的 Key 不能用于 OpenAI）
3. 确认 API Key 有余额/未过期
4. 查看终端错误日志排查具体原因

### Agent 回复乱码
1. 检查终端编码：`chcp 65001`（Windows）或 `export LANG=zh_CN.UTF-8`（Linux/macOS）
2. 浏览器编码设为 UTF-8
3. 如果特定 Agent 出现乱码，尝试切换其他 Agent

### API 调用超时
1. 检查网络连接
2. 某些模型（如 Opus）响应较慢，正常等待即可
3. 在设置中切换更快的模型（如 DeepSeek-Chat）

## 性能与数据

### 界面加载缓慢
1. 清除 `maestro/sessions/` 中的旧会话文件
2. 关闭不用的 Worktree（仪表盘 → 工作区 → 删除）
3. 检查 `maestro/cost.db` 是否过大（>100MB），考虑归档

### 费用数据显示异常
1. 检查 `maestro/cost.db` 文件是否存在
2. 如费用为零，确认已成功发送过任务
3. 如费用异常高，检查是否有未关闭的 SSE 连接持续计费

### 对话历史丢失
1. 检查 `maestro/sessions/` 目录是否存在
2. 确认磁盘空间充足
3. 检查浏览器控制台是否有 localStorage 写入错误

## 微信 Bot

### 扫码后无法连接
1. 确认微信版本 >= 8.0.70
2. 二维码有效期 5 分钟，超时需刷新
3. 检查网络是否能访问 `ilinkai.weixin.qq.com`
4. 重新登录：仪表盘 → 连接 → 微信 → 退出 → 重新扫码

### 微信消息发不出去
1. 24 小时内最多主动发 10 条消息（微信限制）
2. 用户超过 24 小时未发消息，Bot 消息会被丢弃
3. 检查 Bot 状态是否为"运行中"

## 恢复与备份

### 想回到初始状态
1. 设置 → 恢复默认 → 选择恢复范围
2. "清空所有自定义"：只删你的自定义 Agent/Skill
3. "恢复出厂设置"：恢复所有系统文件到默认（需要 git）
4. 恢复前建议备份：复制 `.claude/agents/user/` 和 `.env`
