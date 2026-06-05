# Architecture Rules — 架构规范

> Layer 1: Memory Layer | 命名、结构、仓库规范

---

## 命名规范

### 目录命名
- **中文目录**：项目级目录可使用中文，保持可读性
- **英文目录**：技术配置目录使用英文（`.claude/`、`docker/`、`scripts/` 等）
- **子目录**：子项目内部目录风格跟随各自项目惯例

### 文件命名
- **Python 代码**：`snake_case`（`test_run.py`、`linear_algebra.py`）
- **配置文件**：`lowercase.ext` 或 `CONSTANT_CASE`（`config.yaml`、`CLAUDE.md`）
- **Markdown 文档**：中文描述性命名或英文标准名（`用户画像.md`、`README.md`）
- **Shell 脚本**：`PascalCase.sh`（`SessionStart.sh`），匹配 Claude Code hooks 惯例

---

## 仓库结构

```
$PROJECT_ROOT/                  ← 项目根目录
├── CLAUDE.md                   ← 项目入口指令
├── .claude/                    ← Claude Code 配置
│   ├── settings.json           ← 基线设置
│   ├── settings.local.json     ← 本地覆盖
│   ├── rules/                  ← 项目规则
│   ├── commands/               ← 自定义命令
│   ├── agents/                 ← 子智能体定义
│   ├── skills/                 ← 已安装技能
│   ├── scripts/                ← 共享脚本
│   ├── hooks/                  ← 护栏钩子
│   ├── global.md               ← 全局规则
│   ├── project.md              ← 项目级配置
│   └── context.md              ← 上下文知识
├── <子项目目录>/               ← 按领域组织的子项目
└── <其他目录>/                 ← 根据项目需要自由扩展
```

### 模块边界
- 每个子目录一个独立项目，有自己的入口和依赖
- 通用脚本和工具放在各自约定的位置
- 日志和生成物统一管理，避免散落

---

## 技术栈

详见 `AGENTS.md`（环境）和 `.claude/global.md`（硬约束）。
