# Contributing

Agency is maintained on a best-effort basis. Issues and pull requests are welcome, but there is no fixed response or merge SLA.

## Development setup

```bash
git clone https://github.com/Sweetteabittersugar/agency.git
cd agency
python -m venv .venv
python -m pip install -e ".[dev]"
```

Activate the virtual environment with `.\.venv\Scripts\Activate.ps1` on Windows PowerShell or `source .venv/bin/activate` on macOS/Linux.

## Required checks

```bash
ruff check .
python -m compileall -q maestro scripts
python scripts/check_js.py
python scripts/verify_release.py
python -m pytest -q
git diff --check
```

Keep changes focused. Add tests for behavior changes, especially durable-run transitions, project path boundaries, authentication, and CLI behavior. Never commit real API keys, tokens, credentials, private workspace context, or generated runtime databases.

## Agent and Skill changes

- Product Agent entries live in `agent.yaml`; keep their referenced files valid.
- Skills live under `skills/<name>/`.
- If either registry changes, update documentation and release evidence in the same pull request.
- Do not change the public 33 Agent / 7 Skill claim without updating `scripts/verify_release.py`.

## Pull requests

Use a short conventional title such as `fix: reject project path escape`. Explain:

1. what changed and why;
2. security or compatibility impact;
3. the exact checks you ran;
4. any known limitation left open.

The repository uses squash merging. By participating you agree to [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
