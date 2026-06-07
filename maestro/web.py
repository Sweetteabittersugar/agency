#!/usr/bin/env python3
"""
Agency — Claude Code Web 前端
  python maestro/web.py   →   http://localhost:8800
"""
import os, sys, json, time, yaml, threading, subprocess, shutil, logging, re
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
from queue import Empty

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# 确保 maestro/ 的父目录在 sys.path 中
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Claude Code 配置 ──
# 项目 .claude/ 目录用于存放 Agent 定义等配置文件
# 会话管理由 Claude Code 自己的 ~/.claude/ 负责
_claude_dir = str(PROJECT_ROOT / ".claude")
_claude_dir_path = Path(_claude_dir)
_claude_dir_path.mkdir(parents=True, exist_ok=True)

# Agency 独立沙箱 — 避免和用户主 Claude Code 会话冲突
ISOLATED_CONFIG = str(PROJECT_ROOT / ".claude-isolated")
_isolated_path = Path(ISOLATED_CONFIG)
_isolated_path.mkdir(parents=True, exist_ok=True)
# 确保有 settings.json（始终从全局合并，保证 API key 等配置最新）
src_settings = _claude_dir_path / "settings.json"
global_settings = Path.home() / ".claude" / "settings.json"
_merged = {}
for src in [global_settings, src_settings]:
    if src.exists():
        try:
            for k, v in json.loads(src.read_text(encoding="utf-8")).items():
                if isinstance(v, dict) and k in _merged:
                    _merged[k].update(v)
                else:
                    _merged[k] = v
        except Exception:
            pass
(_isolated_path / "settings.json").write_text(json.dumps(_merged, indent=2, ensure_ascii=False), encoding="utf-8")
# 同步 agents
_src_agents = PROJECT_ROOT / "agents"
if _src_agents.exists():
    _dst_agents = _isolated_path / "agents"
    _dst_agents.mkdir(exist_ok=True)
    for f in _src_agents.glob("*.md"):
        shutil.copy2(str(f), str(_dst_agents / f.name))
# 同步 .claude/agents
_claude_agents = _claude_dir_path / "agents"
if _claude_agents.exists():
    _dst_agents = _isolated_path / "agents"
    _dst_agents.mkdir(exist_ok=True)
    for f in _claude_agents.glob("*.md"):
        shutil.copy2(str(f), str(_dst_agents / f.name))
# 同步 skills
for _src_skills in [_claude_dir_path / "skills", Path.home() / ".claude" / "skills"]:
    if _src_skills.exists():
        _dst_skills = _isolated_path / "skills"
        _dst_skills.mkdir(exist_ok=True)
        for _sd in _src_skills.iterdir():
            if _sd.is_dir():
                _dest = _dst_skills / _sd.name
                if not _dest.exists():
                    shutil.copytree(str(_sd), str(_dest))

# ── 加载 .env ──
from maestro.env_loader import load_dotenv
load_dotenv(PROJECT_ROOT)

PORT = 8800

# ── 诊断日志 ──
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(thread)d] %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(str(PROJECT_ROOT / 'maestro' / 'agency.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stderr),
    ]
)
log = logging.getLogger('agency')
AGENCY_VERSION = (PROJECT_ROOT / "VERSION").read_text().strip() if (PROJECT_ROOT / "VERSION").exists() else "0.1.0"

# ── 检测 Claude CLI ──
CLAUDE_BIN = shutil.which("claude")
if not CLAUDE_BIN:
    for p in [os.path.expanduser("~/AppData/Roaming/npm/claude.cmd"),
              os.path.expanduser("~/AppData/Roaming/npm/claude")]:
        if os.path.isfile(p): CLAUDE_BIN = p; break

# ── Agent 列表缓存 ──
from maestro.agent_parser import parse_agent_md

def load_agents():
    """从 agents/ 目录加载 Agent 列表（只读元数据，不做路由）"""
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

# ── 简单关键词路由（Claude Code --agent 参数用）──
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
            # 看同名的 jsonl 文件大小判断是否有输出
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
            pass
    return agents

