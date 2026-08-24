#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
echo "Agency v0.5.0 — source-only local install"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install -e .
echo "Installed. Start with:"
echo "  .venv/bin/agency start --project-root /path/to/project"
