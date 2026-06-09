"""POST /api/chat — SSE 流式聊天（最核心路由）"""
import json
import os
import re
import time
import subprocess
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# ── 聊天上下文缓存（按 session_id 索引）──
_chat_contexts: dict[str, "ContextLayer"] = {}

# ── 进程池执行辅助 ──
_POOL_FAILURES = 0  # 连续失败计数，超过阈值后降级为直接 subprocess
_POOL_FAILURE_THRESHOLD = 3


def _try_pool_execute(actual_task, agent_name, model, session_id, is_new,
                      proj_dir, iso_env, agent_tools_override, mcp_servers):
    """尝试通过进程池执行任务，返回 (output_lines_list, None)。
    池不可用或失败时返回 (None, None)。"""
    global _POOL_FAILURES
    if _POOL_FAILURES >= _POOL_FAILURE_THRESHOLD:
        return None, None

    try:
        from maestro.process_pool import get_pool
    except ImportError:
        return None, None

    pool = get_pool()
    if pool is None or not pool.available:
        _POOL_FAILURES += 1
        return None, None

    payload = {
        "task": actual_task,
        "agent": agent_name or "",
        "model": model or "",
        "session_id": session_id or "",
        "is_new_session": is_new,
        "proj_dir": proj_dir or "",
        "tools": agent_tools_override,
        "mcp_servers": mcp_servers if isinstance(mcp_servers, list) else [],
        "bare": True,
        "permission_mode": "auto",
        "env": iso_env,
    }

    try:
        raw = pool.execute(payload, timeout=300)
    except Exception:
        _POOL_FAILURES += 1
        log.debug("POOL execute exception, fallback to subprocess", exc_info=True)
        return None, None

    if raw is None:
        _POOL_FAILURES += 1
        return None, None

    _POOL_FAILURES = 0  # 成功后重置
    lines = raw.split("\n")
    output_lines = []
    for line in lines:
        s = line.rstrip("\r")
        if s == '{"type":"done"}' or s == '{"type":"error"}':
            break
        output_lines.append(s)
    return output_lines, None


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
        handler.send_json({"error": "请求为空。请在消息框中输入任务描述后发送"})
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

    # ── 会话上下文注入 ──
    session_id = body.get("session_id", "")
    chat_ctx = None
    if session_id:
        from maestro.context_layer import ContextLayer
        if session_id not in _chat_contexts:
            _chat_contexts[session_id] = ContextLayer(session_id, PROJECT_ROOT)
        chat_ctx = _chat_contexts[session_id]
        ctx_summary = chat_ctx.get_context_for_agent(agent_name or "chat")
        if ctx_summary:
            actual_task = f"[上文摘要]\n{ctx_summary}\n\n[当前问题]\n{actual_task}"

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

    # ── 思考/工具输出过滤 ──
    show_thinking = os.environ.get("SHOW_THINKING", "false").lower() == "true"
    show_tools = os.environ.get("SHOW_TOOLS", "false").lower() == "true"

    # SSE
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "close")
    handler.end_headers()
    # 即时回复 ack
    handler.wfile.write(f"event: ack\ndata: {json.dumps({'ok': True})}\n\n".encode())
    handler.wfile.flush()

    try:
        session_id = body.get("session_id", "")
        is_new = body.get("is_new_session", True)
        meta = json.dumps({"agent": agent_name or "auto", "model": "auto", "session": session_id[:8] if session_id else "new"})
        handler.wfile.write(f"event: meta\ndata: {meta}\n\n".encode())
        handler.wfile.flush()

        # MCP servers 解析（进程池和 fallback 共用）
        mcp_servers = body.get("mcp_servers", "")
        if isinstance(mcp_servers, str):
            mcp_servers = [s.strip() for s in mcp_servers.split(",") if s.strip()]

        log.info(f'CHAT start agent={agent_name or "auto"} task="{actual_task[:40]}…"')
        start_time = time.time()
        iso_env = build_isolated_env(api_key, api_provider)
        if api_key:
            log.info(f'CHAT using user API key provider={api_provider}')

        # ── 优先尝试进程池（长连接复用）──
        pool_output, _pool_err = _try_pool_execute(
            actual_task, agent_name, model, session_id, is_new,
            proj_dir, iso_env, agent_tools_override, mcp_servers,
        )

        proc = None
        out_chars = 0
        chat_output_text = ""
        used_pool = False

        try:
            if pool_output is not None:
                # ── 进程池路径：直接流式输出预读结果 ──
                used_pool = True
                log.info(f'CHAT using pool ({len(pool_output)} lines)')
                for stripped in pool_output:
                    if not stripped:
                        continue
                    # 思考/工具过滤
                    if not show_thinking and (
                        stripped.startswith("[Thinking]") or stripped.startswith("Thinking:")
                    ):
                        continue
                    if not show_tools and (
                        stripped.startswith("[Tool:") or stripped.startswith("Tool:")
                    ):
                        continue
                    out_chars += len(stripped)
                    chat_output_text += stripped + "\n"
                    display = stripped
                    if len(stripped) > 500:
                        display = '<details><summary>📄 展开 (' + str(len(stripped)) + '字符)</summary><pre>' + stripped.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') + '</pre></details>'
                    elif stripped.startswith('[Tool:') or stripped.startswith('Tool:'):
                        display = '<div class="tool-tag">🔧 ' + stripped.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') + '</div>'
                    try:
                        handler.wfile.write(f"data: {json.dumps({'content': display + chr(10)})}\n\n".encode())
                        handler.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        log.info('CHAT client disconnected (pool)')
                        break
            else:
                # ── 回退路径：传统 subprocess.Popen ──
                log.info('CHAT falling back to subprocess.Popen')
                t0 = time.time()
                cmd = [CLAUDE_BIN, "-p", actual_task, "--bare", "--permission-mode", "auto"]
                if session_id:
                    if is_new: cmd += ["--session-id", session_id]
                    else: cmd += ["--resume", session_id]
                if agent_name: cmd += ["--agent", agent_name]
                if model: cmd += ["--model", model]
                if agent_tools_override: cmd += ["--tools", ",".join(agent_tools_override)]
                if agent_tools_override:
                    has_mcp = any(t.startswith("mcp__") for t in agent_tools_override)
                    if not has_mcp and mcp_servers:
                        cmd += ["--tools", ",".join(agent_tools_override + ["mcp__plugin_" + s + "_" + s + "__*" for s in mcp_servers])]
                if proj_dir and os.path.isdir(proj_dir): cmd += ["--add-dir", proj_dir]

                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        encoding='utf-8', errors='replace', bufsize=1,
                                        cwd=str(PROJECT_ROOT), env=iso_env)
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
                    # 思考/工具过滤
                    if not show_thinking and (
                        stripped.startswith("[Thinking]") or stripped.startswith("Thinking:")
                    ):
                        continue
                    if not show_tools and (
                        stripped.startswith("[Tool:") or stripped.startswith("Tool:")
                    ):
                        continue
                    out_chars += len(stripped)
                    chat_output_text += stripped + "\n"
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
                done_payload = {'elapsed': round(elapsed,1), 'cost': round(cost,6), 'in_tokens': in_tokens, 'out_tokens': out_tokens}
                if used_pool:
                    done_payload['via'] = 'pool'
                handler.wfile.write(f"event: done\ndata: {json.dumps(done_payload)}\n\n".encode())
                handler.wfile.flush()
            except Exception:
                pass
            record_cost(PROJECT_ROOT, time.strftime("%Y-%m-%d %H:%M:%S"), detected_model, in_tokens, out_tokens, cost, elapsed, agent_name, proj_dir or "",
                        cache_read, cache_write, cache_saved, is_estimated, session_id or "")
            log.info(f'CHAT done elapsed={elapsed:.1f}s cost=${cost:.4f} model={detected_model} estimated={is_estimated} via={"pool" if used_pool else "subprocess"}')

            # ── 保存会话上下文 ──
            if chat_ctx and chat_output_text:
                turn_key = f"turn_{int(time.time())}"
                chat_ctx.set_short_term(turn_key, {
                    "q": actual_task[:1000],
                    "a": chat_output_text[:2000],
                })
                chat_ctx.set_short_term("last_turn", turn_key)
                chat_ctx.log_episodic(
                    agent_name or "chat", "chat_turn",
                    f"Q: {actual_task[:200]} | A: {chat_output_text[:200]}",
                    elapsed_ms=elapsed * 1000,
                )
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
