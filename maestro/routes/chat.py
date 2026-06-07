"""POST /api/chat — SSE 流式聊天（最核心路由）"""
import json
import os
import re
import time
import subprocess
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def handle_chat(handler, body):
    from maestro.shared import (
        PROJECT_ROOT, CLAUDE_BIN, ISOLATED_CONFIG, _claude_dir_path,
        simple_route, _scan_subagents, build_isolated_env,
    )
    from maestro.agent_parser import parse_agent_md
    from maestro.proc_manager import track_proc, untrack_proc, kill_proc
    from maestro.models import estimate_cost
    from maestro.web_cost import record_cost
    from maestro.harness.jsonl_parser import analyze_session

    task = body.get("task", "")
    force_agent = body.get("force_agent", "")
    proj_dir = body.get("proj_dir", "")
    api_key = body.get("api_key", "")
    api_provider = body.get("api_provider", "")

    if not task:
        handler.send_json({"error": "Empty request"})
        return True

    # 确定 Agent
    route_info = simple_route(task) if not force_agent else None
    agent_name = force_agent or (route_info["agent"] if route_info else "")
    model = body.get("model", "") or (route_info.get("model", "") if route_info else "")
    actual_task = task
    if force_agent:
        m = task.strip().split(" ", 1)
        if len(m) > 1 and m[0].startswith("@"):
            actual_task = m[1]

    # ── Agent 注入：显式读取 agent .md，注入 model / tools ──
    agent_model_override = ""
    agent_tools_override = []
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
                log.info(f"CHAT agent injection: model={agent_model_override}, tools={agent_tools_override}")
                break
    if agent_model_override and not model:
        model = agent_model_override

    if not CLAUDE_BIN:
        handler.send_json({"error": "Claude Code CLI 未安装。请安装后重试。"})
        return True

    # SSE
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "close")
    handler.end_headers()

    try:
        session_id = body.get("session_id", "")
        is_new = body.get("is_new_session", True)
        meta = json.dumps({"agent": agent_name or "auto", "model": "auto", "session": session_id[:8] if session_id else "new"})
        handler.wfile.write(f"event: meta\ndata: {meta}\n\n".encode())
        handler.wfile.flush()

        safe_task = actual_task.replace('\n', ' ').replace('\r', ' ')
        safe_task = re.sub(r'[\$\`\(\)\{\}\;\&\|\<\>\%\^\!]', '', safe_task)
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
            iso_env = build_isolated_env(api_key, api_provider)
            if api_key:
                log.info(f'CHAT using user API key provider={api_provider}')
            t0 = time.time()
            proc = subprocess.Popen(cmd_str, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    encoding='utf-8', errors='replace', bufsize=1,
                                    cwd=str(PROJECT_ROOT), shell=True, env=iso_env)
            log.info(f'CHAT proc spawn {(time.time()-t0)*1000:.0f}ms PID={proc.pid}')
            track_proc(proc)
            first_line = True
            for line in iter(proc.stdout.readline, ''):
                if first_line:
                    log.info(f'CHAT first output after {(time.time()-start_time)*1000:.0f}ms')
                    first_line = False
                if not line: break
                stripped = line.rstrip('\n\r')
                if not stripped: continue
                out_chars += len(stripped)
                display = stripped
                if len(stripped) > 500:
                    display = '<details><summary>📄 展开 (' + str(len(stripped)) + '字符)</summary><pre>' + stripped.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') + '</pre></details>'
                elif stripped.startswith('[Tool:') or stripped.startswith('Tool:'):
                    display = '<div class="tool-tag">🔧 ' + stripped.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') + '</div>'
                try:
                    handler.wfile.write(f"data: {json.dumps({'content': display + chr(10)})}\n\n".encode())
                    handler.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    log.info('CHAT client disconnected, killing proc')
                    break

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
                        log.debug(f"JSONL analysis failed for session {session_id}, using char estimation")
            cost = estimate_cost(detected_model, in_tokens, out_tokens)
            try:
                handler.wfile.write(f"event: done\ndata: {json.dumps({'elapsed': round(elapsed,1), 'cost': round(cost,6), 'in_tokens': in_tokens, 'out_tokens': out_tokens})}\n\n".encode())
                handler.wfile.flush()
            except Exception:
                pass
            record_cost(PROJECT_ROOT, time.strftime("%Y-%m-%d %H:%M:%S"), detected_model, in_tokens, out_tokens, cost, elapsed, agent_name, proj_dir or "",
                        cache_read, cache_write, cache_saved, is_estimated, session_id or "")
            log.info(f'CHAT done elapsed={elapsed:.1f}s cost=${cost:.4f} model={detected_model} estimated={is_estimated}')
        finally:
            if proc:
                kill_proc(proc)
                untrack_proc(proc)
                log.info('CHAT proc cleaned')

    except Exception as e:
        try:
            handler.wfile.write(f"data: {json.dumps({'error': str(e)})}\n\n".encode())
            handler.wfile.flush()
        except Exception:
            pass
    return True
