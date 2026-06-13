"""集中配置 — 所有硬编码常量的单一来源"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# --- 服务器 ---
PORT: int = int(os.environ.get("AGENCY_PORT", "8800"))
BIND_ADDR: str = os.environ.get("AGENCY_HOST", "127.0.0.1")

# --- 安全 ---
RATE_LIMIT_PER_MINUTE: int = int(os.environ.get("AGENCY_RATE_LIMIT", "60"))
MAX_INPUT_LENGTH: int = int(os.environ.get("AGENCY_MAX_INPUT", "32000"))
TRUST_MODES: list[str] = ["cautious", "normal", "trusted"]
DEFAULT_TRUST_MODE: str = "normal"

# --- 路由 ---
CONFIDENCE_HIGH: float = float(os.environ.get("AGENCY_ROUTE_CONFIDENCE_HIGH", "0.7"))
CONFIDENCE_MEDIUM: float = float(os.environ.get("AGENCY_ROUTE_CONFIDENCE_MEDIUM", "0.4"))
SEMANTIC_THRESHOLD: float = float(os.environ.get("AGENCY_SEMANTIC_THRESHOLD", "0.15"))

# --- 进程池 ---
POOL_MAX_WORKERS: int = int(os.environ.get("AGENCY_POOL_WORKERS", "4"))
POOL_FAILURE_THRESHOLD: int = int(os.environ.get("AGENCY_POOL_FAILURE_THRESHOLD", "3"))

# --- 会话 ---
SESSION_SNAPSHOT_THRESHOLD: int = (
    int(os.environ.get("AGENCY_SESSION_SNAPSHOT_MB", "2")) * 1024 * 1024
)

# --- 费用 ---
DEFAULT_TOKEN_LIMIT: int = int(os.environ.get("AGENCY_TOKEN_LIMIT", "100000"))
DEFAULT_DAILY_BUDGET: float = float(os.environ.get("AGENCY_DAILY_BUDGET", "5.0"))

# --- 日志 ---
LOG_FILE: Path = PROJECT_ROOT / "maestro" / "agency.log"
LOG_MAX_BYTES: int = 10 * 1024 * 1024

# --- 路径 ---
AGENTS_DIR: Path = PROJECT_ROOT / ".claude" / "agents"
SKILLS_DIR: Path = PROJECT_ROOT / ".claude" / "skills"
SESSIONS_DIR: Path = PROJECT_ROOT / "maestro" / "sessions"
CREDENTIALS_DIR: Path = PROJECT_ROOT / "credentials"
WORKTREE_DIR: Path = PROJECT_ROOT / "maestro" / "worktrees"
