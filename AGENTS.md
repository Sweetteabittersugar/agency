# AGENTS.md — Agent 路由矩阵

> 32 个 Agent，按 13 大类组织。收到任务 → 路由矩阵判断 → 自动选择最佳 Agent。

## 路由矩阵

### 架构设计
| 关键词 | Agent |
|--------|-------|
| 系统设计/架构/技术选型/接口设计 | `architect` |

### 编码实现
| 关键词 | Agent |
|--------|-------|
| 写/改/重构/代码/实现 | `coder` |
| 构建报错/编译失败/依赖冲突 | `build-error-resolver` |
| 性能/瓶颈/优化/慢查询 | `performance-optimizer` |

### 审查验证
| 关键词 | Agent |
|--------|-------|
| 审查/review/检查（通用） | `code-reviewer` |
| Go审查 | `go-reviewer` |
| Python审查/Django/Flask | `python-reviewer` |
| TS审查/React/Node | `typescript-reviewer` |
| 评估输出/质量检查 | `critic` |

### 测试
| 关键词 | Agent |
|--------|-------|
| 测试/验证/跑/test | `test-runner` |
| TDD/测试先行/生成测试 | `tdd-guide` |
| E2E/Playwright/浏览器 | `e2e-runner` |
| 验证改动/确认修复 | `verifier` |

### 安全
| 关键词 | Agent |
|--------|-------|
| 安全/审计/漏洞 | `security-reviewer` |

### 运维
| 关键词 | Agent |
|--------|-------|
| CI/CD/Docker/部署 | `devops` |
| 发版/发布/CHANGELOG | `release-manager` |

### 数据
| 关键词 | Agent |
|--------|-------|
| 数据库/SQL/Schema/索引 | `database-reviewer` |

### 设计
| 关键词 | Agent |
|--------|-------|
| 界面/UI/UX/交互 | `designer` |

### 编排
| 关键词 | Agent |
|--------|-------|
| 调度/编排/多Agent/拆解 | `orchestrator` |
| 路由/意图识别 | `router` |
| 规划/方案/计划 | `planner` |
| 带队/领导/统筹 | `lead` |
| 产品/需求/验收/优先级 | `ceo` |

### 内容
| 关键词 | Agent |
|--------|-------|
| 写小说/网文/世界观/章节 | `webnovel-writer` |

### 文档
| 关键词 | Agent |
|--------|-------|
| 更新文档/README/CHANGELOG | `doc-updater` |
| 压缩上下文/摘要/记忆 | `memory-keeper` |

### 搜索
| 关键词 | Agent |
|--------|-------|
| 查/搜/找/定位/grep | `explorer` |
| 调试/debug/排查/根因 | `debugger` |

### 通用
| 关键词 | Agent |
|--------|-------|
| 通用/整理/配置/杂务 | `general-worker` |
| 费用/用量/@cost | `cost-analyst` |
| 模糊/复合意图 | 反问用户 |

## 任务分级

| 级别 | 标准 | 执行 |
|------|------|------|
| 轻活 | 单文件读写、搜索、简单编辑 | Agent 直调 |
| 重活 | 3+文件写操作、worktree 隔离、重构 | dispatch.py |

## 添加新 Agent

1. `agents/your-agent.md`（遵循 AGENT.md 格式）
2. 在上面路由矩阵中加条目
3. `maestro/agents.json` 注册（如用 dispatch）
