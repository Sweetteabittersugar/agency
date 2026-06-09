"""Profile 加载 + 任务复杂度估算

与 orchestrator 集成：分配 Agent 前调用 estimate_complexity() 选 profile，
按 profile 过滤可用 Agent 和 Skill。
"""
import json
import logging
from pathlib import Path
from typing import Dict, Optional

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROFILES_PATH = PROJECT_ROOT / "profiles.json"
AGENT_YAML_PATH = PROJECT_ROOT / "agent.yaml"

# 写入操作关键词（用于检测是否需要写权限）
_WRITE_KEYWORDS = [
    "写", "改", "创建", "新建", "生成", "删除", "修改", "编辑",
    "重构", "实现", "开发", "修复", "更新", "添加", "移除",
    "write", "create", "delete", "edit", "update", "fix",
    "refactor", "implement", "generate", "remove", "add",
]

# 多文件操作关键词
_MULTI_FILE_KEYWORDS = [
    "多个", "批量", "全部", "整套", "整个项目", "完整",
    "协调", "编排", "调度", "架构", "重构", "迁移",
    "all", "batch", "multiple", "orchestrate", "pipeline",
    "architecture", "refactor", "migrate",
]

# 小型修复关键词 → 覆盖为 minimal
_SIMPLE_WRITE_KEYWORDS = [
    "简单", "小修", "改一行", "修改一行", "小改",
    "简单修复", "小bug", "minor", "trivial",
    "修typo", "改注释", "加个注释", "补文档",
]

# 复杂操作关键词 → 推定 full
_COMPLEX_KEYWORDS = [
    "架构重构", "多Agent", "DAG", "管线", "pipeline",
    "整套的", "全栈", "端到端", "e2e",
    "安全审计", "全面扫描", "微服务", "拆分为",
]


def _load_yaml_skills(agent_yaml_path: Optional[Path] = None) -> Dict:
    """从 agent.yaml / agents.json 加载 agent-skill 绑定。

    优先从 agent.yaml 读取，若不存在则从 agents.json 读取。
    """
    import yaml

    path = agent_yaml_path or AGENT_YAML_PATH
    if not path.exists():
        log.warning("agent.yaml not found at %s", path)
        return {}

    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception as exc:
        log.error("Failed to load agent.yaml: %s", exc)
        return {}

    skills_binding = {}
    agents = data.get("agents", {})
    for agent_name, agent_def in agents.items():
        if isinstance(agent_def, dict) and "skills" in agent_def:
            skills_binding[agent_name] = agent_def["skills"]
    return skills_binding


def load_profile(task_complexity: str) -> Dict:
    """根据复杂度返回对应 profile 配置。

    Args:
        task_complexity: "minimal" | "standard" | "full"

    Returns:
        {"max_tokens": int, "agents": list, "skills": list, "hooks": list, ...}
    """
    if not PROFILES_PATH.exists():
        log.warning("profiles.json not found, using built-in defaults")
        return _default_profile(task_complexity)

    try:
        data = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError) as exc:
        log.error("Failed to load profiles.json: %s", exc)
        return _default_profile(task_complexity)

    profiles = data.get("profiles", {})
    if task_complexity not in profiles:
        log.warning(
            "Unknown complexity '%s', falling back to standard", task_complexity
        )
        return profiles.get("standard", _default_profile("standard"))

    return profiles[task_complexity]


