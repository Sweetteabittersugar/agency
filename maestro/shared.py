"""跨模块共享状态 — 避免 web.py ↔ routes 循环导入"""
import json
import os
import re
import shutil
import logging
from pathlib import Path

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ISOLATED_CONFIG = str(PROJECT_ROOT / ".claude-isolated")
_claude_dir = str(PROJECT_ROOT / ".claude")
_claude_dir_path = Path(_claude_dir)

AGENCY_VERSION = "0.1.0"
_version_file = PROJECT_ROOT / "VERSION"
if _version_file.exists():
    AGENCY_VERSION = _version_file.read_text().strip()

# ── 检测 Claude CLI ──
CLAUDE_BIN = shutil.which("claude")
if not CLAUDE_BIN:
    for p in [os.path.expanduser("~/AppData/Roaming/npm/claude.cmd"),
              os.path.expanduser("~/AppData/Roaming/npm/claude")]:
        if os.path.isfile(p):
            CLAUDE_BIN = p
            break

# ── Agent 列表 ──
from maestro.agent_parser import parse_agent_md


def load_agents():
    """从 agents/ 目录加载 Agent 列表"""
    agents = []
    agents_dir = PROJECT_ROOT / "agents"
    if agents_dir.exists():
        for f in sorted(agents_dir.glob("*.md")):
            info = parse_agent_md(f)
            agents.append({
                "name": info["name"],
                "description": info["description"],
                "model": info["model"],
                "tools": info["tools"],
            })
    return agents


# ── 简单关键词路由 ──
ROUTING_KEYWORDS = {
    "coder": ["写", "改", "重构", "实现", "开发", "代码", "修复", "fix", "bug"],
    "code-reviewer": ["审查", "review", "检查代码", "代码审查"],
    "explorer": ["查", "找", "分析", "定位", "搜索", "grep"],
    "test-runner": ["测试", "验证", "跑测试", "test"],
    "security-reviewer": ["安全", "漏洞", "注入", "密钥"],
    "webnovel-writer": ["小说", "章节", "大纲", "人物", "写作"],
    "planner": ["规划", "设计", "架构", "方案"],
    "general-worker": ["整理", "配置", "杂务", "文件"],
}

_agent_models = {}


def _init_agent_models():
    global _agent_models
    for agent in load_agents():
        if agent.get("model"):
            _agent_models[agent["name"]] = agent["model"]


_init_agent_models()


def simple_route(task):
    """简单关键词匹配"""
    tl = task.lower()
    best, best_score = None, 0
    for name, keywords in ROUTING_KEYWORDS.items():
        score = sum(2 for kw in keywords if kw.lower() in tl)
        if score > best_score:
            best, best_score = name, score
    if best_score < 2:
        return None
    model = _agent_models.get(best, "")
    return {"agent": best, "model": model}


def _extract_plan(text: str):
    """从 orchestrator 输出中提取 JSON 计划"""
    m = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
    if not m:
        m = re.search(r'\{[^{}]*"phases"\s*:\s*\[.*?\]\s*[^{}]*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1) if '```' in text else m.group(0))
        except Exception:
            pass
    return None


def _scan_subagents(proj_root: str, session_id: str) -> list:
    """扫描 session 下的子 Agent"""
    home = Path.home()
    slug = proj_root.replace("\\", "/").rstrip("/").replace(":/", "--").replace("/", "-").lstrip("-")
    subs_dir = home / ".claude" / "projects" / slug / session_id / "subagents"
    if not subs_dir.exists():
        return []
    agents = []
    for meta_file in sorted(subs_dir.glob("*.meta.json")):
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            agent_id = meta_file.stem.replace(".meta", "")
            jsonl_file = subs_dir / f"{agent_id}.jsonl"
            has_output = jsonl_file.exists() and jsonl_file.stat().st_size > 100
            agents.append({
                "id": agent_id,
                "name": meta.get("name", agent_id[:12]),
                "type": meta.get("agentType", ""),
                "description": (meta.get("description", "") or "")[:120],
                "hasOutput": has_output,
                "project": Path(proj_root).name,
            })
        except Exception:
            log.debug(f"Subagent scan failed for {proj_root}", exc_info=True)
    return agents


# ── API Provider 映射（chat / orchestrate 共用）──
PROVIDER_MAP = {
    "deepseek": {
        "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-v4-pro",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek-v4-flash",
        "ANTHROPIC_MODEL": "deepseek-v4-pro",
    },
    "anthropic": {},
    "openai": {"ANTHROPIC_BASE_URL": "https://api.openai.com/v1"},
}


def build_isolated_env(api_key, api_provider="deepseek"):
    """返回含 API key 注入的隔离环境变量"""
    import os
    iso_env = os.environ.copy()
    iso_env["CLAUDE_CODE_CONFIG_DIR"] = ISOLATED_CONFIG
    if api_key:
        iso_env["ANTHROPIC_AUTH_TOKEN"] = api_key
        for k, v in PROVIDER_MAP.get(api_provider, PROVIDER_MAP["deepseek"]).items():
            iso_env[k] = v
    return iso_env
