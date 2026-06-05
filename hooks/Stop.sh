#!/usr/bin/env bash
# Stop.sh — 会话结束时执行
# 清理临时文件、保存会话状态

set -euo pipefail

PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# 清理超过 7 天的临时文件
if [ -d "$PROJECT_ROOT/.claude/tmp" ]; then
    find "$PROJECT_ROOT/.claude/tmp" -type f -mtime +7 -delete 2>/dev/null || true
fi

# 日志轮转（如有超大日志文件）
for logfile in "$PROJECT_ROOT/.claude"/*.log; do
    if [ -f "$logfile" ]; then
        size=$(wc -c < "$logfile" 2>/dev/null || echo 0)
        if [ "$size" -gt 1048576 ]; then  # 1MB
            tail -n 1000 "$logfile" > "${logfile}.tmp" && mv "${logfile}.tmp" "$logfile"
        fi
    fi
done

exit 0
