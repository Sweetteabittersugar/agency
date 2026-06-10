# Agency

> Claude Code 的 Web 操作面板 — 多 Agent 协作 · 实时监控 · 手机远程操控

<p align="center">
  <em>输入任务 → 自动匹配 Agent → 流式返回。多面板分屏、实时费用追踪。</em>
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-green)](VERSION)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![Agents](https://img.shields.io/badge/Agents-33-purple)]()
[![Skills](https://img.shields.io/badge/Skills-34-orange)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

## 快速开始

```bash
# 1. 安装
git clone https://github.com/Sweetteabittersugar/agency.git && cd agency
pip install -e .

# 2. 启动
agency start
# → 浏览器自动打开 http://localhost:8800
# → 无 API Key 也能体验 Demo！

# 3. 配置（可选）
# 点右上角 🔧 → 填入 API Key → 开始干活
```

> **Windows 用户？** 下载解压 → 双击 `install.bat` → 双击 `start.bat`。三步搞定。

## 功能亮点

| 🧠 | 📊 | 📱 |
|:---:|:---:|:---:|
| **多 Agent 协作** | **实时仪表盘** | **手机远程操控** |
| 33 个专业 Agent 按 12 大类自动匹配任务 | Token · 费用 · 权限全追踪 | 扫码即用，电脑关机也能查 |
| @agent名 显式指定 | 按日期/模型/Agent 三维分析 | 密码保护，Token 持久化 |

| 🔧 | 🎨 | 🔌 |
|:---:|:---:|:---:|
| **Skill 工作流** | **多面板分屏** | **11 家模型供应商** |
| 34 个可复用技能模板 | 1/2/4 窗随心切换 | DeepSeek · GPT · Claude · Gemini |
| 一键编辑源码、启用/禁用 | 面板间独立会话互不干扰 | Kimi · 通义 · 智谱 · MiniMax… |

## 安装

<details open>
<summary><b>pip install（推荐）</b></summary>

```bash
git clone https://github.com/Sweetteabittersugar/agency.git
cd agency
pip install -e .
agency start
```
</details>

<details>
<summary><b>Windows 一键安装</b></summary>

```
下载解压 → 双击 install.bat → 双击 start.bat
```
</details>

<details>
<summary><b>手动安装（只要 Agent 层，30 秒）</b></summary>

不需要 Web 界面？只把 Agent 定义装进 Claude Code：
```bash
cp agents/coder.md ~/.claude/agents/
# Claude Code 里输入 @coder 写个排序函数 就能用
```
</details>

> **需要 Claude CLI？** `npm install -g @anthropic-ai/claude-code`。没有 Claude Key？用 DeepSeek 也一样跑。

## 架构

```
┌─────────────────────────────────────────────────┐
│                    Agency Web UI                  │
│         聊天 · 仪表盘 · 设置 · Skill管理          │
└──────────────────────┬──────────────────────────┘
                       │ REST + SSE
┌──────────────────────▼──────────────────────────┐
│               Maestro 调度引擎                    │
│  路由(关键词+语义) → 分配Agent → 沙箱执行 → 结果  │
└──────────────────────┬──────────────────────────┘
                       │ claude -p / stdin
┌──────────────────────▼──────────────────────────┐
│              Claude Code + MCP                   │
│  Agent 定义 · Skill 工作流 · Hook 自动化          │
│  Playwright · Context7 · Brave Search …          │
└─────────────────────────────────────────────────┘
```

## 项目结构

```
agency/
├── maestro/        调度引擎（路由/聊天/编排/成本/安全）
├── webui/          前端（模块化 JS + CSS 暗色主题 + HTML）
├── agents/         33 个 Agent 定义（12 大类）
├── .claude/skills/ 34 个 Skill 工作流
├── rules/          工程规范
├── hooks/          生命周期自动化
├── commands/       快捷命令
├── docs/           文档
└── tests/          测试
```

## 常见问题

<details>
<summary><b>需要 Claude API Key 吗？</b></summary>

不必须。Agency 支持 11 家模型供应商，推荐 **DeepSeek**（便宜、中文好、注册即送额度）。无 Key 也能进入 Demo 模式浏览全部功能。
</details>

<details>
<summary><b>我的 Key 安全吗？</b></summary>

**绝对安全。** Key 仅存两份：浏览器 localStorage（你的电脑上）和项目 `.env` 文件（已 `.gitignore`）。**永不离开你的设备，永不上传任何服务器。**
</details>

<details>
<summary><b>和 Claude Code 原版有什么区别？</b></summary>

Agency 是 Claude Code 的 **Web 操作面板**。Claude Code 是命令行 AI 编程工具，Agency 给它加了：Web 界面、多 Agent 智能路由、实时费用追踪、手机远程操控、多面板分屏协作。
</details>

<details>
<summary><b>能离线用吗？</b></summary>

Web 界面完全本地运行。但 Agent 执行需要调 AI 模型 API（DeepSeek/OpenAI 等），这部分需要联网。
</details>

## 贡献

欢迎 PR！详见 [CONTRIBUTING.md](CONTRIBUTING.md)。新功能建议请先开 Issue 讨论。

快速入门：[GETTING-STARTED.md](GETTING-STARTED.md) | 完整教程：[USAGE.md](USAGE.md)

## 致谢

- [Claude Code](https://claude.ai/code) — Anthropic 的 AI 编程工具
- [ECC](https://github.com/affaan-m/ECC) — 207K Stars 的 Claude Code 配置增强标杆

## License

MIT © 2026 Sweetteabittersugar
