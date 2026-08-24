"""跨模块共享状态 — 避免 web.py ↔ routes 循环导入

保留核心常量（项目路径 / CLI / 版本 / Profile ）以及
来自新拆分模块的兼容性 re-export。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# ── 项目路径 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_claude_dir = str(PROJECT_ROOT / ".claude")
_claude_dir_path = Path(_claude_dir)

# ── Profile 系统引入 ──
try:
    from maestro.profiles import (
        load_profile,
        estimate_complexity,
        filter_agents_for_profile,
        filter_skills_for_profile,
        get_agent_profile_skills,
        _load_yaml_skills,
    )

    _HAS_PROFILES = True
except ImportError:
    _HAS_PROFILES = False
    log.warning("maestro.profiles 未找到，Profile 系统不可用")

# ── 版本 ──
AGENCY_VERSION = "0.5.0"
_version_file = PROJECT_ROOT / "VERSION"
if _version_file.exists():
    AGENCY_VERSION = _version_file.read_text().strip()


def check_for_updates() -> str | None:
    """启动时检查更新（后台静默，缓存 24 小时）。"""
    try:
        from maestro.version_check import check_version

        return check_version()
    except Exception:
        return None


# ── 检测 Claude CLI ──
CLAUDE_BIN = shutil.which("claude")
if not CLAUDE_BIN:
    for p in [
        os.path.expanduser("~/AppData/Roaming/npm/claude.cmd"),
        os.path.expanduser("~/AppData/Roaming/npm/claude"),
    ]:
        if os.path.isfile(p):
            CLAUDE_BIN = p
            break

# ── Agent 模型缓存 ──
_agent_models = {}


def _init_agent_models():
    global _agent_models
    from maestro.agent_loader import load_agents

    for agent in load_agents():
        if agent.get("model"):
            _agent_models[agent["name"]] = agent["model"]


_init_agent_models()


from maestro.models import PROVIDER_MAP, PROVIDER_PRESETS  # noqa: E402, F401

# ════════════════════════════════════════════════════════════
# 兼容性 re-export — 让旧 import 路径继续工作
# 新代码请直接从对应模块导入
# ════════════════════════════════════════════════════════════

from maestro.routing_keywords import ROUTING_KEYWORDS  # noqa: E402, F401
from maestro.task_classifier import (  # noqa: E402, F401
    classify_task_complexity,
    _extract_plan,
    _scan_subagents,
)
from maestro.agent_loader import (  # noqa: E402, F401
    load_agents,
    load_skill_bindings,
    get_agent_skills,
    _agent_skills_binding,
)
from maestro.app_config import (  # noqa: E402, F401
    build_isolated_env,
    ISOLATED_CONFIG,
)
