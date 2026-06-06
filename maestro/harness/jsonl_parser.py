"""
JSONL 解析器 — 从 Claude Code session JSONL 中提取结构化数据
复用 transcript-parser.py 的解析逻辑，精简为 Harness 所需字段
"""
import json, os, time, threading
from pathlib import Path
from typing import Optional


def find_latest_session(project_root: str = None) -> Optional[dict]:
    """找到当前项目最新的 session JSONL 文件"""
    if not project_root:
        return None
    # Claude Code sessions 存储在 ~/.claude/projects/<slug>/
    import os as _os
    home = Path.home()
    slug = project_root.replace(":\\", "--").replace("\\", "-").replace("/", "-").lstrip("-")
    proj_dir = home / ".claude" / "projects" / slug
    if not proj_dir.exists():
        return None

    jsonl_files = sorted(proj_dir.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not jsonl_files:
        return None

    latest = jsonl_files[0]
    return {
        "session_id": latest.stem,
        "path": str(latest),
        "mtime": latest.stat().st_mtime,
    }


def parse_usage_from_line(line: str) -> Optional[dict]:
    """从单行 JSONL 中提取 token usage"""
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None

    # Claude Code JSONL 结构: {message: {..., usage: {input_tokens, output_tokens, ...}}}
    msg = obj.get("message", obj)
    usage = msg.get("usage", None)
    if not usage:
        return None

    return {
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
        "total": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
    }


def parse_tool_use_from_line(line: str) -> Optional[dict]:
    """从单行 JSONL 中提取工具调用信息"""
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None

    msg = obj.get("message", obj)
    content = msg.get("content", [])

    if isinstance(content, str):
        return None
    if not isinstance(content, list):
        return None

    for block in content:
        if block.get("type") == "tool_use":
            return {
                "tool_name": block.get("name", "unknown"),
                "tool_id": block.get("id", ""),
                "tool_input": block.get("input", {}),
            }
    return None


def parse_subagent_spawn_from_line(line: str) -> Optional[dict]:
    """检测子 Agent 生成事件 (Agent 工具的 tool_use)"""
    tool = parse_tool_use_from_line(line)
    if tool and tool["tool_name"] == "Agent":
        inp = tool.get("tool_input", {})
        return {
            "subagent_type": inp.get("subagent_type", inp.get("type", "unknown")),
            "description": inp.get("description", ""),
            "prompt": inp.get("prompt", "")[:200],
        }
    return None


def tail_session_jsonl(session_path: str, callback, stop_event: threading.Event):
    """tail -f 模式跟踪 JSONL 文件，新行到达时调用 callback(line, parsed)"""
    if not os.path.exists(session_path):
        return

    with open(session_path, "r", encoding="utf-8", errors="replace") as f:
        # 跳到文件末尾
        f.seek(0, 2)

        while not stop_event.is_set():
            line = f.readline()
            if line:
                line = line.strip()
                if line:
                    usage = parse_usage_from_line(line)
                    tool = parse_tool_use_from_line(line)
                    sub = parse_subagent_spawn_from_line(line)
                    callback(line, {"usage": usage, "tool": tool, "subagent": sub})
            else:
                time.sleep(0.5)
