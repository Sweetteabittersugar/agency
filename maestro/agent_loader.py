"""Agent 加载器 — 从 agents/ 目录 + Agent-Skill 绑定加载 Agent 列表

职责：
- load_agent_skills_binding: 从 profiles 或 agents.json 加载技能绑定
- get_agent_skills: 查询单个 Agent 的 Skill 绑定
- load_agents: 扫描 agents/ 目录，组装 Agent 元数据
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Profile 系统引入 ──
try:
    from maestro.profiles import (
        load_profile,
        filter_agents_for_profile,
        _load_yaml_skills,
    )

    _HAS_PROFILES = True
except ImportError:
    _HAS_PROFILES = False
    log.warning("maestro.profiles 未找到，Profile 系统不可用")

from maestro.agent_parser import parse_agent_md

# ── Agent-Skill 绑定缓存 ──
_agent_skills_binding: dict = {}


def load_skill_bindings() -> dict:
    """从 agent.yaml 加载 Agent-Skill 绑定，返回 {agent_name: {required, optional, excluded}}"""
    global _agent_skills_binding
    if _agent_skills_binding:
        return _agent_skills_binding

    if _HAS_PROFILES:
        _agent_skills_binding = _load_yaml_skills()
    if not _agent_skills_binding:
        # fallback: 从 agents.json 读取
        agents_json = PROJECT_ROOT / "maestro" / "agents.json"
        if agents_json.exists():
            try:
                data = json.loads(agents_json.read_text(encoding="utf-8"))
                for agent_name, agent_def in data.items():
                    if isinstance(agent_def, dict) and "skills" in agent_def:
                        _agent_skills_binding[agent_name] = agent_def["skills"]
            except Exception as exc:
                log.debug("Failed to load skill bindings from agents.json: %s", exc)

    return _agent_skills_binding


def get_agent_skills(agent_name: str) -> dict:
    """获取指定 Agent 的 Skill 绑定。"""
    bindings = load_skill_bindings()
    return bindings.get(agent_name, {"required": [], "optional": [], "excluded": []})


def load_agents(profile_complexity: str | None = None) -> list[dict]:
    """从 agents/ 目录加载 Agent 列表，可选按 profile 过滤。

    Args:
        profile_complexity: "minimal"|"standard"|"full"|None。None 时不按 profile 过滤。
    """
    agents = []
    agents_dir = PROJECT_ROOT / "agents"
    if agents_dir.exists():
        for f in sorted(agents_dir.glob("**/*.md")):
            info = parse_agent_md(f)
            agent_name = info["name"]
            skill_binding = get_agent_skills(agent_name)
            agents.append(
                {
                    "name": agent_name,
                    "description": info["description"],
                    "model": info["model"],
                    "tools": info["tools"],
                    "skills": skill_binding,
                }
            )

    # Profile 过滤
    if profile_complexity and _HAS_PROFILES:
        profile = load_profile(profile_complexity)
        agents = filter_agents_for_profile(agents, profile)

    return agents
