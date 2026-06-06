#!/usr/bin/env bash
# Agency — PostToolUse hook (auto-format, log)
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
echo "[$(date '+%T')] Tool used" >> "$ROOT/.claude/hooks/post-tool-use.log"