def _extract_plan(text: str):
    """从 orchestrator 输出中提取 JSON 计划"""
    import re
    # 匹配 ```json ... ``` 块
    m = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
    if not m:
        # 尝试匹配裸 JSON 对象
        m = re.search(r'\{[^{}]*"phases"\s*:\s*\[.*?\]\s*[^{}]*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1) if '```' in text else m.group(0))
        except Exception:
            pass
    return None

# ── Agent model 映射 ──
_agent_models = {}
def _init_agent_models():
    global _agent_models
    for agent in load_agents():
        if agent.get("model"):
            _agent_models[agent["name"]] = agent["model"]
_init_agent_models()

def simple_route(task):
    """简单关键词匹配，返回 {"agent": name, "model": model} 或 None"""
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

# ── 费用估算 ── 统一使用 models.py 的定价表
from maestro.models import estimate_cost

# ── Harness 模块 ──
from maestro.harness.watcher import bus
from maestro.harness.hooks_receiver import handle_hook_callback
from maestro.harness.jsonl_parser import find_latest_session, parse_usage_from_line, analyze_session

# ── 权限日志 ──
_permission_log = []  # 最近 200 条权限决策
_permission_log_lock = threading.Lock()

def record_permission(tool_name, decision, risk, reason=""):
    entry = {"time": time.strftime("%H:%M:%S"), "tool": tool_name, "decision": decision, "risk": risk, "reason": reason}
    with _permission_log_lock:
        _permission_log.append(entry)
        if len(_permission_log) > 200:
            _permission_log[:] = _permission_log[-200:]

def get_permission_stats():
    with _permission_log_lock:
        total = len(_permission_log)
        allowed = sum(1 for e in _permission_log if e["decision"] == "allow")
        denied = sum(1 for e in _permission_log if e["decision"] == "deny")
        blocked = sum(1 for e in _permission_log if e["decision"] == "block")
    return {"total": total, "allowed": allowed, "denied": denied, "blocked": blocked}

# ── 记忆文件辅助 ──
from maestro.web_memory import list_memory_files, get_memory_file, save_memory_file

# ── 子进程追踪（防止泄漏）──
_proc_lock = threading.Lock()
MAX_PROCS = 8

# 用 list 包装避免 global 声明问题 — Python 的 set -= 是赋值操作
_proc_registry = []  # list of subprocess.Popen

def _track_proc(proc):
    with _proc_lock:
        _proc_registry.append(proc)
        if len(_proc_registry) > MAX_PROCS:
            _proc_registry[:] = [p for p in _proc_registry if p.poll() is None]

def _untrack_proc(proc):
    with _proc_lock:
        try:
            _proc_registry.remove(proc)
        except ValueError:
            pass

def _kill_proc(proc):
    """强制终止子进程并清理"""
    try:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    _untrack_proc(proc)

def _cleanup_all_procs():
    with _proc_lock:
        for p in list(_proc_registry):
            _kill_proc(p)
        _proc_registry.clear()

# ── 费用记录（多维：项目 / Agent / 模型 / 日期）──
from maestro.web_cost import record_cost, get_cost_analytics


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """多线程 HTTP Server"""
    daemon_threads = True
    request_queue_size = 32
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            html_path = PROJECT_ROOT / "webui" / "index.html"
            if html_path.exists():
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                self.wfile.write(html_path.read_bytes())
            else:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"<h1>Agency</h1><p>webui/index.html not found.</p>")
            return

        # Static files
        static_path = PROJECT_ROOT / "webui" / path.lstrip("/")
        if static_path.exists() and static_path.is_file():
            ct = "text/html"
            if path.endswith(".css"): ct = "text/css"
            elif path.endswith(".js"): ct = "application/javascript"
            elif path.endswith(".svg"): ct = "image/svg+xml"
            elif path.endswith(".png"): ct = "image/png"
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(static_path.read_bytes())
            return

        if path == "/api/agents":
            self.send_json(load_agents())
        elif path.startswith("/api/agents/") and len(path) > len("/api/agents/"):
            # 读取单个 Agent 的 .md 完整内容
            name = path[len("/api/agents/"):]
            if not re.match(r'^[a-zA-Z0-9_-]+$', name):
                self.send_json({"error": "invalid name"}, 400)
                return
            agent_content = None
            for search_dir in [
                PROJECT_ROOT / "agents",
                _claude_dir_path / "agents",
                Path.home() / ".claude" / "agents",
            ]:
                candidate = search_dir / f"{name}.md"
                if candidate.exists():
                    agent_content = candidate.read_text(encoding="utf-8")
                    break
            if agent_content is not None:
                self.send_json({"name": name, "content": agent_content})
            else:
                self.send_json({"error": f"agent '{name}' not found"}, 404)
        elif path == "/api/version":
            self.send_json({"version": AGENCY_VERSION})
        elif path == "/api/settings":
            self.send_json({
                "claude_bin": CLAUDE_BIN or "not found",
                "config_dir": _claude_dir,
                "has_api_key": bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")),
                "version": AGENCY_VERSION,
            })
        elif path == "/api/cost":
            days = int(parse_qs(parsed.query).get("days", ["30"])[0])
            data = get_cost_analytics(PROJECT_ROOT, days)
            if data:
                self.send_json(data)
            else:
                self.send_json({"total": {"calls":0,"cost":0}, "today": {"calls":0,"cost":0}, "by_date":[], "by_model":[], "by_agent":[], "by_project":[], "alerts":[]})
        elif path == "/api/cost/history":
            days = int(parse_qs(parsed.query).get("days", ["30"])[0])
            data = get_cost_analytics(PROJECT_ROOT, days)
            if data:
                self.send_json({"by_date": data.get("by_date", []), "by_model": data.get("by_model", []),
                                "cache": data.get("cache", {"read_tok":0,"write_tok":0,"saved":0})})
            else:
                self.send_json({"by_date": [], "by_model": [], "cache": {"read_tok":0,"write_tok":0,"saved":0}})
        elif path == "/api/cost/alerts":
            data = get_cost_analytics(PROJECT_ROOT, 7)
            alerts = data.get("alerts", []) if data else []
            self.send_json({"alerts": alerts})
        # ── Harness GET 端点 ──
        elif path == "/api/harness/stream":
            # SSE 长连接 — 聚合所有 Harness 事件
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            q = bus.listen()
            try:
                while True:
                    payload = q.get(timeout=30)
                    try:
                        self.wfile.write(f"event: harness\ndata: {payload}\n\n".encode())
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        break
            except Empty:
                pass
            finally:
                bus.unlisten(q)
        elif path == "/api/permissions/allowlist":
            # 从 settings.json 读取 allow 规则
            settings_path = _claude_dir_path / "settings.json"
            rules = []
            if settings_path.exists():
                try:
                    s = json.loads(settings_path.read_text(encoding="utf-8"))
                    rules = s.get("permissions", {}).get("allow", [])
                except Exception:
                    pass
            self.send_json({"rules": rules})
        elif path == "/api/permissions/history":
            limit = int(parse_qs(parsed.query).get("limit", ["50"])[0])
            with _permission_log_lock:
                hist = _permission_log[-limit:]
            stats = get_permission_stats()
            self.send_json({"history": list(reversed(hist)), "stats": stats})
        elif path == "/api/permissions/stats":
            self.send_json(get_permission_stats())
        elif path == "/api/harness/context":
            try:
                sid = parse_qs(parsed.query).get("session", [""])[0]
                proj = str(PROJECT_ROOT)
                if sid:
                    home = Path.home()
                    slug = proj.replace("\\", "/").rstrip("/").replace(":/", "--").replace("/", "-").lstrip("-")
                    jsonl_path = home / ".claude" / "projects" / slug / f"{sid}.jsonl"
                    if jsonl_path.exists():
                        result = analyze_session(str(jsonl_path))
                        result["should_compact"] = result.get("total_tokens", 0) > 300000
                        self.send_json(result)
                    else:
                        self.send_json({"total_tokens": 0, "session_id": sid, "error": "session not found", "should_compact": False})
                else:
                    session_info = find_latest_session(proj)
                    if session_info and os.path.exists(session_info["path"]):
                        result = analyze_session(session_info["path"])
                        result["should_compact"] = result.get("total_tokens", 0) > 300000
                        self.send_json(result)
                    else:
                        self.send_json({"total_tokens": 0, "session_id": "", "last_update": time.strftime("%H:%M:%S"), "should_compact": False})
            except Exception as e:
                self.send_json({"total_tokens": 0, "error": str(e)[:100], "should_compact": False})
        elif path == "/api/harness/subagents":
            sid = parse_qs(parsed.query).get("session", [""])[0]
            proj = str(PROJECT_ROOT)
            tree = []
            # 扫描 Agency 的 sessions
            if not sid:
                info = find_latest_session(proj)
                sid = info["session_id"] if info else ""
            if sid:
                tree += _scan_subagents(proj, sid)
            # 也扫描用户主项目 D:\ai 的最新 session（常有丰富子Agent数据）
            user_proj = os.environ.get("AGENCY_USER_PROJ", "")
            if user_proj and os.path.isdir(user_proj):
                user_info = find_latest_session(user_proj)
                if user_info:
                    tree += _scan_subagents(user_proj, user_info["session_id"])
            self.send_json({"tree": tree, "stats": {"total": len(tree), "running": 0, "done": len(tree), "failed": 0}})
        elif path == "/api/harness/events":
            evt_type = parse_qs(parsed.query).get("type", [None])[0]
            limit = int(parse_qs(parsed.query).get("limit", ["50"])[0])
            events = bus.recent_events(evt_type, limit)
            self.send_json({"events": events})
        elif path == "/api/skills":
            skills = []
            for skills_dir in [_claude_dir_path / "skills", Path.home() / ".claude" / "skills"]:
                if not skills_dir.exists():
                    continue
                for skill_dir in skills_dir.iterdir():
                    if not skill_dir.is_dir():
                        continue
                    skmd = skill_dir / "SKILL.md"
                    if skmd.exists():
                        try:
                            content = skmd.read_text(encoding="utf-8")
                            fm = {}
                            if content.startswith("---"):
                                parts = content.split("---", 2)
                                if len(parts) >= 3:
                                    try:
                                        fm = yaml.safe_load(parts[1]) or {}
                                    except Exception:
                                        pass
                            skills.append({
                                "name": skill_dir.name,
                                "description": fm.get("description", ""),
                                "triggers": fm.get("triggers", fm.get("trigger", [])),
                                "model": fm.get("model", ""),
                                "enabled": True,
                                "path": str(skmd.resolve()),
                            })
                        except Exception:
                            pass
            self.send_json(skills)
        elif path == "/api/memory":
            self.send_json({"files": list_memory_files(PROJECT_ROOT)})
        elif path.startswith("/api/memory/"):
            rel = path[len("/api/memory/"):]
            data, code = get_memory_file(PROJECT_ROOT, rel)
            self.send_json(data, code)
        elif path == "/api/files":
            # 文件浏览器 — 列出目录
            target = parse_qs(parsed.query).get("path", [str(PROJECT_ROOT)])[0]
            try:
                p = Path(target).resolve()
                if not p.exists():
                    p = PROJECT_ROOT.resolve()
                else:
                    try:
                        p.relative_to(PROJECT_ROOT.resolve())
                    except ValueError:
                        self.send_json({"error": "forbidden"}, 403)
                        return
                entries = []
                for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                    try:
                        entries.append({
                            "name": child.name,
                            "is_dir": child.is_dir(),
                            "size": child.stat().st_size if child.is_file() else 0,
                            "mtime": time.strftime("%m-%d %H:%M", time.localtime(child.stat().st_mtime)),
                        })
                    except Exception:
                        pass
                self.send_json({"path": str(p), "entries": entries, "parent": str(p.parent) if p.parent != p else ""})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        elif path == "/api/mcp/status":
            # 读取多个 .mcp.json 并检测进程
            servers = []
            seen = set()
            # 扫描多个来源
            mcp_sources = [
                PROJECT_ROOT / ".mcp.json",
                Path.home() / ".claude" / ".mcp.json",
                PROJECT_ROOT / ".." / ".mcp.json",  # 上级目录（如 D:\ai）
            ]
            for src in mcp_sources:
                if not src.exists():
                    continue
                try:
                    mcp = json.loads(src.read_text(encoding="utf-8"))
                    for name, cfg in mcp.get("mcpServers", {}).items():
                        if name in seen:
                            continue
                        seen.add(name)
                        cmd = cfg.get("command", "")
                        # MCP 服务由 Claude Code 管理，有配置即视为可用
                        running = True
                        servers.append({
                            "name": name,
                            "command": cmd,
                            "args": cfg.get("args", []),
                            "env": list(cfg.get("env", {}).keys()) if cfg.get("env") else [],
                            "running": running,
                            "source": str(src),
                            "tools": [],
                            "callCount": 0,
                        })
                except Exception:
                    pass
            self.send_json({"servers": servers})
        else:
            self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length > 0 else {}
        path = urlparse(self.path).path

        if path == "/api/chat":
            task = body.get("task", "")
            force_agent = body.get("force_agent", "")
            proj_dir = body.get("proj_dir", "")
            api_key = body.get("api_key", "")
            api_provider = body.get("api_provider", "")

            if not task:
                self.send_json({"error": "Empty request"})
                return

            # 确定 Agent
            route_info = simple_route(task) if not force_agent else None
            agent_name = force_agent or (route_info["agent"] if route_info else "")
            model = body.get("model", "") or (route_info.get("model", "") if route_info else "")
            actual_task = task
            if force_agent:
                m = task.strip().split(" ", 1)
                if len(m) > 1 and m[0].startswith("@"):
                    actual_task = m[1]

            # ── Agent 注入：显式读取 agent .md，注入 model / tools / system prompt ──
            agent_model_override = ""
            agent_tools_override = []
            agent_system_prompt = ""
            if force_agent:
                for search_dir in [
                    PROJECT_ROOT / "agents",
                    _claude_dir_path / "agents",
                    Path.home() / ".claude" / "agents",
                ]:
                    candidate = search_dir / f"{force_agent}.md"
                    if candidate.exists():
                        info = parse_agent_md(candidate)
                        agent_model_override = info["model"]
                        agent_tools_override = info["tools"]
                        agent_system_prompt = info["body"]
                        log.info(f"CHAT agent injection: model={agent_model_override}, tools={agent_tools_override}, prompt_len={len(agent_system_prompt)}")
                        break
            # 注入 model
            if agent_model_override and not model:
                model = agent_model_override
            # 注入系统提示词到消息开头
            if agent_system_prompt:
                actual_task = agent_system_prompt + "\n\n---\n\n" + actual_task

            if not CLAUDE_BIN:
                self.send_json({"error": "Claude Code CLI 未安装。请安装后重试。"})
                return

            # SSE
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()

            try:
                # 上下文：首条消息不用 --continue，后续自动加
                is_first = body.get("is_first_message", True)

                # 会话管理：--session-id 创建命名会话，--resume 续接
                session_id = body.get("session_id", "")
                is_new = body.get("is_new_session", True)
                meta = json.dumps({"agent": agent_name or "auto", "model": "auto", "session": session_id[:8] if session_id else "new"})
                self.wfile.write(f"event: meta\ndata: {meta}\n\n".encode())
                self.wfile.flush()

                safe_task = actual_task.replace('\n', ' ').replace('\r', ' ')
                safe_task = re.sub(r'[\$\`\(\)\{\}\;\&\|\<\>]', '', safe_task)
                safe_task = safe_task.replace('"', '\\"')
                flags = "--bare --permission-mode auto"
                if session_id:
                    if is_new:
                        flags += f' --session-id "{session_id}"'
                    else:
                        flags += f' --resume "{session_id}"'
                if agent_name:
                    flags += f' --agent "{agent_name}"'
                if model:
                    flags += f' --model "{model}"'
                if agent_tools_override:
                    flags += f' --tools "{",".join(agent_tools_override)}"'
                if proj_dir and os.path.isdir(proj_dir):
                    flags += f' --add-dir "{proj_dir}"'
                cmd_str = f'"{CLAUDE_BIN}" -p "{safe_task}" {flags}'

                log.info(f'CHAT start agent={agent_name or "auto"} task="{actual_task[:40]}…"')
                start_time = time.time()
                proc = None
                out_chars = 0
                try:
                    # 隔离 env — 不和用户主 Claude Code 抢资源
                    iso_env = os.environ.copy()
                    iso_env["CLAUDE_CODE_CONFIG_DIR"] = ISOLATED_CONFIG
                    # 用户自配 API Key — 新手只需填 Key
                    if api_key:
                        provider_map = {
                            "deepseek": {"ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic", "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-v4-pro", "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek-v4-flash", "ANTHROPIC_MODEL": "deepseek-v4-pro"},
                            "anthropic": {},
                            "openai": {"ANTHROPIC_BASE_URL": "https://api.openai.com/v1"},
                        }
                        iso_env["ANTHROPIC_AUTH_TOKEN"] = api_key
                        for k, v in provider_map.get(api_provider, provider_map["deepseek"]).items():
                            iso_env[k] = v
                        log.info(f'CHAT using user API key provider={api_provider}')
                    t0 = time.time()
                    proc = subprocess.Popen(cmd_str, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            encoding='utf-8', errors='replace', bufsize=1,
                                            cwd=str(PROJECT_ROOT), shell=True, env=iso_env)
                    log.info(f'CHAT proc spawn {(time.time()-t0)*1000:.0f}ms PID={proc.pid}')
                    _track_proc(proc)
                    first_line = True
                    for line in iter(proc.stdout.readline, ''):
                        if first_line:
                            log.info(f'CHAT first output after {(time.time()-start_time)*1000:.0f}ms')
                            first_line = False
                        if not line: break
                        stripped = line.rstrip('\n\r')
                        if not stripped: continue
                        out_chars += len(stripped)
                        # 折叠超长工具输出 / 标记工具调用
                        display = stripped
                        if len(stripped) > 500:
                            display = '<details><summary>📄 展开 (' + str(len(stripped)) + '字符)</summary><pre>' + stripped.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') + '</pre></details>'
                        elif stripped.startswith('[Tool:') or stripped.startswith('Tool:'):
                            display = '<div class="tool-tag">🔧 ' + stripped.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') + '</div>'
                        try:
                            self.wfile.write(f"data: {json.dumps({'content': display + chr(10)})}\n\n".encode())
                            self.wfile.flush()
                        except (BrokenPipeError, ConnectionResetError):
                            log.info(f'CHAT client disconnected, killing proc')
                            break  # 客户端断开

                    # 正常结束：等待进程退出
                    try:
                        proc.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        pass

                    elapsed = time.time() - start_time

                    # 尝试从 JSONL 获取真实 token 数
                    detected_model = model or "deepseek-v4-pro"
                    is_estimated = True
                    in_tokens = len(task) // 4
                    out_tokens = out_chars // 2
                    cache_read = 0
                    cache_write = 0
                    cache_saved = 0.0

                    if session_id:
                        home = Path.home()
                        proj_slug = str(PROJECT_ROOT).replace("\\", "/").rstrip("/").replace(":/", "--").replace("/", "-").lstrip("-")
                        jsonl_path = home / ".claude" / "projects" / proj_slug / f"{session_id}.jsonl"
                        if jsonl_path.exists() and jsonl_path.stat().st_size > 100:
                            try:
                                analysis = analyze_session(str(jsonl_path), model or "")
                                in_tokens = analysis.get("input_tokens", 0) or in_tokens
                                out_tokens = analysis.get("output_tokens", 0) or out_tokens
                                cache_read = analysis.get("cache_read_tokens", 0)
                                cache_write = analysis.get("cache_write_tokens", 0)
                                cache_saved = analysis.get("cost_est", {}).get("cache_saved", 0.0)
                                if analysis.get("model"):
                                    detected_model = analysis["model"]
                                is_estimated = False
                            except Exception:
                                pass

                    cost = estimate_cost(detected_model, in_tokens, out_tokens)
                    try:
                        self.wfile.write(f"event: done\ndata: {json.dumps({'elapsed': round(elapsed,1), 'cost': round(cost,6), 'in_tokens': in_tokens, 'out_tokens': out_tokens})}\n\n".encode())
                        self.wfile.flush()
                    except Exception:
                        pass
                    record_cost(PROJECT_ROOT, time.strftime("%Y-%m-%d %H:%M:%S"), detected_model, in_tokens, out_tokens, cost, elapsed, agent_name, proj_dir or "",
                                cache_read, cache_write, cache_saved, is_estimated, session_id or "")
                    log.info(f'CHAT done elapsed={elapsed:.1f}s cost=${cost:.4f} model={detected_model} estimated={is_estimated}')
                finally:
                    if proc:
                        _kill_proc(proc)
                        log.info(f'CHAT proc cleaned')

            except Exception as e:
                try:
                    self.wfile.write(f"data: {json.dumps({'error': str(e)})}\n\n".encode())
                    self.wfile.flush()
                except Exception:
                    pass

        elif path == "/api/route":
            task = body.get("task", "")
            route_info = simple_route(task)
            if route_info:
                self.send_json({"agent": route_info["agent"], "model": route_info["model"], "method": "keyword"})
            else:
                self.send_json({"agent": "coder", "model": "", "method": "keyword"})

        elif path == "/api/orchestrate":
            # 智能调度：orchestrator 出计划 → 自动分窗执行
            task = body.get("task", "")
            proj_dir = body.get("proj_dir", "")
            api_key = body.get("api_key", "")
            api_provider = body.get("api_provider", "")
            if not task:
                self.send_json({"error": "task required"})
                return
            if not CLAUDE_BIN:
                self.send_json({"error": "Claude CLI not found"})
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()

            proc = None
            full_output = ""
            start_time = time.time()
            try:
                safe_task = task.replace('\n', ' ').replace('\r', ' ')
                cmd = ["cmd", "/c", CLAUDE_BIN, "-p", safe_task, "--bare", "--permission-mode", "auto", "--agent", "orchestrator"]
                if proj_dir and os.path.isdir(proj_dir):
                    cmd += ["--add-dir", proj_dir]

                self.wfile.write(f"event: phase\ndata: {json.dumps({'msg': '🧠 分析任务…'})}\n\n".encode())
                self.wfile.flush()

                iso_env = os.environ.copy()
                iso_env["CLAUDE_CODE_CONFIG_DIR"] = ISOLATED_CONFIG
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        encoding='utf-8', errors='replace', bufsize=1,
                                        cwd=str(PROJECT_ROOT), env=iso_env)
                _track_proc(proc)
                for line in iter(proc.stdout.readline, ''):
                    if not line: break
                    stripped = line.rstrip('\n\r')
                    if not stripped: continue
                    full_output += stripped + "\n"
                    try:
                        self.wfile.write(f"data: {json.dumps({'content': stripped + chr(10)})}\n\n".encode())
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        break

                try: proc.wait(timeout=15)
                except subprocess.TimeoutExpired: pass

                # 记录 orchestrator 调用费用
                elapsed = time.time() - start_time
                in_tokens = len(task) // 4
                out_tokens = len(full_output) // 2
                orchestrator_model = "deepseek-v4-pro"
                cost = estimate_cost(orchestrator_model, in_tokens, out_tokens)
                record_cost(PROJECT_ROOT, time.strftime("%Y-%m-%d %H:%M:%S"), orchestrator_model, in_tokens, out_tokens, cost, elapsed, "orchestrator", proj_dir or "")

                # 提取 JSON 计划
                plan = _extract_plan(full_output)
                if plan:
                    self.wfile.write(f"event: plan\ndata: {json.dumps(plan, ensure_ascii=False)}\n\n".encode())
                    self.wfile.flush()
                else:
                    self.wfile.write(f"event: done\ndata: {json.dumps({'summary': '无法解析调度计划'})}\n\n".encode())
                    self.wfile.flush()
            except Exception as e:
                try:
                    self.wfile.write(f"event: error\ndata: {json.dumps({'msg': str(e)})}\n\n".encode())
                    self.wfile.flush()
                except Exception: pass
            finally:
                if proc: _kill_proc(proc)

        # ── Harness POST 端点 ──
        elif path.startswith("/api/hooks/"):
            # Claude Code Hook HTTP 回调接收
            event = path[len("/api/hooks/"):]
            result = handle_hook_callback(event, body)
            self.send_json(result)

        elif path == "/api/permissions/allowlist":
            # 添加 allow 规则到 settings.json
            rule = body.get("rule", "")
            if not rule:
                self.send_json({"error": "rule required"}, 400)
                return
            settings_path = _claude_dir_path / "settings.json"
            settings = {}
            if settings_path.exists():
                try:
                    settings = json.loads(settings_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            perms = settings.setdefault("permissions", {})
            allow_list = perms.setdefault("allow", [])
            if rule not in allow_list:
                allow_list.append(rule)
            settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
            self.send_json({"ok": True, "rule": rule})

        elif path == "/api/permissions/decision":
            # 前端返回权限决策
            decision = body.get("decision", "deny")
            tool_name = body.get("tool_name", "")
            risk = body.get("risk", {})
            reason = body.get("reason", "")
            record_permission(tool_name, decision, risk, reason)
            # 广播给其他连接的 Harness 客户端
            bus.broadcast("permission_decision", {
                "tool_name": tool_name, "decision": decision, "reason": reason,
                "timestamp": time.strftime("%H:%M:%S"),
            })
            self.send_json({"ok": True})

        elif path.startswith("/api/memory/"):
            rel = path[len("/api/memory/"):]
            content = body.get("content", "")
            data, code = save_memory_file(PROJECT_ROOT, rel, content)
            self.send_json(data, code)

        elif path == "/api/skills/toggle":
            # 启用/禁用 Skill
            name = body.get("name", "")
            enabled = body.get("enabled", True)
            if not name:
                self.send_json({"error": "name required"}, 400)
                return
            skill_path = _claude_dir_path / "skills" / name / "SKILL.md"
            disabled_path = _claude_dir_path / "skills" / name / "SKILL.md.disabled"
            try:
                if enabled and disabled_path.exists():
                    disabled_path.rename(skill_path)
                elif not enabled and skill_path.exists():
                    skill_path.rename(disabled_path)
                self.send_json({"ok": True, "name": name, "enabled": enabled})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        elif path == "/api/mcp/config":
            # 保存 MCP 配置
            mcp_config = body.get("config", body)
            mcp_config_path = PROJECT_ROOT / ".mcp.json"
            try:
                mcp_config_path.write_text(json.dumps(mcp_config, indent=2, ensure_ascii=False), encoding="utf-8")
                self.send_json({"ok": True})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        elif path == "/api/agent-update":
            # 保存 Agent .md 文件（PUT 语义）
            name = body.get("name", "")
            if not re.match(r'^[a-zA-Z0-9_-]+$', name):
                self.send_json({"error": "invalid name"}, 400)
                return
            content = body.get("content", "")
            if not name or not content:
                self.send_json({"error": "name and content required"}, 400)
                return
            try:
                # 优先写入 agents/ 目录
                agent_file = PROJECT_ROOT / "agents" / f"{name}.md"
                agent_file.parent.mkdir(parents=True, exist_ok=True)
                agent_file.write_text(content, encoding="utf-8")
                # 同步到 .claude/agents/
                claude_agent = _claude_dir_path / "agents" / f"{name}.md"
                claude_agent.parent.mkdir(parents=True, exist_ok=True)
                claude_agent.write_text(content, encoding="utf-8")
                # 同步到 .claude-isolated/
                iso_agent = _isolated_path / "agents" / f"{name}.md"
                iso_agent.parent.mkdir(parents=True, exist_ok=True)
                iso_agent.write_text(content, encoding="utf-8")
                self.send_json({"ok": True, "name": name})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        elif path == "/api/settings":
            # PATCH settings.json
            patch = body.get("patch", body)
            settings_path = _claude_dir_path / "settings.json"
            current = {}
            if settings_path.exists():
                try:
                    current = json.loads(settings_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            # 浅合并
            current.update(patch)
            settings_path.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
            self.send_json({"ok": True})

        else:
            self.send_json({"error": "not found"}, 404)

    def send_json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        pass

# ═══════════════════════════════════════
# Startup
# ═══════════════════════════════════════
def _kill_old():
    """Kill processes on our port."""
    try:
        subprocess.run(
            f'powershell -Command "'
            f'$pids = (Get-NetTCPConnection -LocalPort {PORT} -ErrorAction SilentlyContinue |'
            f' Select-Object -ExpandProperty OwningProcess | Sort-Object -Unique);'
            f' foreach ($p in $pids) {{ if ($p -ne $pid) {{ Stop-Process -Id $p -Force }} }}"',
            shell=True, capture_output=True, timeout=10
        )
    except Exception:
        pass

if __name__ == "__main__":
    import webbrowser, socket
    _kill_old()
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    httpd.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    httpd.timeout = 30  # socket 超时
    threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    print(f"\n  Agency v{AGENCY_VERSION}  [多线程模式]")
    print(f"  Claude Code config: {_claude_dir}")
    print(f"  http://localhost:{PORT}\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        _cleanup_all_procs()
        httpd.shutdown()
