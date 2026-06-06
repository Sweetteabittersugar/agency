"""
JSONL 解析器 — 从 Claude Code session JSONL 中提取结构化数据
复用 transcript-parser.py 的解析逻辑，精简为 Harness 所需字段
"""
import json, os, time, threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def find_latest_session(project_root: str = None) -> Optional[dict]:
    """找到当前项目最新的 session JSONL 文件"""
    if not project_root:
        return None
    # Claude Code sessions 存储在 ~/.claude/projects/<slug>/
    import os as _os
    home = Path.home()
    # 统一路径分隔符后计算 slug
    normalized = project_root.replace("\\", "/").rstrip("/")
    slug = normalized.replace(":/", "--").replace("/", "-").lstrip("-")
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
    """从单行 JSONL 中提取 token usage 和 model"""
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None

    # Claude Code JSONL 结构: {message: {model, usage: {input_tokens, output_tokens, ...}}}
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
        "model": msg.get("model", ""),
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


def analyze_session(jsonl_path: str, model: str = "") -> dict:
    """完整解析一个 session JSONL，返回上下文统计。

    model 参数可选：如果提供且在 PRICING 中，用实际定价；否则保守估算。
    优先使用 JSONL 中检测到的实际模型。
    """
    if not os.path.exists(jsonl_path):
        return {"total_tokens": 0, "messages": 0, "session_id": ""}

    total_in = 0
    total_out = 0
    total_cache_read = 0
    total_cache_write = 0
    message_count = 0
    tool_calls = 0
    subagent_spawns = 0
    lines = 0
    first_ts = None
    last_ts = None
    model_counter: dict[str, int] = {}

    try:
        with open(jsonl_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                lines += 1
                usage = parse_usage_from_line(line)
                if usage:
                    total_in += usage.get("input_tokens", 0)
                    total_out += usage.get("output_tokens", 0)
                    total_cache_read += usage.get("cache_read_input_tokens", 0)
                    total_cache_write += usage.get("cache_creation_input_tokens", 0)
                    message_count += 1
                    m = usage.get("model", "")
                    if m:
                        model_counter[m] = model_counter.get(m, 0) + 1

                tool = parse_tool_use_from_line(line)
                if tool:
                    tool_calls += 1

                if parse_subagent_spawn_from_line(line):
                    subagent_spawns += 1

                # 提取时间戳
                try:
                    obj = json.loads(line)
                    ts = obj.get("timestamp")
                    if ts:
                        try:
                            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                            epoch = dt.timestamp()
                        except Exception:
                            epoch = 0
                        if first_ts is None:
                            first_ts = epoch
                        last_ts = epoch
                except Exception:
                    pass

    except Exception:
        pass

    # 检测实际使用的模型：优先 JSONL 中频率最高的模型，其次传入的 model 参数
    detected_model = model
    if model_counter:
        detected_model = sorted(model_counter.items(), key=lambda x: x[1], reverse=True)[0][0]
    if not detected_model and model:
        detected_model = model

    # 费用估算 — 使用 models.py 的定价表
    from maestro.models import estimate_cost, PRICING
    cache_saved = 0.0
    if detected_model and detected_model in PRICING:
        in_price, out_price = PRICING[detected_model]
        cost_in = (total_in / 1_000_000) * in_price
        cost_out = (total_out / 1_000_000) * out_price
        cache_saved = (total_cache_read / 1_000_000) * in_price  # 缓存命中共节省的输入费用
    else:
        # 保守估算：未知模型按 $1.00/$3.00 每百万 token
        cost_in = (total_in / 1_000_000) * 1.0
        cost_out = (total_out / 1_000_000) * 3.0
        cache_saved = (total_cache_read / 1_000_000) * 1.0
    cost_total = cost_in + cost_out

    # 估算上下文组成
    est_system = min(total_in * 0.3, 50000) if total_in > 0 else 0
    est_conversation = total_in - est_system - total_cache_read if total_in > 0 else 0
    est_tool = min(tool_calls * 500, total_in * 0.05) if tool_calls > 0 else 0

    # 计算缓存命中率
    cache_hit_rate = (total_cache_read / (total_in + 1)) * 100 if total_in > 0 else 0

    # 会话时长
    duration_s = (last_ts - first_ts) / 1000 if first_ts and last_ts else 0

    return {
        "session_id": Path(jsonl_path).stem,
        "model": detected_model,
        "total_tokens": total_in + total_out,
        "input_tokens": total_in,
        "output_tokens": total_out,
        "cache_read_tokens": total_cache_read,
        "cache_write_tokens": total_cache_write,
        "cache_hit_rate": round(cache_hit_rate, 1),
        "messages": message_count,
        "tool_calls": tool_calls,
        "subagent_spawns": subagent_spawns,
        "lines": lines,
        "composition": {
            "system_pct": round(est_system / (total_in + 1) * 100, 1) if total_in > 0 else 0,
            "conversation_pct": round(max(0, est_conversation) / (total_in + 1) * 100, 1) if total_in > 0 else 0,
            "tool_pct": round(est_tool / (total_in + 1) * 100, 1) if total_in > 0 else 0,
        },
        "cost_est": {
            "input": round(cost_in, 6),
            "output": round(cost_out, 6),
            "cache_saved": round(cache_saved, 6),
            "total": round(cost_total, 6),
        },
        "duration_s": round(duration_s, 1),
        "last_update": time.strftime("%H:%M:%S"),
    }
