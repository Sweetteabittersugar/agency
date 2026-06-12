"""跨模块共享状态 — 避免 web.py ↔ routes 循环导入"""
from __future__ import annotations

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

# ── Agent-Skill 绑定缓存 ──
_agent_skills_binding: dict = {}

AGENCY_VERSION = "0.1.0"
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
    for p in [os.path.expanduser("~/AppData/Roaming/npm/claude.cmd"),
              os.path.expanduser("~/AppData/Roaming/npm/claude")]:
        if os.path.isfile(p):
            CLAUDE_BIN = p
            break

# ── Agent 列表 ──
from maestro.agent_parser import parse_agent_md


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
            agents.append({
                "name": agent_name,
                "description": info["description"],
                "model": info["model"],
                "tools": info["tools"],
                "skills": skill_binding,
            })

    # Profile 过滤
    if profile_complexity and _HAS_PROFILES:
        profile = load_profile(profile_complexity)
        agents = filter_agents_for_profile(agents, profile)

    return agents


# ── 简单关键词路由 ──
ROUTING_KEYWORDS = {
    "coder": [
        ("写代码", 10), ("实现功能", 9), ("开发功能", 9), ("修复bug", 9),
        ("改代码", 8), ("编程", 8), ("fix", 8),
        ("重构", 6), ("bug", 6), ("代码", 6), ("写", 4), ("改", 3),
        ("开发", 7), ("实现", 5), ("编写", 7), ("修改", 5),
        ("构建", 6), ("编译", 6), ("build", 6),
        ("死代码", 7), ("清理代码", 7), ("简化代码", 6),
        ("构建失败", 10), ("编译错误", 10),
        ("报错", 4), ("修复", 6),
        ("函数", 7), ("类", 7), ("模块", 7), ("接口", 8), ("api", 8),
        ("后端", 7), ("脚本", 7), ("算法", 7), ("写一个", 9), ("改一下", 8),
        ("修bug", 10), ("程序", 7), ("加个功能", 9), ("新建文件", 8),
        ("改函数", 8), ("删掉", 6), ("重复", 6), ("精简", 6),
    ],
    "code-reviewer": [
        ("审查代码", 10), ("代码审查", 10), ("审查", 10), ("review", 9),
        ("检查代码", 9), ("代码检查", 9), ("code review", 10),
        ("审阅", 8), ("复查", 8), ("检查一下", 7),
    ],
    "explorer": [
        ("查", 9), ("找", 8), ("分析", 7), ("定位", 8), ("搜索", 9),
        ("grep", 8), ("探索", 8), ("搜", 9), ("在哪", 8),
        ("哪些文件", 9), ("找一下", 8), ("看看哪里", 8), ("找找看", 7),
        ("搜一下", 8), ("哪里有", 7), ("查一下", 7), ("过一遍", 6),
        ("排查", 7), ("追溯", 7),
    ],
    "test-runner": [
        ("跑测试", 10), ("测试策略", 9), ("边界用例", 8), ("回归测试", 9),
        ("测试", 8), ("验证", 5), ("test", 7), ("跑一下", 6),
        ("通过没", 7), ("单元测试", 9), ("集成测试", 8), ("测试用例", 8),
        ("跑一遍", 7), ("验证一下", 7), ("质量保证", 7), ("测试计划", 8),
    ],
    "security-reviewer": [
        ("安全", 10), ("漏洞", 10), ("注入", 9), ("密钥", 9), ("扫描", 7),
        ("审计安全", 9), ("审计", 8), ("xss", 10), ("csrf", 9),
        ("加密", 8), ("安全隐患", 10), ("安全检查", 9),
        ("安全审查", 10), ("sql注入", 10),
    ],
    "webnovel-writer": [
        ("写小说", 10), ("写一篇小说", 10), ("小说", 9), ("网文", 10),
        ("章节", 9), ("大纲", 8), ("人物", 8), ("写作", 9), ("故事", 9),
        ("世界观", 8), ("写故事", 10), ("情节", 8), ("角色", 8), ("续写", 8),
    ],
    "planner": [
        ("规划", 9), ("设计", 8), ("架构", 10), ("方案", 8), ("计划", 7),
        ("怎么实现", 8), ("技术选型", 10), ("系统设计", 10),
        ("设计方案", 9), ("整体设计", 9), ("架构设计", 10),
        ("规划一下", 8), ("设计一下", 7),
    ],
    # general-worker 不参与自动路由，只能通过 @general-worker 指定或总调度调用
    # 保留关键词仅用于 @指定 时的匹配
    "python-reviewer": [
        ("python", 10), ("py", 8), ("pip", 7), ("django", 10),
        ("flask", 9), ("fastapi", 10), ("python代码", 9),
        ("py文件", 8), ("python项目", 9), ("pytest", 8),
    ],
    "go-reviewer": [
        ("go", 10), ("golang", 10), ("go mod", 8), ("goroutine", 9),
        ("channel", 8), ("go代码", 9), ("go项目", 8), ("go语言", 8),
    ],
    "typescript-reviewer": [
        ("ts", 9), ("typescript", 10), ("js", 8), ("javascript", 9),
        ("react", 10), ("vue", 8), ("node", 8), ("npm", 7),
        ("前端", 9), ("tsx", 8), ("jsx", 8), ("组件", 8), ("node.js", 8),
    ],
    "database-reviewer": [
        ("sql", 10), ("数据库", 10), ("mysql", 9), ("postgres", 9),
        ("sqlite", 8), ("mongodb", 8), ("orm", 8),
        ("schema", 9), ("索引", 9), ("查询", 8), ("慢查询", 9),
        ("表结构", 9), ("建表", 9),
    ],
    "performance-optimizer": [
        ("性能", 10), ("优化", 9), ("加速", 8), ("慢", 7), ("卡", 6),
        ("性能问题", 10), ("profiling", 7), ("瓶颈", 8),
        ("内存", 7), ("cpu", 7), ("性能优化", 10), ("提速", 8),
        ("快一点", 6), ("太慢", 7),
    ],
    "devops": [
        ("部署", 10), ("docker", 10), ("k8s", 9), ("ci", 8), ("cd", 8),
        ("容器", 8), ("镜像", 8), ("流水线", 8), ("ci/cd", 10),
        ("环境配置", 9), ("devops", 10), ("运维", 9),
        ("容器化", 9), ("dockerfile", 9), ("kubernetes", 9), ("上线", 8),
        ("编排", 7),
    ],
    "doc-updater": [
        ("更新文档", 10), ("写文档", 10), ("文档更新", 10),
        ("api文档", 10), ("readme", 9), ("文档", 4),
        ("接口文档", 10), ("补文档", 9), ("changelog", 8),
        ("更新readme", 9),
    ],
    "build-error-resolver": [
        ("构建", 10), ("编译", 10), ("build", 8), ("编译错误", 10),
        ("构建失败", 10), ("报错", 7),
        ("构建错误", 10), ("编译失败", 10), ("build error", 8),
        ("装不上", 8), ("编译报错", 10), ("装不了", 7),
    ],
    "e2e-runner": [
        ("e2e", 10), ("端到端", 10), ("浏览器测试", 9), ("playwright", 10),
        ("界面测试", 8), ("端到端测试", 10), ("e2e测试", 10),
    ],
    "cost-analyst": [
        ("费用", 10), ("用量", 9), ("成本", 10), ("花费", 9), ("账单", 8),
        ("花了多少", 9), ("费用统计", 9), ("成本分析", 9),
    ],
    "tdd-guide": [
        ("tdd", 10), ("测试驱动", 10), ("先写测试", 9),
        ("测试驱动开发", 10),
    ],
    "orchestrator": [
        ("完整项目", 9), ("做一个", 6), ("整个项目", 10),
        ("搭一个", 7), ("多个任务", 8), ("调度", 7),
        ("编排", 7), ("多agent", 9), ("复杂任务", 8),
        ("拆解", 10), ("分配", 9), ("协作", 9),
        ("全部", 7), ("整套", 8),
        ("全部完成", 9), ("统筹", 9), ("全流程", 9),
        ("所有任务", 9),
    ],
    "ceo": [
        ("产品", 10), ("需求", 9), ("优先级", 9), ("用户故事", 10),
        ("验收标准", 9), ("功能范围", 8), ("需求分析", 10),
        ("产品需求", 9), ("功能需求", 9), ("prd", 8),
    ],
    "release-manager": [
        ("发布", 10), ("版本", 9), ("changelog", 8), ("tag", 7),
        ("release", 9), ("回滚", 8), ("semver", 7),
        ("发版", 9), ("版本号", 8), ("发布管理", 9), ("发布检查", 9),
        ("release note", 8), ("发布说明", 8),
    ],
    "lead": [
        ("委派", 10), ("领导", 9), ("异步", 8), ("后台执行", 9),
        ("大任务", 9), ("lead", 10), ("异步任务", 9),
        ("后台任务", 8), ("委派任务", 9), ("领导任务", 9),
    ],
    "architect": [
        ("系统设计", 10), ("架构设计", 10), ("技术选型", 10), ("接口设计", 9),
        ("模块划分", 9), ("架构方案", 10), ("设计文档", 8),
        ("系统架构", 10), ("设计系统", 10), ("整体设计", 9),
    ],
    "debugger": [
        ("排查bug", 10), ("排查这个", 10), ("调试", 9), ("debug", 9),
        ("定位问题", 9), ("错误分析", 10), ("堆栈跟踪", 10),
        ("根因分析", 10), ("报错排查", 9), ("崩溃分析", 10),
        ("排查", 10), ("调bug", 10),
    ],
    "verifier": [
        ("验证改动", 10), ("检查修复", 10), ("确认修复", 9),
        ("改动验证", 10), ("回归检查", 9), ("验证修复", 10),
        ("是否修复", 9), ("验证一下", 8), ("检查一下改动", 9),
    ],
    "designer": [
        ("界面设计", 10), ("UI设计", 10), ("UX设计", 10), ("交互设计", 10),
        ("页面设计", 9), ("网页设计", 10), ("设计网页", 10),
        ("原型", 7), ("设计规范", 9), ("视觉设计", 9),
        ("布局设计", 9), ("组件设计", 8),
    ],
    "test-generator": [
        ("生成测试", 10), ("写测试用例", 10), ("测试生成", 10),
        ("单元测试生成", 10), ("自动生成测试", 10), ("mock", 7),
        ("测试用例", 10),
    ],
    "critic": [
        ("评估输出", 10), ("质量检查", 9), ("输出审查", 9), ("格式检查", 8),
    ],
    "memory-keeper": [
        ("压缩上下文", 10), ("摘要", 8), ("记忆管理", 9), ("会话总结", 9),
    ],
    "router": [
        ("路由", 8), ("意图识别", 9), ("agent选择", 9),
    ],
}

