# Agency

> Web Dashboard for Claude Code — Multi-Agent · Live Monitor · Remote Control

<p align="center">
  <img src="docs/screenshot.png" alt="Agency Screenshot" width="800"><br>
  <em>▲ Type your task → auto-matched Agent → streaming response. Split panels, real-time cost tracking.</em>
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-green)](VERSION)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![Agents](https://img.shields.io/badge/Agents-31-purple)]()
[![Skills](https://img.shields.io/badge/Skills-34-orange)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

> *中文用户？[点此阅读中文 README](README.md)*

## Quick Start

```bash
# 1. Install
git clone https://github.com/Sweetteabittersugar/agency.git && cd agency
pip install -e .

# 2. Launch
agency start
# → Opens http://localhost:8800 in your browser
# → Browse Demo mode without any API Key!

# 3. Configure (optional)
# Click 🔧 → enter your API Key → start working
```

> **Windows?** Download → extract → double-click `install.bat` → double-click `start.bat`. Done.

## Features

| 🧠 | 📊 | 📱 |
|:---:|:---:|:---:|
| **Multi-Agent** | **Live Dashboard** | **Remote Control** |
| 31 specialized agents auto-matched | Token · Cost · Permissions tracking | Access from phone/tablet |
| Use @agentname to specify | 3D analysis by date/model/agent | Password protected |

| 🔧 | 🎨 | 🔌 |
|:---:|:---:|:---:|
| **Skill Workflows** | **Split Panels** | **11 Providers** |
| 34 reusable skill templates | 1/2/4 panel layouts | DeepSeek · GPT · Claude · Gemini |
| Edit source, toggle on/off | Independent sessions per panel | Kimi · Qwen · GLM · MiniMax… |

## Installation

<details open>
<summary><b>pip install (recommended)</b></summary>

```bash
git clone https://github.com/Sweetteabittersugar/agency.git
cd agency
pip install -e .
agency start
```
</details>

<details>
<summary><b>Windows one-click</b></summary>

Download → extract → double-click `install.bat` → double-click `start.bat`
</details>

<details>
<summary><b>Manual (Agents only, 30 seconds)</b></summary>

Don't need the Web UI? Just install Agent definitions:
```bash
cp agents/coder.md ~/.claude/agents/
# In Claude Code: @coder write a sorting function
```
</details>

> **Need Claude CLI?** `npm install -g @anthropic-ai/claude-code`. No Claude Key? DeepSeek works great too.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Agency Web UI                    │
│        Chat · Dashboard · Settings · Skills      │
└──────────────────────┬──────────────────────────┘
                       │ REST + SSE streaming
┌──────────────────────▼──────────────────────────┐
│              Maestro Engine                       │
│  Route (keyword+semantic) → Agent → Sandbox → Out│
└──────────────────────┬──────────────────────────┘
                       │ claude -p / stdin pipe
┌──────────────────────▼──────────────────────────┐
│            Claude Code + MCP                     │
│  Agents · Skills · Hooks · Rules                 │
│  Playwright · Context7 · Brave Search …          │
└─────────────────────────────────────────────────┘
```

## FAQ

<details>
<summary><b>Do I need a Claude API Key?</b></summary>

No. Agency supports 11 model providers. We recommend **DeepSeek** (affordable, excellent Chinese support). You can also browse the full UI in Demo mode without any key.
</details>

<details>
<summary><b>Is my API Key safe?</b></summary>

**Absolutely.** Your key is stored only in browser localStorage (on your machine) and the project `.env` file (gitignored). **It never leaves your device, never uploaded anywhere.**
</details>

<details>
<summary><b>How is this different from Claude Code?</b></summary>

Agency is a **Web Dashboard** for Claude Code. Claude Code is a CLI coding tool; Agency adds: Web UI, intelligent Agent routing, real-time cost tracking, remote mobile access, and multi-panel collaboration.
</details>

<details>
<summary><b>Can I use it offline?</b></summary>

The Web UI runs entirely locally. However, Agent execution requires API calls to AI model providers (DeepSeek, OpenAI, etc.) — that part needs internet.
</details>

## Contributing

PRs welcome! See [CONTRIBUTING.md](CONTRIBUTING.md). Please open an Issue before proposing major changes.

Quick start: [GETTING-STARTED.md](GETTING-STARTED.md) | Full guide: [USAGE.md](USAGE.md)

## Credits

- [Claude Code](https://claude.ai/code) — Anthropic's AI coding tool
- [ECC](https://github.com/affaan-m/ECC) — 207K+ Stars Claude Code enhancement benchmark

## License

MIT © 2026 Sweetteabittersugar
