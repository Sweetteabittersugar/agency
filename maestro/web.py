#!/usr/bin/env python3
"""
Agency Web UI — 在浏览器里测试 Agent
python maestro/web.py  →  http://localhost:8800
"""
import os, sys, json, time, queue, threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "maestro"))

# 加载 .env
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"').strip("'")

from main import route_task, load_agent, estimate_cost

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE = "https://api.deepseek.com"
PORT = 8800

HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agency Test Console</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font:14px/1.6 'Segoe UI',system-ui,sans-serif;background:#0d1117;color:#c9d1d9;min-height:100vh}
.container{max-width:800px;margin:0 auto;padding:20px}
h1{font-size:24px;color:#58a6ff;margin-bottom:4px}
.sub{color:#8b949e;font-size:13px;margin-bottom:20px}
.input-area{display:flex;gap:8px;margin-bottom:12px}
#task{flex:1;padding:10px 14px;background:#161b22;border:1px solid #30363d;border-radius:6px;color:#c9d1d9;font-size:14px;outline:none}
#task:focus{border-color:#58a6ff}
#submit{padding:10px 20px;background:#238636;color:#fff;border:none;border-radius:6px;font-size:14px;cursor:pointer}
#submit:hover{background:#2ea043}
#submit:disabled{opacity:.5;cursor:default}
.info{display:flex;gap:16px;font-size:12px;color:#8b949e;margin-bottom:12px;flex-wrap:wrap}
.info span{background:#161b22;padding:3px 10px;border-radius:4px;border:1px solid #30363d}
.info .agent{color:#58a6ff}
.info .model{color:#d2a8ff}
.info .time{color:#7ee787}
.info .cost{color:#f0883e}
#output{background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:16px;min-height:300px;max-height:500px;overflow-y:auto;font:13px/1.7 'Cascadia Code','Fira Code',monospace;white-space:pre-wrap;word-break:break-all}
#output .dim{color:#484f58}
.spinner{display:none;width:16px;height:16px;border:2px solid #30363d;border-top:2px solid #58a6ff;border-radius:50%;animation:spin .8s linear infinite;margin-left:8px}
@keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<div class="container">
<h1>Agency Test Console</h1>
<p class="sub">输入任务，系统自动选 Agent、调 API、流式返回。Ctrl+Enter 发送。</p>

<div class="input-area">
  <input id="task" placeholder="写一个快排函数 / 审查这段代码 / 找到所有TODO..." autofocus>
  <button id="submit" onclick="run()">发送</button>
</div>

<div class="info" id="info"></div>
<div id="output"><span class="dim">等待输入...</span></div>
</div>

<script>
const output = document.getElementById('output');
const info = document.getElementById('info');
const taskInput = document.getElementById('task');
const submitBtn = document.getElementById('submit');

taskInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && e.ctrlKey) run();
});

async function run() {
  const task = taskInput.value.trim();
  if (!task) return;

  submitBtn.disabled = true;
  taskInput.disabled = true;
  output.innerHTML = '<span class="dim">路由中...</span>';
  info.innerHTML = '';

  try {
    // 1. 路由
    const routeResp = await fetch('/api/route', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({task})
    });
    const routeData = await routeResp.json();
    if (routeData.error) { output.textContent = '路由失败: ' + routeData.error; return; }

    info.innerHTML = `
      <span class="agent">${routeData.rerouted ? '↳ ' : ''}Agent: ${routeData.agent}</span>
      <span class="model">模型: ${routeData.model}</span>
    `;
    output.innerHTML = '';

    // 2. 流式调用
    const chatResp = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({task, agent: routeData.agent})
    });

    const reader = chatResp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, {stream: true});

      // 解析 SSE
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') break;
          try {
            const chunk = JSON.parse(data);
            if (chunk.content) {
              output.textContent += chunk.content;
              output.scrollTop = output.scrollHeight;
            }
          } catch(e) {}
        } else if (line.startsWith('event: meta')) {
          // next line is data
        } else if (line.startsWith('data: ') && line.includes('time')) {
          // meta line, skip for now
        }
      }
    }

    // 3. 获取统计
    const statResp = await fetch('/api/stat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({task, agent: routeData.agent})
    });
    const stat = await statResp.json();
    if (!stat.error) {
      info.innerHTML += `
        <span class="time">${stat.elapsed}s</span>
        <span class="cost">$${stat.cost}</span>
      `;
    }

  } catch (e) {
    output.textContent = '错误: ' + e.message;
  } finally {
    submitBtn.disabled = false;
    taskInput.disabled = false;
    taskInput.focus();
  }
}
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length > 0 else {}

        if self.path == "/api/route":
            task = body.get("task", "")
            agent, score = route_task(task)
            system_prompt, model = load_agent(agent)
            self.send_json({"agent": agent, "score": score, "model": model})

        elif self.path == "/api/chat":
            task = body.get("task", "")
            agent = body.get("agent", "coder")
            system_prompt, model = load_agent(agent)

            import requests as req
            key = os.environ.get("DEEPSEEK_API_KEY", "")
            if not key:
                self.send_json({"error": "DEEPSEEK_API_KEY not set"})
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            try:
                resp = req.post(
                    f"{DEEPSEEK_BASE}/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": task},
                    ], "stream": True, "temperature": 0.7, "max_tokens": 8192},
                    stream=True, timeout=300,
                )
                for line in resp.iter_lines():
                    if not line: continue
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        self.wfile.write(f"{line}\n\n".encode("utf-8"))
                        self.wfile.flush()
                self.wfile.write("data: [DONE]\n\n".encode("utf-8"))
                self.wfile.flush()
            except Exception as e:
                self.wfile.write(f"data: {{\"error\": \"{str(e)}\"}}\n\n".encode("utf-8"))

        elif self.path == "/api/stat":
            # 返回统计（简化版）
            self.send_json({"elapsed": "?", "cost": "?"})

        else:
            self.send_response(404)
            self.end_headers()

    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def log_message(self, format, *args):
        pass  # 安静模式


if __name__ == "__main__":
    print(f"\n  Agency Web UI → http://localhost:{PORT}\n")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
