#!/usr/bin/env bash
# PostToolUse.sh
# Layer 3: Guardrail Layer — 工具执行后通知/记录/清理
# 可用于部署通知、操作日志

set -euo pipefail

# 项目根目录：优先使用 Claude Code 注入的环境变量，否则用当前目录
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
LOG_FILE="$PROJECT_ROOT/.claude/hooks/post-tool-use.log"

# 从环境变量获取工具信息（由 Claude Code 注入）
TOOL_NAME="${CLAUDE_TOOL_NAME:-unknown}"
TOOL_EXIT_CODE="${CLAUDE_TOOL_EXIT_CODE:-0}"

# === 日志 ===
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] TOOL=$TOOL_NAME EXIT=$TOOL_EXIT_CODE | $1" >> "$LOG_FILE"
}

# === 主逻辑 ===
log "Post-tool hook fired"

# === 日志轮转 ===
# 日志文件超过 1MB 时自动截断，保留最后 1000 行
rotate_log_if_needed() {
    local log_path="$1"
    local max_size=$((1 * 1024 * 1024))  # 1MB
    local keep_lines=1000

    if [ -f "$log_path" ]; then
        local size
        size=$(wc -c < "$log_path" 2>/dev/null || echo 0)
        if [ "$size" -gt "$max_size" ]; then
            tail -n "$keep_lines" "$log_path" > "${log_path}.tmp" && \
                mv "${log_path}.tmp" "$log_path"
            log "Log rotated (was ${size} bytes, kept last ${keep_lines} lines)"
        fi
    fi
}

rotate_log_if_needed "$LOG_FILE"

# === 扩展点 ===
# 未来可以在此添加：
# 1. 文件修改后自动索引
# 2. git commit 后自动 push（需谨慎）
# 3. 部署通知（webhook）
# 4. 关键操作审计日志

exit 0
