"""Agent 工厂 — AI 生成 + 保存 Agent .md"""
import json
import os
import re
import time
import subprocess
import logging
from pathlib import Path

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def handle_generate(handler, body):
    """POST /api/agent-generate — SSE 流式生成 Agent .md"""
    from maestro.shared import CLAUDE_BIN, ISOLATED_CONFIG, build_isolated_env
    requirement = body.get("requirement", "")
    api_key = body.get("api_key", "")
    api_provider = body.get("api_provider", "")

    if not requirement:
        handler.send_json({"error": "请描述你想创建的 Agent 功能需求。例如：\"一个擅长写 Python 测试的 Agent\""}, 400)
        return True
    if not CLAUDE_BIN:
        handler.send_json({"error": "Claude CLI not found"}, 500)
        return True

    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "close")
    handler.end_headers()

    prompt = f"""根据以下需求生成一个 Claude Code Agent 的 .md 定义文件。严格按以下格式输出，不要输出其他内容：

---
name: <英文小写连字符名>
description: <一句话中文描述>
model: <sonnet|haiku|opus>
tools: <逗号分隔的工具列表，如 Read,Write,Edit,Bash,Grep,Glob>
---

<Agent 的 system prompt，中文，简洁>

需求: {requirement}"""

    proc = None
    full_output = ""
    try:
        cmd = [CLAUDE_BIN, "-p", prompt, "--bare", "--permission-mode", "auto"]

        iso_env = build_isolated_env(api_key, api_provider)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                encoding='utf-8', errors='replace', bufsize=1,
                                cwd=str(PROJECT_ROOT), env=iso_env)
        from maestro.proc_manager import track_proc
        track_proc(proc)
        for line in iter(proc.stdout.readline, ''):
            if not line:
                break
            stripped = line.rstrip('\n\r')
            if not stripped:
                continue
            full_output += stripped + "\n"
            try:
                handler.wfile.write(f"data: {json.dumps({'content': stripped + chr(10)}, ensure_ascii=False)}\n\n".encode())
                handler.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                break
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            pass
    except Exception as e:
        try:
            handler.wfile.write(f"data: {json.dumps({'error': str(e)})}\n\n".encode())
            handler.wfile.flush()
        except Exception:
            pass
    finally:
        if proc:
            from maestro.proc_manager import kill_proc, untrack_proc
            kill_proc(proc)
            untrack_proc(proc)
    return True


def handle_create(handler, body):
    """POST /api/agent-create — 保存生成的 Agent .md 到 agents/ 目录"""
    name = body.get("name", "").strip()
    content = body.get("content", "").strip()

    if not name or not content:
        handler.send_json({"error": "缺少必填字段。请同时提供 name（Agent 名称）和 content（Agent 内容）"}, 400)
        return True
    if not re.match(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$', name):
        handler.send_json({"error": "invalid name: use lowercase letters, digits, hyphens"}, 400)
        return True

    try:
        # 写 agents/ 目录
        agent_file = PROJECT_ROOT / "agents" / f"{name}.md"
        agent_file.parent.mkdir(parents=True, exist_ok=True)
        agent_file.write_text(content, encoding="utf-8")

        # 同步到 .claude/agents/
        claude_dir = PROJECT_ROOT / ".claude" / "agents"
        claude_dir.mkdir(parents=True, exist_ok=True)
        (claude_dir / f"{name}.md").write_text(content, encoding="utf-8")

        # 同步到 .claude-isolated/agents/
        iso_dir = PROJECT_ROOT / ".claude-isolated" / "agents"
        iso_dir.mkdir(parents=True, exist_ok=True)
        (iso_dir / f"{name}.md").write_text(content, encoding="utf-8")

        handler.send_json({"ok": True, "name": name})
        log.info(f"Agent created: {name}")
    except Exception as e:
        handler.send_json({"error": str(e)}, 500)
    return True