def estimate_complexity(task: str) -> str:
    r"""根据任务描述估算复杂度级别。

    规则：
    - 含架构/多Agent/DAG/管线关键词 → full
    - 含3+文件操作关键词 或 含写+多文件关键词 → standard
    - 含文件路径计数 ≥ 3 → standard
    - 纯读/查/单文件 → minimal

    Args:
        task: 任务描述文本

    Returns:
        "minimal" | "standard" | "full"
    """
    if not task or not task.strip():
        return "minimal"

    task_lower = task.lower()

    # 1. 复杂关键词 → full
    full_score = sum(1 for kw in _COMPLEX_KEYWORDS if kw in task_lower)
    if full_score >= 1:
        return "full"

    # 2. 估算涉及文件数（通过路径模式匹配）
    path_patterns = [
        r"(?:[A-Za-z]:[/\\]|/)[^\s,;，；]+",
        r"\b\w+\.\w+\b",
    ]
    import re

    max_paths = 0
    for pat in path_patterns:
        paths = re.findall(pat, task)
        max_paths = max(max_paths, len(paths))

    # 3. 写操作检测
    has_write = any(kw in task_lower for kw in _WRITE_KEYWORDS)

    # 4. 多文件/批量关键词
    multi_score = sum(1 for kw in _MULTI_FILE_KEYWORDS if kw in task_lower)

    # 5. 步骤数估算（基于常见分隔词）
    step_patterns = [
        r"(?:步骤?\s*\d+|第[一二三四五六七八九十]步|首先|然后|接着|最后|1\.[\s])",
        r"\n\s*[-*+]\s",
        r"\bstep\s*\d+\b",
    ]
    step_count = 0
    for pat in step_patterns:
        step_count += len(re.findall(pat, task, re.IGNORECASE))

    # 6. 简单修复检测（覆盖写操作为 minimal）
    has_simple = any(kw in task_lower for kw in _SIMPLE_WRITE_KEYWORDS)

    # ── 综合判断 ──
    if multi_score >= 2:
        return "full"
    if multi_score >= 1 or max_paths >= 3 or (has_write and step_count >= 3):
        return "standard"
    # 有写操作但明确是简单修复 → minimal
    if has_write and has_simple and max_paths <= 1 and step_count <= 1:
        return "minimal"
    if has_write or max_paths >= 2 or step_count >= 2:
        return "standard"
    return "minimal"


def filter_agents_for_profile(agents: list, profile: Dict) -> list:
    """按 profile 的 agents 白名单过滤可用 Agent。

    - "领域全组" → 返回所有 agents
    - "协调层 + 领域全组" → 返回所有 agents
    - 具体 agent 名列表 → 只返回列表中的 agent

    Args:
        agents: 全部可用 agent 列表 (每个 agent 含 name 字段)
        profile: load_profile() 返回值

    Returns:
        过滤后的 agent 列表
    """
    allowed = profile.get("agents", [])
    if not allowed:
        return agents

    # 全组标记 → 不过滤
    if "领域全组" in allowed or "协调层 + 领域全组" in allowed:
        return agents

    filtered = [a for a in agents if a.get("name", "") in allowed]
    return filtered or agents  # fallback: 至少返回一个


def filter_skills_for_profile(skills: list, profile: Dict) -> list:
    """按 profile 的 skills 设置过滤可用 Skill。

    - "全部匹配" → 返回所有 skills
    - "按需匹配" → 返回所有（触发由关键词决定）
    - 具体 skill 名列表 → 只返回列表中的 skill

    Args:
        skills: 全部可用 skill 列表
        profile: load_profile() 返回值

    Returns:
        过滤后的 skill 列表
    """
    allowed = profile.get("skills", [])
    if not allowed:
        return []
    if "全部匹配" in allowed or "按需匹配" in allowed:
        return skills
    return [s for s in skills if s.get("name", "") in allowed]


def get_agent_profile_skills(agent_name: str) -> Dict:
    """获取特定 Agent 的 Skill 绑定配置。

    Returns:
        {
            "required": ["self-healing"],
            "optional": ["pre-commit-guard", "context-budget"],
            "excluded": []
        }
    """
    bindings = _load_yaml_skills()
    return bindings.get(agent_name, {
        "required": [],
        "optional": [],
        "excluded": [],
    })


def _default_profile(complexity: str) -> Dict:
    """内置默认 profile（当 profiles.json 不可用时）。"""
    defaults = {
        "minimal": {
            "max_tokens": 3000,
            "agents": ["router"],
            "skills": [],
            "hooks": ["SessionStart"],
            "trigger": "单文件读写、grep搜索、状态查询、简单编辑",
            "conditions": {"max_files": 1, "max_steps": 1, "allow_write": False},
        },
        "standard": {
            "max_tokens": 8000,
            "agents": ["领域全组"],
            "skills": ["按需匹配"],
            "hooks": ["SessionStart", "SubagentStop"],
            "trigger": "多文件修改、代码生成、测试编写",
            "conditions": {"max_files": 5, "max_steps": 5, "allow_write": True},
        },
        "full": {
            "max_tokens": 20000,
            "agents": ["协调层 + 领域全组"],
            "skills": ["全部匹配"],
            "hooks": ["全部"],
            "trigger": "架构重构、DAG协调、多Agent协作",
            "conditions": {"max_files": 999, "max_steps": 999, "allow_write": True},
        },
    }
    return defaults.get(complexity, defaults["standard"])
