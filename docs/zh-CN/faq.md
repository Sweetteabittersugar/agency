# 常见问题 (FAQ)

## 安装

### Q: 安装后 Agent 没有生效？
检查 `~/.claude/agents/` 下是否有 .md 文件。如果没有，重新运行 `./install.sh`。

### Q: 只想安装部分 Agent？
手动复制需要的文件：
```bash
cp agents/coder.md agents/code-reviewer.md ~/.claude/agents/
```

### Q: 如何卸载？
删除对应的目录即可：
```bash
rm -rf ~/.claude/agents ~/.claude/skills ~/.claude/commands ~/.claude/hooks ~/.claude/rules
```

## Agent

### Q: 如何知道当前用的是哪个 Agent？
系统会根据关键词自动路由。查看 `AGENTS.md` 了解路由规则。

### Q: Agent 返回的内容是英文？
设置 `CLAUDE.md` 中的铁律"禁止用英文"（默认已设置）。

### Q: 可以同时用多个 Agent 吗？
可以。独立的任务会自动并行分派给不同 Agent。

## Maestro

### Q: dispatch.py 报找不到模块？
确保在项目根目录运行，并且 Python 3.10+ 可用：
```bash
python --version
python maestro/dispatch.py --list
```

### Q: cost-tracker 数据在哪？
SQLite 数据库：`maestro/cost.db`。可以用任何 SQLite 工具查看：
```bash
sqlite3 maestro/cost.db "SELECT * FROM costs ORDER BY date DESC LIMIT 10;"
```

### Q: 成本追踪支持哪些模型？
支持 haiku/sonnet/opus/deepseek-v4-pro/deepseek-v4-flash/deepseek-v3/deepseek-r1/mimo-v2-pro。未知模型按 sonnet 估算。

## 设计模式

### Q: 设计模式和普通对话有什么区别？
设计模式是多阶段的引导式对话（目标→约束→方案→确认），帮你把模糊想法变成结构化方案。说 `/design` 进入，说"设计完成"退出。

### Q: 沙盘推演什么时候用？
当你有一个想法想评估时——不直接执行也不直接反驳，而是三步分析（建设→挑战→裁判）。

## 性能

### Q: 太多了会影响 Claude Code 速度吗？
不会。Agent 定义是按需加载的，只有当前任务需要的 agent 才会注入上下文。这也是我们和 ECC 的核心区别。

### Q: Python 必须 3.10+ 吗？
Maestro 脚本用到了 3.10 的 `match` 语法。如果不用 Maestro，Python 版本无要求。

## 贡献

### Q: 如何贡献新 Agent？
见 `CONTRIBUTING.md`。简单的流程：创建 agents/xxx.md（含 YAML frontmatter）→ 更新 AGENTS.md 路由矩阵 → 更新 agent.yaml → 提 PR。

### Q: Agent 的 model 字段选什么？
- `haiku`：简单搜索、费用分析
- `sonnet`：代码编写、审查、规划
- `opus`：复杂创作（小说、深度推理）
