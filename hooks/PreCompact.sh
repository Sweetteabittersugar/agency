#!/usr/bin/env bash
# PreCompact.sh — 上下文压缩前执行
# 在压缩前保存关键信息到记忆文件

set -euo pipefail

MEMORY_DIR="${CLAUDE_PROJECT_DIR:-.}/.claude/memory"
mkdir -p "$MEMORY_DIR"

# 记录压缩时间
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) compact" >> "$MEMORY_DIR/.compact-log"

# 在此添加需要在压缩前保存的自定义逻辑
# 例如：保存当前任务状态、未完成的决策等

exit 0
