#!/usr/bin/env python3
"""
Agency — Claude Code Web 前端
  python maestro/web.py   →   http://localhost:8800
"""
import os, sys, json, time, yaml, sqlite3, threading, subprocess, shutil
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Claude Code 配置 ──
# 项目 .claude/ 目录用于存放 Agent 定义等配置文件
# 会话管理由 Claude Code 自己的 ~/.claude/ 负责
_claude_dir = str(PROJECT_ROOT / ".claude")
_claude_dir_path = Path(_claude_dir)
_claude_dir_path.mkdir(parents=True, exist_ok=True)

# ── 加载 .env ──
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

PORT = 8800
AGENCY_VERSION = (PROJECT_ROOT / "VERSION").read_text().strip() if (PROJECT_ROOT / "VERSION").exists() else "0.1.0"

# ── 检测 Claude CLI ──
CLAUDE_BIN = shutil.which("claude")
if not CLAUDE_BIN:
    for p in [os.path.expanduser("~/AppData/Roaming/npm/claude.cmd"),
              os.path.expanduser("~/AppData/Roaming/npm/claude")]:
        if os.path.isfile(p): CLAUDE_BIN = p; break

# ── Agent 列表缓存 ──
def load_agents():
    """从 agents/ 目录加载 Agent 列表（只读元数据，不做路由）"""
    agents = []
    agents_dir = PROJECT_ROOT / "agents"
    if agents_dir.exists():
        for f in sorted(agents_dir.glob("*.md")):
            content = f.read_text(encoding="utf-8")
            fm = {}
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    try: fm = yaml.safe_load(parts[1]) or {}
                    except: pass
            agents.append({
                "name": f.stem,
                "description": fm.get("description", ""),
                "model": fm.get("model", ""),
                "tools": fm.get("tools", []),
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
def simple_route(task):
    """简单关键词匹配，返回 agent 名（供 Claude Code --agent 使用）"""
    tl = task.lower()
    best, best_score = None, 0
    for name, keywords in ROUTING_KEYWORDS.items():
        score = sum(2 for kw in keywords if kw.lower() in tl)
        if score > best_score:
            best, best_score = name, score
    return best if best_score >= 2 else None

# ── 费用估算 ──
PRICING = {
    "deepseek-v4-pro": (0.28, 0.28),
    "deepseek-v4-flash": (0.14, 0.14),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (0.80, 4.0),
}
def estimate_cost(model, in_tokens, out_tokens):
    p = PRICING.get(model, (0, 0))
    return (in_tokens / 1_000_000 * p[0]) + (out_tokens / 1_000_000 * p[1])

# ── 费用记录（多维：项目 / Agent / 模型 / 日期）──
_cost_db_lock = threading.Lock()
def record_cost(time_str, model, in_tokens, out_tokens, cost_usd, duration_s, agent="", project=""):
    try:
        db = PROJECT_ROOT / "maestro" / "cost.db"
        date_str = time_str[:10]  # YYYY-MM-DD
        with _cost_db_lock:
            conn = sqlite3.connect(str(db))
            conn.execute("""CREATE TABLE IF NOT EXISTS costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT, date TEXT, project TEXT, agent TEXT, model TEXT,
                in_tokens INTEGER, out_tokens INTEGER, cost_usd REAL,
                duration_s REAL, task_preview TEXT
            )""")
            conn.execute(
                "INSERT INTO costs (time, date, project, agent, model, in_tokens, out_tokens, cost_usd, duration_s) VALUES (?,?,?,?,?,?,?,?,?)",
                (time_str, date_str, project or "", agent or "", model, in_tokens, out_tokens, round(cost_usd, 8), duration_s)
            )
            conn.commit()
            conn.close()
    except Exception:
        pass

def get_cost_analytics(days=30):
    """多维度费用分析"""
    try:
        db = PROJECT_ROOT / "maestro" / "cost.db"
        if not db.exists(): return None
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        # 总览
        total = conn.execute("SELECT COUNT(*) as calls, COALESCE(SUM(cost_usd),0) as cost, COALESCE(SUM(in_tokens),0) as in_tok, COALESCE(SUM(out_tokens),0) as out_tok FROM costs WHERE date >= date('now','-'||?||' days')", (days,)).fetchone()
        # 按日期
        by_date = [dict(r) for r in conn.execute("SELECT date, COUNT(*) as calls, ROUND(COALESCE(SUM(cost_usd),0),6) as cost FROM costs WHERE date >= date('now','-'||?||' days') GROUP BY date ORDER BY date", (days,))]
        # 按模型
        by_model = [dict(r) for r in conn.execute("SELECT model, COUNT(*) as calls, ROUND(COALESCE(SUM(cost_usd),0),6) as cost, SUM(in_tokens) as in_tok, SUM(out_tokens) as out_tok FROM costs WHERE date >= date('now','-'||?||' days') GROUP BY model ORDER BY cost DESC", (days,))]
        # 按 Agent
        by_agent = [dict(r) for r in conn.execute("SELECT agent, COUNT(*) as calls, ROUND(COALESCE(SUM(cost_usd),0),6) as cost FROM costs WHERE date >= date('now','-'||?||' days') AND agent != '' GROUP BY agent ORDER BY cost DESC", (days,))]
        # 按项目
        by_project = [dict(r) for r in conn.execute("SELECT project, COUNT(*) as calls, ROUND(COALESCE(SUM(cost_usd),0),6) as cost FROM costs WHERE date >= date('now','-'||?||' days') AND project != '' GROUP BY project ORDER BY cost DESC", (days,))]
        # 今日
        today = conn.execute("SELECT COUNT(*) as calls, COALESCE(SUM(cost_usd),0) as cost FROM costs WHERE date = date('now')").fetchone()
        conn.close()
        return {
            "total": dict(total), "today": dict(today),
            "by_date": by_date, "by_model": by_model,
            "by_agent": by_agent, "by_project": by_project,
        }
    except Exception:
        return None

# ═══════════════════════════════════════
# HTTP Handler
# ═══════════════════════════════════════
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
            data = get_cost_analytics(days)
            if data:
                self.send_json(data)
            else:
                self.send_json({"total": {"calls":0,"cost":0}, "today": {"calls":0,"cost":0}, "by_date":[], "by_model":[], "by_agent":[], "by_project":[]})
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

            if not task:
                self.send_json({"error": "Empty request"})
                return

            # 确定 Agent
            agent_name = force_agent or simple_route(task) or ""
            actual_task = task
            if force_agent:
                m = task.strip().split(" ", 1)
                if len(m) > 1 and m[0].startswith("@"):
                    actual_task = m[1]

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

                meta = json.dumps({"agent": agent_name or "auto", "model": "auto", "is_first": is_first, "continue": not is_first})
                self.wfile.write(f"event: meta\ndata: {meta}\n\n".encode())
                self.wfile.flush()

                # shell=True → cmd.exe 自动处理 .CMD + 引号
                safe_task = actual_task.replace('"', '\\"').replace('\n', ' ').replace('\r', ' ')
                flags = "--bare --permission-mode auto"
                if not is_first:
                    flags += " --continue"
                if agent_name:
                    flags += f' --agent "{agent_name}"'
                if proj_dir and os.path.isdir(proj_dir):
                    flags += f' --add-dir "{proj_dir}"'
                cmd_str = f'"{CLAUDE_BIN}" -p "{safe_task}" {flags}'

                start_time = time.time()
                proc = subprocess.Popen(cmd_str, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        encoding='utf-8', errors='replace', bufsize=1,
                                        cwd=str(PROJECT_ROOT), shell=True)
                out_chars = 0
                for line in iter(proc.stdout.readline, ''):
                    if not line: break
                    stripped = line.rstrip('\n\r')
                    if not stripped: continue
                    out_chars += len(stripped)
                    try:
                        self.wfile.write(f"data: {json.dumps({'content': stripped + chr(10)})}\n\n".encode())
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        proc.kill()
                        break

                proc.wait(timeout=10)
                elapsed = time.time() - start_time
                in_tokens = len(task) // 4
                out_tokens = out_chars // 2
                cost = estimate_cost("deepseek-v4-pro", in_tokens, out_tokens)
                self.wfile.write(f"event: done\ndata: {json.dumps({'elapsed': round(elapsed,1), 'cost': round(cost,6), 'in_tokens': in_tokens, 'out_tokens': out_tokens})}\n\n".encode())
                self.wfile.flush()

                record_cost(time.strftime("%Y-%m-%d %H:%M:%S"), "deepseek-v4-pro", in_tokens, out_tokens, cost, elapsed, agent_name, proj_dir or "")

            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as e:
                try:
                    self.wfile.write(f"data: {json.dumps({'error': str(e)})}\n\n".encode())
                    self.wfile.flush()
                except: pass

        elif path == "/api/route":
            task = body.get("task", "")
            agent = simple_route(task)
            self.send_json({"agent": agent or "coder", "method": "keyword"})

        elif path == "/api/orchestrate":
            # 透传给 Claude Code Workflow
            task = body.get("task", "")
            proj_dir = body.get("proj_dir", "")
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

            try:
                safe_task = task.replace('\n', ' ').replace('\r', ' ')
                cmd = ["cmd", "/c", CLAUDE_BIN, "-p", safe_task, "--bare", "--permission-mode", "auto", "--agent", "orchestrator"]
                if proj_dir and os.path.isdir(proj_dir):
                    cmd += ["--add-dir", proj_dir]

                self.wfile.write(f"event: phase\ndata: {json.dumps({'msg': 'orchestrator 分析中…'})}\n\n".encode())
                self.wfile.flush()

                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        encoding='utf-8', errors='replace', bufsize=1,
                                        cwd=str(PROJECT_ROOT))
                out_chars = 0
                for line in iter(proc.stdout.readline, ''):
                    if not line: break
                    stripped = line.rstrip('\n\r')
                    if not stripped: continue
                    out_chars += len(stripped)
                    try:
                        self.wfile.write(f"data: {json.dumps({'content': stripped + chr(10)})}\n\n".encode())
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        proc.kill()
                        break

                proc.wait(timeout=10)
                self.wfile.write(f"event: done\ndata: {json.dumps({'summary': '调度完成'})}\n\n".encode())
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as e:
                try:
                    self.wfile.write(f"event: error\ndata: {json.dumps({'msg': str(e)})}\n\n".encode())
                    self.wfile.flush()
                except: pass

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
    httpd = HTTPServer(("127.0.0.1", PORT), Handler)
    httpd.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    print(f"\n  Agency v{AGENCY_VERSION}")
    print(f"  Claude Code config: {_claude_dir}")
    print(f"  http://localhost:{PORT}\n")
    httpd.serve_forever()
