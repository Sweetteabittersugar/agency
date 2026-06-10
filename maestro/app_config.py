"""集中配置 — 所有硬编码常量的单一来源"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- 服务器 ---
PORT = int(os.environ.get("AGENCY_PORT", "8800"))
BIND_ADDR = os.environ.get("AGENCY_HOST", "127.0.0.1")

# --- 安全 ---
RATE_LIMIT_PER_MINUTE = int(os.environ.get("AGENCY_RATE_LIMIT", "60"))
MAX_INPUT_LENGTH = int(os.environ.get("AGENCY_MAX_INPUT", "32000"))
TRUST_MODES = ["cautious", "normal", "trusted"]
DEFAULT_TRUST_MODE = "normal"

# --- 路由 ---
CONFIDENCE_HIGH = float(os.environ.get("AGENCY_ROUTE_CONFIDENCE_HIGH", "0.7"))
CONFIDENCE_MEDIUM = float(os.environ.get("AGENCY_ROUTE_CONFIDENCE_MEDIUM", "0.4"))
SEMANTIC_THRESHOLD = float(os.environ.get("AGENCY_SEMANTIC_THRESHOLD", "0.6"))

# --- 进程池 ---
POOL_MAX_WORKERS = int(os.environ.get("AGENCY_POOL_WORKERS", "4"))
POOL_FAILURE_THRESHOLD = int(os.environ.get("AGENCY_POOL_FAILURE_THRESHOLD", "3"))

# --- 会话 ---
SESSION_SNAPSHOT_THRESHOLD = int(os.environ.get("AGENCY_SESSION_SNAPSHOT_MB", "2")) * 1024 * 1024

# --- 费用 ---
DEFAULT_TOKEN_LIMIT = int(os.environ.get("AGENCY_TOKEN_LIMIT", "100000"))
DEFAULT_DAILY_BUDGET = float(os.environ.get("AGENCY_DAILY_BUDGET", "5.0"))

# --- 日志 ---
LOG_FILE = PROJECT_ROOT / "maestro" / "agency.log"
LOG_MAX_BYTES = 10 * 1024 * 1024

# --- 路径 ---
AGENTS_DIR = PROJECT_ROOT / ".claude" / "agents"
SKILLS_DIR = PROJECT_ROOT / ".claude" / "skills"
SESSIONS_DIR = PROJECT_ROOT / "maestro" / "sessions"
CREDENTIALS_DIR = PROJECT_ROOT / "credentials"
WORKTREE_DIR = PROJECT_ROOT / "maestro" / "worktrees"
