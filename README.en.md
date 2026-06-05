# agency-kit

> Chinese-native Claude Code configuration platform — Agent orchestration, cost tracking, creative workflows. Battle-tested in daily production.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-green)](VERSION)

```bash
git clone https://github.com/Sweetteabittersugar/agency.git
cd agency && ./install.sh
```

* [中文 README](README.md)

## What is this

**agency-kit** is a Claude Code enhancement system. It's not another AI tool — it's a plugin layer that adds these capabilities to your existing Claude Code:

```
Your Claude Code
    │
    ├── agents/   ← 19 specialized sub-agents (auto-routed)
    ├── skills/   ← 7 workflow skills (design/debug/release/translate/cost/compress)
    ├── commands/ ← 4 quick commands (status/cost/track/compress)
    ├── hooks/    ← 4 automation hooks (start/stop/compress)
    ├── rules/    ← 8+ engineering standards (multi-language)
    └── maestro/  ← Multi-agent orchestration engine (unique)
```

## Why this

| | Vanilla Claude Code | ECC | **agency-kit** |
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
git clone https://github.com/Sweetteabittersugar/agency.git
cd agency

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

### Agents (19 specialized sub-agents)

| Category | Agent | Role |
|----------|-------|------|
| **Dev** | `coder` | Write, fix, refactor code |
| | `build-error-resolver` | Fix build/compile errors |
| | `refactor-cleaner` | Remove dead/duplicate code |
| **Review** | `code-reviewer` | General 4-dimension review |
| | `python-reviewer` | Python/Django/FastAPI |
| | `go-reviewer` | Go concurrency/interface |
| | `typescript-reviewer` | TS/React/Node.js |
| | `security-reviewer` | Security vulnerability audit |
| | `database-reviewer` | SQL perf/schema review |
| **Test** | `test-runner` | Test execution & analysis |
| | `tdd-guide` | TDD workflow guide |
| | `e2e-runner` | Playwright E2E testing |
| **Plan** | `planner` | Architecture & task planning |
| | `cost-analyst` | API cost analysis |
| | `performance-optimizer` | Bottleneck profiling |
| **Other** | `explorer` | Codebase search & analysis |
| | `doc-updater` | Auto-sync documentation |
| | `general-worker` | General tasks |
| | `webnovel-writer` | Novel writing |

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

### Skills (7 workflow skills)

| Skill | Trigger | Function |
|-------|---------|----------|
| `design` | `/design` | 4-phase requirement clarification |
| `debug` | "debug" | Systematic debugging workflow |
| `cost` | `@cost` | API cost tracking & reports |
| `compress` | `/compress` | Context compression |
| `init` | "new project" | Project scaffolding |
| `release` | "release" | Version & changelog management |
| `translate` | "translate" | Technical doc translation |

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
