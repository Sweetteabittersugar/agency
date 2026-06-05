# everythingclaudecode

> Chinese-native Claude Code configuration platform — Agent orchestration, cost tracking, creative workflows. Battle-tested in daily production.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-green)](VERSION)

```bash
git clone https://github.com/Sweetteabittersugar/everythingclaudecode.git
cd everythingclaudecode && ./install.sh
```

* [中文 README](README.md)

## What is this

**everythingclaudecode** is a Claude Code enhancement system. It's not another AI tool — it's a plugin layer that adds these capabilities to your existing Claude Code:

```
Your Claude Code
    │
    ├── agents/   ← 9 specialized sub-agents (auto-routed)
    ├── skills/   ← 6 workflow skills (design/cost/compress/docs)
    ├── commands/ ← 4 quick commands (status/cost/track/compress)
    ├── hooks/    ← 4 automation hooks (start/stop/compress)
    ├── rules/    ← 8+ engineering standards (multi-language)
    └── maestro/  ← Multi-agent orchestration engine (unique)
```

## Why this

| | Vanilla Claude Code | ECC | **everythingclaudecode** |
|---|---|---|---|
| Language | English | English | **Chinese-native** |
| Agent routing | Manual | Manual | **Auto routing matrix** |
| Cost tracking | None | None | **Built-in, per-model/date/agent** |
| Creative tools | None | None | **Novel writing + design mode** |
| Context mgmt | Manual | Basic | **Auto-compress + memory persistence** |
| Proven | — | Template-level | **Daily production use** |

## Quick Start

```bash
# Clone
git clone https://github.com/Sweetteabittersugar/everythingclaudecode.git
cd everythingclaudecode

# Install (auto-links to Claude Code)
./install.sh        # macOS / Linux / Git Bash
# or
.\install.ps1       # Windows PowerShell
```

Verify in Claude Code:

```
@status          # Check agent status
@cost            # View API costs
/design          # Enter design mode
```

## Core Modules

### Agents (9 specialized sub-agents)

| Agent | Role | Trigger |
|-------|------|---------|
| `coder` | Write code directly | Code tasks |
| `code-reviewer` | 4-dimension code review | After writing code |
| `explorer` | Codebase search & analysis | Find/locate/analyze |
| `test-runner` | Test execution & results | Testing/verification |
| `general-worker` | General tasks | Non-specialist work |
| `webnovel-writer` | Novel writing | Writing tasks |
| `planner` | Implementation planning | Complex features |
| `security-reviewer` | Security audits | Sensitive code review |
| `cost-analyst` | API cost analysis | Cost review |

### Maestro — Multi-Agent Orchestration Engine (Unique)

```
Your Task → Routing Matrix → Auto-select Agent → Sandbox → Result Gateway → Summary
                                ↓
                           Cost Tracking (realtime)
                                ↓
                           Task Board (persistent)
```

| Script | Function |
|--------|----------|
| `dispatch.py` | Task dispatch engine |
| `sandbox.py` | Process isolation |
| `gateway.py` | Result gateway |
| `cost-tracker.py` | Realtime cost tracking |
| `cost-analyzer.py` | Cost trend analysis |
| `task-tracker.py` | Task board |
| `transcript-parser.py` | Conversation parser |
| `cleanup-agents.py` | Idle process cleanup |

### Skills (6 workflow skills)

| Skill | Trigger | Function |
|-------|---------|----------|
| `design` | `/design` | 4-phase requirement clarification |
| `cost` | `@cost` | API cost tracking & reports |
| `compress` | `/compress` | Context compression |
| `docx` | Document tasks | Word document creation |
| `pdf` | PDF tasks | PDF generation |
| `xlsx` | Spreadsheet tasks | Excel creation |

### Rules (8+ engineering standards)

```
rules/
├── architecture.md      # Project structure
├── maestro.md           # Agent routing rules
├── security.md          # Security standards
├── coding-style.md      # Code style guide
├── git-workflow.md      # Git workflow
├── common/              # Universal best practices
├── python/              # Python conventions
├── golang/              # Go conventions
└── typescript/          # TypeScript conventions
```

## Design Philosophy

### Sandbox Collaboration

For any idea: Builder (strengthen) → Challenger (stress-test) → Judge (evaluate). Core principle: **Us vs the idea**, not you vs me.

### Hybrid Dispatch

Light tasks → direct Agent tool. Heavy tasks (3+ files, isolation needed) → dispatch.py.

### Result Gateway

Agents return only concise summaries to the user. No internal thought chains or tool calls forwarded. Keeps conversations clean.

## Credits

- [everything-claude-code](https://github.com/affaan-m/ECC) — Form reference, 207K+ Stars
- [Claude Code](https://claude.ai/code) — Anthropic's AI coding tool

## License

MIT © 2026 Sweetteabittersugar
