# RULES.md — 工程规范总览

> agency-kit 的所有规范文件索引。每个规范文件标注了适用范围和优先级。

## 规范层级

```
rules/
├── architecture.md        # 项目结构规范 [所有项目]
├── maestro.md             # Agent 调度规则 [使用 Maestro 的项目]
├── security.md            # 安全规范 [所有项目，最高优先级]
├── coding-style.md        # 代码风格规范 [所有项目]
├── git-workflow.md        # Git 工作流 [所有项目]
│
├── common/                # === 通用最佳实践 ===
│   ├── agents.md          # Agent 编排策略
│   ├── coding-style.md    # 代码风格（不可变性、文件组织、错误处理）
│   ├── git-workflow.md    # Git 工作流
│   ├── hooks.md           # Hooks 系统
│   ├── patterns.md        # 通用设计模式
│   ├── performance.md     # 性能优化（模型选择、上下文管理）
│   ├── security.md        # 安全指南（密钥、输入校验、提交检查）
│   └── testing.md         # 测试要求（80% 覆盖率、TDD）
│
├── python/                # === Python 规范 ===
│   ├── coding-style.md    # PEP 8、类型注解、black/ruff
│   ├── hooks.md           # PostToolUse 自动格式化
│   ├── patterns.md        # Protocol、Dataclass、Context Manager
│   ├── security.md        # bandit 扫描、密钥管理
│   └── testing.md         # pytest、coverage
│
├── golang/                # === Go 规范 ===
│   ├── coding-style.md    # gofmt、接口设计、错误包装
│   ├── hooks.md           # go vet、staticcheck
│   ├── patterns.md        # Functional Options、DI
│   ├── security.md        # gosec、Context 超时
│   └── testing.md         # table-driven、-race
│
└── typescript/            # === TypeScript 规范 ===
    ├── coding-style.md    # 不可变性、async/await、Zod
    ├── hooks.md           # Prettier、tsc 检查
    ├── patterns.md        # Repository、Custom Hooks
    ├── security.md        # 环境变量、security-reviewer
    └── testing.md         # Playwright E2E
```

## 优先级

1. **security.md** — 任何时候不能违反
2. **maestro.md** — 使用 Agent 调度时必须遵守
3. **coding-style.md** — 写代码时遵守
4. **语言规范** — 写对应语言时自动应用

## 添加新规范

1. 在对应目录下创建 `.md` 文件
2. 如需要跨语言，放在 `common/`
3. 如针对特定语言，放在对应语言目录
4. 更新本文档的索引
