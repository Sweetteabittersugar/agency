"""集中配置 — 所有硬编码常量的单一来源

提供：
- ISOLATED_CONFIG: .claude-isolated 目录路径
- build_isolated_env: 构建含 API Key 注入的隔离环境变量字典
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from maestro.models import PROVIDER_MAP

logger = logging.getLogger(__name__)

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
ISOLATED_CONFIG: str = str(PROJECT_ROOT / ".claude-isolated")


def _env_int(key: str, default: int) -> int:
    """读取环境变量并转为 int，失败时降级为默认值并记录警告。"""
    val = os.environ.get(key)
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        logger.warning("Invalid int for env %r (%r), falling back to %r", key, val, default)
        return default


def _env_float(key: str, default: float) -> float:
    """读取环境变量并转为 float，失败时降级为默认值并记录警告。"""
    val = os.environ.get(key)
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        logger.warning("Invalid float for env %r (%r), falling back to %r", key, val, default)
        return default


# --- 服务器 ---
PORT: int = _env_int("AGENCY_PORT", 8800)
BIND_ADDR: str = os.environ.get("AGENCY_HOST", "127.0.0.1")

# --- 安全 ---
RATE_LIMIT_PER_MINUTE: int = _env_int("AGENCY_RATE_LIMIT", 60)
MAX_INPUT_LENGTH: int = _env_int("AGENCY_MAX_INPUT", 32000)
TRUST_MODES: list[str] = ["cautious", "normal", "trusted"]
DEFAULT_TRUST_MODE: str = "normal"

# --- 路由 ---
CONFIDENCE_HIGH: float = _env_float("AGENCY_ROUTE_CONFIDENCE_HIGH", 0.7)
CONFIDENCE_MEDIUM: float = _env_float("AGENCY_ROUTE_CONFIDENCE_MEDIUM", 0.4)
SEMANTIC_THRESHOLD: float = _env_float("AGENCY_SEMANTIC_THRESHOLD", 0.15)

# --- 进程池 ---
POOL_MAX_WORKERS: int = _env_int("AGENCY_POOL_WORKERS", 4)
POOL_FAILURE_THRESHOLD: int = _env_int("AGENCY_POOL_FAILURE_THRESHOLD", 3)

# --- 会话 ---
SESSION_SNAPSHOT_THRESHOLD: int = (
    _env_int("AGENCY_SESSION_SNAPSHOT_MB", 2) * 1024 * 1024
)

# --- 费用 ---
DEFAULT_TOKEN_LIMIT: int = _env_int("AGENCY_TOKEN_LIMIT", 100000)
DEFAULT_DAILY_BUDGET: float = _env_float("AGENCY_DAILY_BUDGET", 5.0)

# --- 日志 ---
LOG_FILE: Path = PROJECT_ROOT / "maestro" / "agency.log"
LOG_MAX_BYTES: int = 10 * 1024 * 1024

# --- 路径 ---
AGENTS_DIR: Path = PROJECT_ROOT / ".claude" / "agents"
SKILLS_DIR: Path = PROJECT_ROOT / ".claude" / "skills"
SESSIONS_DIR: Path = PROJECT_ROOT / "maestro" / "sessions"
CREDENTIALS_DIR: Path = PROJECT_ROOT / "credentials"
WORKTREE_DIR: Path = PROJECT_ROOT / "maestro" / "worktrees"
STATE_DIR: Path = Path(os.environ.get("AGENCY_STATE_DIR", Path.home() / ".agency")).expanduser()
RUN_LEDGER_PATH: Path = STATE_DIR / "runs.sqlite3"
RUN_ARTIFACTS_DIR: Path = STATE_DIR / "run-artifacts"


def build_isolated_env(api_key: str | None, api_provider: str = "deepseek") -> dict[str, str]:
    """返回含 API key 注入的隔离环境变量"""
    iso_env = os.environ.copy()
    iso_env["CLAUDE_CODE_CONFIG_DIR"] = ISOLATED_CONFIG
    if api_key:
        iso_env["ANTHROPIC_AUTH_TOKEN"] = api_key
        for k, v in PROVIDER_MAP.get(api_provider, PROVIDER_MAP["deepseek"]).items():
            iso_env[k] = v
    return iso_env
