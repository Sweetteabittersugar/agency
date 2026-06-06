#!/usr/bin/env bash
# Agency — SessionStart hook
set -eu
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Session started (root: $ROOT)" >> "$ROOT/.claude/hooks/session-start.log"