_agent_models = {}


def _init_agent_models():
    global _agent_models
    for agent in load_agents():
        if agent.get("model"):
            _agent_models[agent["name"]] = agent["model"]


_init_agent_models()


def classify_task_complexity(task: str) -> str:
    """评估任务复杂度，决定走哪条管线路径。

    Returns: 'trivial' | 'simple' | 'normal' | 'complex'
    """
    task_lower = task.lower()

    # 估算涉及文件数（显式数字 + 文件名模式匹配）
    file_patterns = re.findall(r'(\d+)\s*(?:个|处|份)?\s*(?:文件|file)', task)
    file_count = sum(int(n) for n in file_patterns)
    named_files = len(re.findall(r'\b[\w/-]+\.(?:py|js|ts|jsx|tsx|css|html|md|yaml|json|toml)\b', task))
    total_files = max(file_count, named_files)

    # 只读关键词 → 优先 trivial
    readonly_kw = ["查找", "搜索", "grep", "查看", "读取", "检查", "查询",
                   "列出", "显示", "list", "find", "search", "cat ", "ls ", "dir ",
                   "帮我看", "看看", "怎么", "什么是", "在哪", "是什么"]
    # 架构/重量级关键词 → complex
    complex_kw = ["重构", "架构", "系统设计", "多模块", "数据库迁移",
                  "安全审计", "性能优化", "全量", "整体", "refactor",
                  "architecture", "migration", "完整的", "重新设计", "重写整个"]
    # 写入关键词 → 至少 simple 起步
    write_kw = ["修改", "修复", "fix", "调整", "加个", "删掉", "改个", "tweak",
                "写一个", "添加", "增加", "新建", "创建", "实现", "开发",
                "add ", "create", "build", "implement"]

    task_len = len(task)

    # ── complex: 5+文件 / 架构词 / 超长 ──
    if total_files >= 5 or any(kw in task_lower for kw in complex_kw) or task_len > 400:
        return "complex"

    # ── trivial: 只读 + 0-1文件 + 不太长 ──
    is_readonly = any(kw in task_lower for kw in readonly_kw)
    is_write = any(kw in task_lower for kw in write_kw)
    if is_readonly and not is_write and total_files <= 1 and task_len < 200:
        return "trivial"
    # 单文件小修 → 也归 trivial
    if total_files == 1 and task_len < 40 and not any(kw in task_lower for kw in complex_kw):
        return "trivial"

    # ── simple: 1-3文件 + 有写入意图 ──
    if 1 <= total_files <= 3 and is_write:
        return "simple"
    # 短写入任务无明确文件 → simple
    if is_write and task_len < 120 and total_files == 0:
        return "simple"

    return "normal"


def _extract_plan(text: str) -> dict | None:
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


from maestro.models import PROVIDER_MAP, PROVIDER_PRESETS  # noqa: F401


def build_isolated_env(api_key: str | None, api_provider: str = "deepseek") -> dict[str, str]:
    """返回含 API key 注入的隔离环境变量"""
    import os
    iso_env = os.environ.copy()
    iso_env["CLAUDE_CODE_CONFIG_DIR"] = ISOLATED_CONFIG
    if api_key:
        iso_env["ANTHROPIC_AUTH_TOKEN"] = api_key
        for k, v in PROVIDER_MAP.get(api_provider, PROVIDER_MAP["deepseek"]).items():
            iso_env[k] = v
    return iso_env
