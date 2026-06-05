# agency-kit for Gemini CLI

Gemini CLI 适配层。将 agency-kit 的 agents、rules、skills 映射到 Gemini CLI 的能力体系。

## 概述

Gemini CLI 使用不同的 Agent 和 skill 机制。agency-kit 的大部分规范和自动化工作流可以通过适配在 Gemini CLI 中复用。

## Agent 映射

Gemini CLI 使用 `agents` 配置定义子代理。以下是将 ECC Agent 映射到 Gemini CLI 的配置：

### gemini.json 配置

```json
{
  "agents": {
    "coder": {
      "description": "代码编写和修改",
      "systemPrompt": "你是代码执行者，负责写代码、改代码、重构。严格遵循项目规范。"
    },
    "reviewer": {
      "description": "代码审查",
      "systemPrompt": "你是代码审查员。检查代码的安全性、性能、可维护性。"
    },
    "explorer": {
      "description": "代码搜索和分析",
      "systemPrompt": "你是代码探索员。只读搜索，不修改文件。快速定位代码和问题。"
    },
    "test-runner": {
      "description": "测试执行",
      "systemPrompt": "你是测试执行员。运行测试，报告结果，不修改源代码。"
    },
    "general-worker": {
      "description": "通用任务处理",
      "systemPrompt": "你是通用执行者。处理配置、整理、杂务类任务。"
    },
    "planner": {
      "description": "架构规划",
      "systemPrompt": "你是规划架构师。先规划再执行，确保方案可行。"
    }
  }
}
```

## Rule 映射

agency-kit 的规则文件可以复制到 Gemini CLI 的配置中：

```
~/.gemini/
├── rules/
│   ├── coding-style.md    ← rules/common/coding-style.md
│   ├── testing.md          ← rules/common/testing.md
│   ├── security.md         ← rules/common/security.md
│   ├── git-workflow.md    ← rules/common/git-workflow.md
│   ├── hooks.md            ← rules/common/hooks.md
│   ├── patterns.md         ← rules/common/patterns.md
│   ├── performance.md      ← rules/common/performance.md
│   └── agents.md           ← rules/common/agents.md
```

语言特定规则：
```
~/.gemini/rules/
├── python/     ← rules/python/
├── typescript/ ← rules/typescript/
└── golang/     ← rules/golang/
```

在 `~/.gemini/settings.json` 中加载：

```json
{
  "rules": [
    "~/.gemini/rules/coding-style.md",
    "~/.gemini/rules/testing.md",
    "~/.gemini/rules/security.md",
    "~/.gemini/rules/git-workflow.md",
    "~/.gemini/rules/patterns.md",
    "~/.gemini/rules/performance.md"
  ]
}
```

## Skill 映射

Gemini CLI 使用 `commands` 和 `skills` 两个概念。ECC 的 skill 可移植如下：

### 技能映射表

| ECC Skill | Gemini 实现方式 | 说明 |
|-----------|----------------|------|
| `/design` | 自定义 command | 创建 commands/design.md 移植四阶段流程 |
| `/compress` | Gemini 自动管理 | Gemini CLI 自行管理上下文，无需手动压缩 |
| `@cost` | 保留 Python 脚本 | 复制 maestro/cost-tracker.py，用 command 调用 |
| `@status` | 保留 Python 脚本 | 复制 maestro/dispatch.py --status |

### 自定义命令示例

`~/.gemini/commands/cost.md`:
```markdown
# /cost — 查看 API 费用

调用 agency-kit 的费用追踪脚本。

用法：
- /cost          今日汇总
- /cost 7        最近 7 天
- /cost live     实时看板

执行：python maestro/cost-tracker.py [args]
```

`~/.gemini/commands/design.md`:
```markdown
# /design — 设计模式

进入四阶段需求澄清模式：目标 → 约束 → 方案 → 确认。

说「设计完成」退出，输出结构化提示词。
```

## Maestro 调度引擎

Gemini CLI 有自己的任务系统，Maestro 调度引擎的适配策略：

### 保留的部分（直接可用）
- `maestro/cost-tracker.py` — 费用实时追踪
- `maestro/cost-analyzer.py` — 费用深度分析
- `maestro/task-tracker.py` — 任务看板

### 需要适配的部分
- `maestro/dispatch.py` — Agent 调度，改用 Gemini 的 agents 系统
- `maestro/gateway.py` — 结果网关，改用 Gemini 的输出处理
- `maestro/sandbox.py` — 隔离执行，Gemini CLI 有内置沙箱

## 安装步骤

```bash
# 1. 复制规则文件
cp -r agency-kit/rules/common ~/.gemini/rules/
cp -r agency-kit/rules/python ~/.gemini/rules/     # 按需
cp -r agency-kit/rules/typescript ~/.gemini/rules/ # 按需
cp -r agency-kit/rules/golang ~/.gemini/rules/     # 按需

# 2. 配置 gemini.json（Agent 定义）
# 参考上方 Agent 映射章节

# 3. 复制费用追踪脚本
mkdir -p your-project/maestro
cp agency-kit/maestro/cost-tracker.py your-project/maestro/
cp agency-kit/maestro/cost-analyzer.py your-project/maestro/
cp agency-kit/maestro/cost-writer.py your-project/maestro/

# 4. 创建自定义命令
mkdir -p ~/.gemini/commands
# 创建 cost.md 和 design.md（参考上方示例）

# 5. 在 gemini.json 中注册规则
# 参考上方 Rule 映射章节的 settings.json 配置
```

## 与 Claude Code 版的差异

| 功能 | Claude Code | Gemini CLI |
|------|------------|------------|
| Agent 调度 | dispatch.py | gemini.json agents 配置 |
| Hooks 系统 | SessionStart/PostToolUse/Stop/PreCompact | 不支持等价机制 |
| 上下文压缩 | /compress skill | 自动管理 |
| 费用追踪 | cost-tracker.py | 保留 Python 脚本，command 调用 |
| 任务看板 | task-tracker.py | 保留 Python 脚本 |
| 设计模式 | /design skill | 自定义 command 移植 |
| 多语言规则 | rules/ 自动加载 | settings.json 显式注册 |

## 限制

- Gemini CLI 的 hooks 机制与 Claude Code 不同，SessionStart/PostToolUse 等自动化脚本不能直接使用
- dispatch.py 调度系统与 Gemini 的 agents 不兼容，Agent 定义需重写
- PreCompact hook 不可用（Gemini CLI 自行管理上下文压缩窗口）
- 部分 Maestro 功能（如 cleanup-agents.py、notif-proxy.py）可能需要针对 Gemini CLI 的进程管理重写
