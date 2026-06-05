#!/usr/bin/env bash
# SessionStart.sh
# Layer 3: Guardrail Layer — 会话启动钩子
# 在每次 Claude Code 会话启动时执行

set -euo pipefail

# 项目根目录：优先使用 Claude Code 注入的环境变量，否则用当前目录
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
LOG_FILE="$PROJECT_ROOT/.claude/hooks/session-start.log"

# === 日志 ===
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log "=== Session started ==="

# === 环境检查 ===

# Python 可用性
if powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "python --version" 2>/dev/null; then
    log "Python: OK"
else
    log "Python: NOT FOUND"
fi

# Ollama 可用性（不阻塞，仅记录）
if curl -s --connect-timeout 3 http://localhost:11434/api/tags > /dev/null 2>&1; then
    log "Ollama: OK"
else
    log "Ollama: not running (non-blocking)"
fi

# 项目根目录
if [ -d "$PROJECT_ROOT" ]; then
    log "Project root: OK ($PROJECT_ROOT)"
else
    log "Project root: MISSING ($PROJECT_ROOT)"
fi

# === 扩展点 ===
# 在此添加你的项目特定启动逻辑：
# 1. 检查数据库/缓存服务是否在线
# 2. 启动本地开发服务器
# 3. 加载环境变量（如 .env 文件）
# 4. 清理临时文件
# 5. 同步远程配置

log "=== Session start complete ==="
