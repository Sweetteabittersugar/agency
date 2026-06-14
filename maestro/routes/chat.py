"""POST /api/chat — SSE 流式聊天（最核心路由）"""

import json
import os
import time
import logging
from pathlib import Path
from maestro.routes.operations import record_operation

log = logging.getLogger(__name__)


def handle_chat(handler, body):
    from maestro.shared import (
        PROJECT_ROOT,
        CLAUDE_BIN,
        _claude_dir_path,
        build_isolated_env,
    )
    from maestro.main import simple_route
    from maestro.agent_parser import parse_agent_md
    from maestro.web_cost import record_cost

    task = body.get("task", "")
    force_agent = body.get("force_agent", "")
    proj_dir = body.get("proj_dir", "")
    api_key = body.get("api_key", "")
    api_provider = body.get("api_provider", "")

    # 后台配置优先：环境变量有 Key 时直接使用，前端不必传
    if not api_key:
        from maestro.models import get_provider_config
        _, env_key, _ = get_provider_config()
        api_key = env_key
    if not api_provider:
        api_provider = os.environ.get("PROVIDER", "deepseek")

    if not task:
        handler.send_json({"error": "请求为空。请在消息框中输入任务描述后发送"}, 400)
        return True

    if not api_key:
        handler.send_json(
            {
                "ok": False,
                "error": "未配置 API Key",
                "friendly_message": "还没有配置 API Key，请在设置中添加",
                "action": "open_settings",
                "provider_hint": "支持 DeepSeek / Anthropic / OpenAI",
            },
            400,
        )
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

    # ── 会话接续：前端传 Claude 生成的 session_id，后端用 --resume 接续 ──

    # ── 会话记录 ──
    route_source = (
        "force" if force_agent else (route_info.get("source", "auto") if route_info else "auto")
    )

    # ── Agent 注入：显式读取 agent .md，注入 model / tools ──
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
                agent_system_prompt = info.get("body", "")
                log.info(
                    f"CHAT agent injection: model={agent_model_override}, tools={agent_tools_override}, body_len={len(agent_system_prompt)}"
                )
                break
    if agent_model_override and not model:
        model = agent_model_override
    # 注入 agent 系统提示词到任务开头，确保 Claude 获得角色设定
    if agent_system_prompt:
        actual_task = (
            f"[角色设定]\n你是 {force_agent}。{agent_system_prompt}\n\n[用户任务]\n{actual_task}"
        )

    if not CLAUDE_BIN:
        handler.send_json(
            {
                "ok": False,
                "error": "Claude Code CLI 未安装",
                "friendly_message": "需要安装 Claude Code CLI 才能发送任务",
                "action": "install_claude",
                "install_cmd": "npm install -g @anthropic-ai/claude-code",
            }
        )
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
        meta = json.dumps(
            {
                "agent": agent_name or "auto",
                "model": "auto",
                "session": session_id[:8] if session_id else "new",
            }
        )
        handler.wfile.write(f"event: meta\ndata: {meta}\n\n".encode())
        handler.wfile.flush()

        # ── 进度：路由完成 ──
        _agent_display = agent_name or "auto"
        handler.wfile.write(
            f"data: {json.dumps({'progress': True, 'stage': 'routing', 'message': f'已匹配 Agent: {_agent_display}', 'agent': _agent_display})}\n\n".encode()
        )
        handler.wfile.flush()

        # MCP servers 解析（进程池和 fallback 共用）
        mcp_servers = body.get("mcp_servers", "")
        if isinstance(mcp_servers, str):
            mcp_servers = [s.strip() for s in mcp_servers.split(",") if s.strip()]

        log.info(f'CHAT start agent={agent_name or "auto"} task="{actual_task[:40]}…"')
        # 会话事件记录：路由决策写入 session_store，供时间线和会话列表使用
        try:
            from maestro.session_store import append_event
            append_event(session_id, "route_decision", {
                "agent": agent_name or "auto",
                "model": model or "auto",
                "source": route_source,
                "task_preview": actual_task[:100],
            })
        except Exception:
            pass
        start_time = time.time()
        iso_env = build_isolated_env(api_key, api_provider)
        if api_key:
            log.info(f"CHAT using user API key provider={api_provider}")

        # ── 进度：正在分配任务 ──
        handler.wfile.write(
            f"data: {json.dumps({'progress': True, 'stage': 'dispatching', 'message': '正在分配任务...'})}\n\n".encode()
        )
        handler.wfile.flush()

        # ── 持久化 Claude 进程：stream-json 双向管道 ──
        from maestro.claude_session import get_or_create

        # -- persistent Claude process --
        # Each panel has a session_id (UUID) mapped to an independent Claude process.
        # session_id is a local panel-to-process route key, NOT passed to Claude --resume.
        # Same panel reuses same process across turns; different panels get separate processes.
        session_id = body.get("session_id", "")
        is_new_session = not bool(session_id)
        if is_new_session:
            import uuid
            session_id = str(uuid.uuid4())
            # Memory injection: scan memory/ directory for relevant past learnings
            # and prepend them to the user's task so Claude sees historical context
            try:
                from maestro.memory_engine import build_injection_prefix
                actual_task = build_injection_prefix(actual_task, str(PROJECT_ROOT))
            except Exception:
                pass

        handler.wfile.write(
            f"data: {json.dumps({'progress': True, 'stage': 'executing', 'message': (agent_name or 'auto') + ' 正在执行...'})}\n\n".encode()
        )
        handler.wfile.flush()

        cs = get_or_create(session_id, str(PROJECT_ROOT), iso_env)
        if cs is None:
            handler.wfile.write(
                f"event: done\ndata: {json.dumps({'error': '无法启动 Claude 进程', 'elapsed': 0})}\n\n".encode()
            )
            handler.wfile.flush()
            return True

        # 会话事件：用户消息写入 session_store
        try:
            from maestro.session_store import append_event
            append_event(session_id, "user_message", {"content": actual_task[:200]})
        except Exception:
            pass
        elapsed = time.time() - start_time

        # 2026-06 修复：send_and_read 调用曾被误删，导致聊天链路完全断裂
        # 此行不可移除——它是整个对话管道的核心：发送任务 → 接收 Claude 流式响应
        events = cs.send_and_read(actual_task)

        # 流式输出事件
        chat_output_text = ""
        done_data = {}
        for evt in events:
            if "content" in evt:
                chat_output_text += evt["content"]
                try:
                    handler.wfile.write(
                        f"data: {json.dumps({'content': evt['content']})}\n\n".encode()
                    )
                    handler.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    log.info("CHAT client disconnected")
                    break
            elif "done" in evt:
                done_data = evt["done"]
            elif "error" in evt:
                try:
                    handler.wfile.write(
                        f"event: done\ndata: {json.dumps({'error': evt['error'], 'elapsed': 0})}\n\n".encode()
                    )
                    handler.wfile.flush()
                except Exception:
                    pass

        # 发送 done 事件——模型名从 Claude result 事件读取，不再硬编码
        in_tokens = done_data.get("in_tokens", len(task) // 4)
        out_tokens = done_data.get("out_tokens", 0)
        cache_read = done_data.get("cache_read", 0)
        cost = done_data.get("cost", 0)
        detected_model = done_data.get("model", "") or model or "deepseek-v4-flash"

        done_payload = {
            "elapsed": round(elapsed, 1),
            "cost": round(cost, 6),
            "in_tokens": in_tokens,
            "out_tokens": out_tokens,
            "session_id": session_id,
            "model": detected_model,
            # 累计统计——前端可按面板展示 token 用量
            "total_in": done_data.get("total_in", in_tokens),
            "total_out": done_data.get("total_out", out_tokens),
            "total_cost": done_data.get("total_cost", cost),
        }
        if cache_read:
            done_payload["cache_read"] = cache_read
        # 压缩状态：按模型窗口容量判断，70%警告/85%强制压缩
        try:
            comp = cs.compaction_status()
            done_payload["compaction"] = comp
        except Exception:
            pass
        try:
            handler.wfile.write(f"event: done\ndata: {json.dumps(done_payload)}\n\n".encode())
            handler.wfile.flush()
            handler.wfile.write(
                f"data: {json.dumps({'progress': True, 'stage': 'done', 'message': '执行完成'})}\n\n".encode()
            )
            handler.wfile.flush()
        except Exception:
            pass

        record_cost(
            PROJECT_ROOT,
            time.strftime("%Y-%m-%d %H:%M:%S"),
            detected_model,
            in_tokens,
            out_tokens,
            cost,
            elapsed,
            agent_name,
            proj_dir or "",
            cache_read,
            0,
            0,
            False,
            session_id or "",
        )
        # session event: agent response to session_store for timeline
        try:
            from maestro.session_store import append_event
            append_event(session_id, "agent_response", {
                "content_preview": chat_output_text[:200],
                "elapsed": round(elapsed, 1),
                "cost": round(cost, 6),
                "tokens_in": in_tokens,
                "tokens_out": out_tokens,
            })
        except Exception:
            pass
        log.info(
            f"CHAT done elapsed={elapsed:.1f}s cost=${cost:.4f} model={detected_model} session={session_id[:8] if session_id else 'new'}"
        )

        try:
            record_operation(
                agent_name or "auto",
                "chat_session",
                actual_task[:200],
                f"elapsed={elapsed:.1f}s cost=${cost:.4f} tokens={in_tokens}+{out_tokens}",
            )
        except Exception:
            pass

    except Exception as e:
        try:
            handler.wfile.write(
                f"event: done\ndata: {json.dumps({'error': str(e), 'elapsed': 0})}\n\n".encode()
            )
            handler.wfile.flush()
        except Exception:
            pass
    return True
