# Agency

[中文](README.md) · [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md)

[![Version](https://img.shields.io/badge/version-0.5.0-green)](VERSION)
[![CI](https://github.com/Sweetteabittersugar/agency/actions/workflows/ci.yml/badge.svg)](https://github.com/Sweetteabittersugar/agency/actions/workflows/ci.yml)
[![Source only](https://img.shields.io/badge/distribution-source--only-blue)](#installation)

Agency is a local-first web workspace for agent routing, staged execution, cost records, and resumable runs. Version 0.5.0 is distributed as source through GitHub Releases; it is not published to PyPI or npm.

The product registry currently contains **33 agents and 7 skills**, verified from [agent.yaml](agent.yaml) and [skills/](skills/). Runtime projections and Markdown file counts serve different purposes and may not have the same count.

## What is new in v0.5.0

- A local SQLite run ledger for append-only events, DAG checkpoints, action intent/result pairs, and runner fences.
- Resumable orchestration: `POST /api/orchestrate` accepts an optional `run_id`; a task or project mismatch returns `RUN_RESUME_REJECTED`.
- Side-effect protection: an interrupted write with no recorded result returns `ACTION_RECONCILIATION_REQUIRED` and is never replayed automatically.
- A real project boundary: repeatable `--project-root PATH` arguments control file, terminal, test, and agent execution access.
- A stable CLI whose help and version paths do not start the server. The default listener is `127.0.0.1`.

## Installation

Python 3.10–3.13 is supported. The source workflow below is the only supported distribution method for this release.

```bash
git clone https://github.com/Sweetteabittersugar/agency.git
cd agency
git checkout v0.5.0
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
agency --version
```

macOS / Linux:

```bash
source .venv/bin/activate
python -m pip install -e .
agency --version
```

The version command prints only `0.5.0`.

## Starting Agency

```bash
agency start --project-root /path/to/your/project
```

The default URL is `http://127.0.0.1:8800`. Repeat the option to allow more than one directory:

```bash
agency start \
  --project-root /path/to/project-a \
  --project-root /path/to/project-b
```

With no project root, the UI can start, but project file browsing, agent execution, terminals, and test operations are rejected. Request paths are canonicalized on every access and checked again after resolving symlinks or junctions.

A non-loopback listener requires explicit authentication:

```bash
export AGENCY_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
agency start --host 0.0.0.0 --project-root /path/to/project
```

In PowerShell, generate a temporary token with `$env:AGENCY_TOKEN = & python -c "import secrets; print(secrets.token_urlsafe(32))"`. Startup fails closed when a non-loopback address has no configured token.

## Model providers and API keys

Agency sends the API key and request content needed to complete a task to the model provider selected by the user. Review that provider's data-handling terms.

The Web UI can store a key in browser `localStorage`. This is convenient for local use, but an XSS vulnerability could expose it. Environment variables are safer for regular use. Never commit `.env` files, real keys, or credentials.

## Resumable runs

Ordinary new messages do not send an old `run_id`. The UI sends the original task, project, and `run_id` only after the user explicitly clicks **Resume run**.

```json
{
  "task": "add tests to the current project",
  "proj_dir": "/allowed/project",
  "run_id": "optional-existing-run-id"
}
```

Only one runner may own a run at a time. If the process stops after a potentially side-effecting action but before recording its result, Agency requires manual reconciliation. Inspect files, commands, and external state before continuing.

## Security boundary

- The listener defaults to loopback, and remote listening requires authentication.
- Project roots are an enforced allowlist. Path traversal and symlink/junction escapes are rejected.
- Docker-enabled features may provide additional isolation. **Without Docker, commands run with the permissions of the operating-system user that started Agency.**
- This project is not a multi-tenant service and does not claim that every model input or secret always remains on the device.
- Follow [SECURITY.md](SECURITY.md) for private vulnerability reporting. Never put a real secret in a public issue.

## Known limitations

- v0.5.0 is source-only: no PyPI/npm package, binary installer, or hosted SaaS is provided.
- Agency cannot automatically determine whether an interrupted external side effect succeeded. `ACTION_RECONCILIATION_REQUIRED` needs a human decision.
- Browser credential storage remains exposed to browser/XSS risk.
- The Windows junction test skips with an explicit reason when directory-link creation is unavailable.
- The single-machine ledger and token authentication are not an enterprise multi-user authorization system.

## Verification

Release CI exposes these stable check names:

- `Quality`
- `Tests (Python 3.10)`
- `Tests (Python 3.11)`
- `Tests (Python 3.12)`
- `Tests (Python 3.13)`

Run the same core checks locally:

```bash
python -m pip install -e ".[dev]"
ruff check .
python -m compileall -q maestro scripts
python scripts/verify_release.py
python -m pytest -q
```

`scripts/verify_release.py` checks version consistency, the 33/7 registry counts, source-only package settings, and forbidden public-tree content.

## Contributing

Maintenance is best effort; there is no fixed response SLA. Read [CONTRIBUTING.md](CONTRIBUTING.md) and run Ruff, pytest, and the release verifier before opening a pull request.

License: [MIT](LICENSE)
