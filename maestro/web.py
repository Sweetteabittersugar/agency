#!/usr/bin/env python3
"""
Agency API Server
  python maestro/web.py   ->   http://localhost:8800
"""
import os, sys, json, time, yaml, sqlite3, threading, hashlib
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "maestro"))

# Load .env
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"').strip("'")

from models import get_provider_config, resolve_model, estimate_cost
from main import route_task, route_with_cache, load_agent, ROUTING, record_agent_result, get_agent_stats, semantic_match
import requests as req

PORT = 8800
AGENCY_VERSION = (PROJECT_ROOT / "VERSION").read_text().strip() if (PROJECT_ROOT / "VERSION").exists() else "0.1.0"

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            # Serve index.html
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
                self.wfile.write(b"<h1>Agency API Server</h1><p>Frontend not found. Place webui/index.html in the project root.</p>")
            return

        # Serve static files from webui/
        static_path = PROJECT_ROOT / "webui" / path.lstrip("/")
        if static_path.exists() and static_path.is_file():
            content_type = "text/html"
            if path.endswith(".css"): content_type = "text/css"
            elif path.endswith(".js"): content_type = "application/javascript"
            elif path.endswith(".svg"): content_type = "image/svg+xml"
            elif path.endswith(".png"): content_type = "image/png"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(static_path.read_bytes())
            return

        # API endpoints
        if path == "/api/agents":
            agents_list = []
            for f in sorted((PROJECT_ROOT / "agents").glob("*.md")):
                content = f.read_text(encoding="utf-8")
                fm = {}
                body = content
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        try: fm = yaml.safe_load(parts[1]) or {}
                        except: pass
                        body = parts[2].strip()
                agents_list.append({
                    "name": f.stem, "description": fm.get("description", ""),
                    "model": fm.get("model", ""), "tools": fm.get("tools", []),
                    "prompt_preview": body[:200], "prompt_full": body,
                    "keywords": ROUTING.get(f.stem, [])
                })
            self.send_json(agents_list)
        elif path == "/api/version":
            self.send_json({"version": AGENCY_VERSION})
        elif path == "/api/settings":
            base_url, api_key, _ = get_provider_config()
            self.send_json({
                "provider_type": os.environ.get("PROVIDER", "deepseek"),
                "base_url": base_url, "has_key": bool(api_key),
                "model_mapping": {
                    "heavy": resolve_model("opus"), "standard": resolve_model("sonnet"), "light": resolve_model("haiku")
                },
                "default_model": os.environ.get("DEFAULT_MODEL", "deepseek-v4-pro"),
                "version": AGENCY_VERSION
            })
        elif path == "/api/cost":
            try:
                db = PROJECT_ROOT / "maestro" / "cost.db"
                if db.exists():
                    conn = sqlite3.connect(str(db))
                    cur = conn.execute("SELECT COUNT(*), COALESCE(SUM(cost_usd),0) FROM costs")
                    total_calls, total_cost = cur.fetchone()
                    cur = conn.execute("SELECT model, COUNT(*), COALESCE(SUM(cost_usd),0) FROM costs GROUP BY model")
                    by_model = [{"model": r[0], "calls": r[1], "cost": round(r[2], 4)} for r in cur.fetchall()]
                    conn.close()
                    self.send_json({"total_calls": total_calls, "total_cost": round(total_cost or 0, 4), "by_model": by_model})
                else:
                    self.send_json({"total_calls": 0, "total_cost": 0, "by_model": []})
            except Exception as e:
                self.send_json({"error": str(e)})
        elif path == "/api/cost-recent":
            try:
                db = PROJECT_ROOT / "maestro" / "cost.db"
                if db.exists():
                    conn = sqlite3.connect(str(db))
                    rows = conn.execute("SELECT time, channel, model, in_tokens, out_tokens, cost_usd, duration_s FROM costs ORDER BY id DESC LIMIT 20").fetchall()
                    conn.close()
                    self.send_json([{"time": r[0], "channel": r[1], "model": r[2], "in_tokens": r[3], "out_tokens": r[4], "cost": r[5], "duration": r[6]} for r in rows])
                else:
                    self.send_json([])
            except Exception as e:
                self.send_json({"error": str(e)})
        elif path == "/api/agent-stats":
            self.send_json(get_agent_stats())
        else:
            self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length > 0 else {}
        path = urlparse(self.path).path

        if path == "/api/chat":
            messages = body.get("messages", [])
            task = body.get("task", "")
            force_agent = body.get("force_agent", "")
            model_override = body.get("model", "")

            if not messages and not task:
                self.send_json({"error": "Empty request"})
                return

            # Route
            actual_task = task
            if not messages:
                if not task:
                    self.send_json({"error": "No task or messages"})
                    return
                actual_task = task

            agent_name, score, conf, method = route_with_cache(actual_task, force_agent or None)
            system_prompt, agent_model = load_agent(agent_name)
            actual_model = resolve_model(agent_model)
            if model_override:
                actual_model = model_override

            base_url, api_key, headers = get_provider_config()
            if not base_url:
                self.send_json({"error": "未配置 API Key。请在 .env 中设置。"})
                return

            # Build messages
            if not messages:
                api_messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": actual_task},
                ]
            else:
                # Insert system prompt if not present
                if not any(m.get("role") == "system" for m in messages):
                    api_messages = [{"role": "system", "content": system_prompt}] + messages
                else:
                    api_messages = messages

            # SSE stream
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            # Send metadata
            meta = json.dumps({"agent": agent_name, "model": actual_model, "confidence": conf, "method": method})
            self.wfile.write(f"event: meta\ndata: {meta}\n\n".encode())
            self.wfile.flush()

            try:
                resp = req.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json={"model": actual_model, "messages": api_messages, "stream": True, "temperature": 0.7, "max_tokens": 8192},
                    stream=True, timeout=300,
                )

                in_tokens = sum(len(m.get("content","")) // 4 for m in api_messages)
                out_chars = 0
                start_time = time.time()

                for line in resp.iter_lines():
                    if not line: continue
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]": break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                out_chars += len(content)
                                chunk_data = json.dumps({"content": content})
                                self.wfile.write(f"data: {chunk_data}\n\n".encode())
                                self.wfile.flush()
                        except: pass

                elapsed = time.time() - start_time
                out_tokens = out_chars // 2
                cost = estimate_cost(actual_model, in_tokens, out_tokens)

                self.wfile.write(f"event: done\ndata: {json.dumps({'elapsed': round(elapsed,1), 'cost': round(cost,6), 'in_tokens': in_tokens, 'out_tokens': out_tokens})}\n\n".encode())
                self.wfile.flush()

                record_agent_result(agent_name, True)

            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as e:
                try:
                    self.wfile.write(f"data: {json.dumps({'error': str(e)})}\n\n".encode())
                    self.wfile.flush()
                except: pass
                record_agent_result(agent_name, False)

        elif path == "/api/route":
            task = body.get("task", "")
            force_agent = body.get("force_agent", "")
            agent, score, conf, method = route_with_cache(task, force_agent or None)
            _, model = load_agent(agent)
            self.send_json({
                "agent": agent, "score": score, "confidence": round(conf, 3),
                "method": method, "model": resolve_model(model),
            })

        elif path == "/api/route-test":
            task = body.get("task", "")
            results = []
            for agent_name, keywords in ROUTING.items():
                score = sum(len(kw) * 2 for kw in keywords if kw.lower() in task.lower())
                if score > 0:
                    results.append({"agent": agent_name, "score": score})
            results.sort(key=lambda x: x["score"], reverse=True)
            self.send_json(results)

        elif path == "/api/agent-generate":
            requirement = body.get("requirement", "")
            _, model = load_agent("coder")
            gen_prompt = f"你是一个Agent设计专家。根据需求生成完整Agent定义文件...\n需求：{requirement}"
            # Stream the generation
            base_url, api_key, headers = get_provider_config()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            try:
                resp = req.post(f"{base_url}/chat/completions", headers=headers,
                    json={"model": resolve_model("sonnet"), "messages": [{"role":"user","content":gen_prompt}], "stream":True},
                    stream=True, timeout=120)
                for line in resp.iter_lines():
                    if not line: continue
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]": break
                        try:
                            chunk = json.loads(data)
                            c = chunk.get("choices",[{}])[0].get("delta",{}).get("content","")
                            if c:
                                self.wfile.write(f"data: {json.dumps({'content':c})}\n\n".encode())
                                self.wfile.flush()
                        except: pass
                self.wfile.write("data: [DONE]\n\n".encode())
                self.wfile.flush()
            except Exception as e:
                self.wfile.write(f"data: {json.dumps({'error':str(e)})}\n\n".encode())
                self.wfile.flush()

        elif path == "/api/agent-create":
            name = body.get("name", "").strip()
            content = body.get("content", "").strip()
            if not name or not content:
                self.send_json({"error": "name and content required"})
                return
            # Validate name
            import re
            if not re.match(r'^[a-z0-9-]+$', name):
                self.send_json({"error": "name must be lowercase letters, numbers, hyphens"})
                return
            agent_file = PROJECT_ROOT / "agents" / f"{name}.md"
            agent_file.write_text(content, encoding="utf-8")
            self.send_json({"ok": True, "path": str(agent_file)})

        else:
            self.send_json({"error": "not found"}, 404)

    def send_json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        pass

def _kill_old():
    """Kill existing python processes listening on our port."""
    try:
        import subprocess, platform
        if platform.system() == "Windows":
            out = subprocess.check_output(
                f'netstat -ano | findstr "127.0.0.1:{PORT} " | findstr "LISTENING"',
                shell=True, text=True, timeout=5
            )
            pids = set()
            for line in out.strip().split('\n'):
                parts = line.strip().split()
                if len(parts) >= 5 and parts[-1].isdigit():
                    pid = int(parts[-1])
                    if pid != os.getpid():
                        pids.add(str(pid))
            for pid in pids:
                subprocess.run(f'taskkill //F //PID {pid}', shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"  Killed old server (PID {pid})")
    except Exception:
        pass

if __name__ == "__main__":
    import webbrowser
    _kill_old()
    threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    print(f"\n  Agency v{AGENCY_VERSION}")
    print(f"  http://localhost:{PORT}\n")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
