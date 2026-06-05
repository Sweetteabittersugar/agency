# 快速开始

## 安装

### 方式一：Git 克隆（推荐）

```bash
git clone https://github.com/Sweetteabittersugar/agency.git
cd agency
./install.sh
```

安装时选择：
- **全局安装** → 所有项目都能用
- **项目安装** → 仅当前项目生效

### 方式二：npm

```bash
npm install -g agency-kit
```

## 验证

在 Claude Code 中测试：

```
@status          # 查看 Agent 任务状态
@cost            # 查看 API 费用
```

看到正常输出即安装成功。

## 目录结构

安装后 `.claude/` 下新增：

```
.claude/
├── agents/       # 9 个专业子代理
├── skills/       # 6 个工作流技能
├── commands/     # 4 个快捷命令
├── hooks/        # 4 个自动化钩子
└── rules/        # 8+ 套工程规范
```

## 下一步

- 试试 `/design` 进入设计模式
- 试试 `@tracker` 查看任务看板
- 阅读 `AGENTS.md` 了解 Agent 路由规则
- 阅读 `maestro/` 下的脚本了解调度系统
