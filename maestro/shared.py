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
    "coder": [
        ("写代码", 10), ("实现功能", 9), ("开发功能", 9), ("修复bug", 9),
        ("改代码", 8), ("编程", 8), ("fix", 8),
        ("重构", 6), ("bug", 6), ("代码", 6), ("写", 4), ("改", 3),
        ("开发", 7), ("实现", 5), ("编写", 7), ("修改", 5),
        ("构建", 6), ("编译", 6), ("build", 6),
        ("死代码", 7), ("清理代码", 7), ("简化代码", 6),
        ("构建失败", 10), ("编译错误", 10),
        ("报错", 4), ("修复", 6),
    ],
    "code-reviewer": [("审查代码", 10), ("代码审查", 10), ("审查", 10), ("review", 9), ("检查代码", 9)],
    "explorer": [("查",9),("找",8),("分析",7),("定位",8),("搜索",9),("grep",8),("探索",8)],
    "test-runner": [("跑测试",10),("测试策略",9),("边界用例",8),("回归测试",9),("测试",8),("验证",5),("test",7),("跑一下",6)],
    "security-reviewer": [("安全",10),("漏洞",10),("注入",9),("密钥",9),("扫描",7),("审计安全",9)],
    "webnovel-writer": [("写小说",10),("写一篇小说",10),("小说",9),("网文",10),("章节",9),("大纲",8),("人物",8),("写作",9),("故事",9),("世界观",8),("写故事",10)],
    "planner": [("规划",9),("设计",8),("架构",10),("方案",8),("计划",7)],
    "general-worker": [("整理",7),("配置",7),("杂务",5),("文件",6),("清理",7),("文档",7)],
    "python-reviewer": [("python",10),("py",8),("pip",7),("django",10),("flask",9),("fastapi",10)],
    "go-reviewer": [("go",10),("golang",10),("go mod",8),("goroutine",9),("channel",8)],
    "typescript-reviewer": [("ts",9),("typescript",10),("js",8),("javascript",9),("react",10),("vue",8),("node",8),("npm",7)],
    "database-reviewer": [("sql",10),("数据库",10),("mysql",9),("postgres",9),("sqlite",8),("mongodb",8),("orm",8)],
    "performance-optimizer": [("性能",10),("优化",9),("加速",8),("慢",7),("卡",6),("性能问题",10),("profiling",7)],
    "devops": [("部署",10),("docker",10),("k8s",9),("ci",8),("cd",8),("容器",8),("镜像",8),("流水线",8)],
    "doc-updater": [
        ("更新文档", 10), ("写文档", 10), ("文档更新", 10),
        ("api文档", 10), ("readme", 9), ("文档", 4),
        ("接口文档", 10), ("补文档", 9),
    ],
    "build-error-resolver": [("构建",10),("编译",10),("build",8),("编译错误",10),("构建失败",10),("报错",7)],
    "e2e-runner": [("e2e",10),("端到端",10),("浏览器测试",9),("playwright",10),("界面测试",8)],
    "cost-analyst": [("费用",10),("用量",9),("成本",10),("花费",9),("账单",8)],
    "tdd-guide": [("tdd",10),("测试驱动",10),("先写测试",9)],
    "orchestrator": [
        ("完整项目", 9), ("做一个", 6), ("整个项目", 10),
        ("搭一个", 7), ("多个任务", 8), ("调度", 7),
        ("编排", 7), ("多agent", 9), ("复杂任务", 8),
        ("拆解", 10), ("分配", 9), ("协作", 9),
        ("全部", 7), ("整套", 8),
    ],
    "ceo": [("产品",10),("需求",9),("优先级",9),("用户故事",10),("验收标准",9),("功能范围",8)],
    "release-manager": [("发布",10),("版本",9),("changelog",8),("tag",7),("release",9),("回滚",8),("semver",7)],
    "lead": [("委派",10),("领导",9),("异步",8),("后台执行",9),("大任务",9),("lead",10)],
    "architect": [
        ("系统设计", 10), ("架构设计", 10), ("技术选型", 10), ("接口设计", 9),
        ("模块划分", 9), ("架构方案", 10), ("设计文档", 8),
        ("系统架构", 10), ("设计系统", 10),
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
    "critic": [("评估输出",10),("质量检查",9),("输出审查",9),("格式检查",8)],
    "memory-keeper": [("压缩上下文",10),("摘要",8),("记忆管理",9),("会话总结",9)],
    "router": [("路由",8),("意图识别",9),("agent选择",9)],
}

_agent_models = {}


def _init_agent_models():
    global _agent_models
    for agent in load_agents():
        if agent.get("model"):
            _agent_models[agent["name"]] = agent["model"]


_init_agent_models()


def simple_route(task):
    """简单关键词匹配（加权）"""
    tl = task.lower()
    best, best_score = None, 0
    for name, keywords in ROUTING_KEYWORDS.items():
        score = sum(weight for kw, weight in keywords if kw.lower() in tl)
        if score > best_score:
            best, best_score = name, score
    if best_score < 4:
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
    "anthropic": {
        "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
        "ANTHROPIC_MODEL": "claude-sonnet-4-6",
    },
    "openai": {
        "ANTHROPIC_BASE_URL": "https://api.openai.com/v1",
        "ANTHROPIC_MODEL": "gpt-4o",
    },
    "google": {
        "ANTHROPIC_BASE_URL": "https://generativelanguage.googleapis.com/v1beta/openai",
        "ANTHROPIC_MODEL": "gemini-2.5-pro",
    },
    "xai": {
        "ANTHROPIC_BASE_URL": "https://api.x.ai/v1",
        "ANTHROPIC_MODEL": "grok-3",
    },
    "siliconflow": {
        "ANTHROPIC_BASE_URL": "https://api.siliconflow.cn/v1",
        "ANTHROPIC_MODEL": "Pro/deepseek-ai/DeepSeek-V3",
    },
    "qwen": {
        "ANTHROPIC_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "ANTHROPIC_MODEL": "qwen-plus",
    },
    "kimi": {
        "ANTHROPIC_BASE_URL": "https://api.moonshot.cn/v1",
        "ANTHROPIC_MODEL": "moonshot-v1-8k",
    },
    "glm": {
        "ANTHROPIC_BASE_URL": "https://open.bigmodel.cn/api/paas/v4",
        "ANTHROPIC_MODEL": "glm-4-plus",
    },
    "minimax": {
        "ANTHROPIC_BASE_URL": "https://api.minimax.chat/v1",
        "ANTHROPIC_MODEL": "abab7-chat",
    },
    "custom": {},
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
