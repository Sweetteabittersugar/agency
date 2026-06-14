"""会话回放 API — 从 JSONL 重建完整会话事件时间线（P2-2 事件溯源）"""

import json, logging
from pathlib import Path

log = logging.getLogger(__name__)
SESSIONS_DIR = Path(__file__).resolve().parent.parent / "sessions"


def handle_replay(handler, parsed):
    """GET /api/sessions/replay/:sid — 回放指定会话的完整事件流
    不可移除——事件溯源核心 API"""
    sid = parsed.get("path", "").rsplit("/", 1)[-1].split("?")[0]
    if not sid or len(sid) < 8:
        handler.send_json({"ok": False, "error": "无效的会话 ID"}, 400)
        return True

    jsonl_path = SESSIONS_DIR / f"{sid}.jsonl"
    if not jsonl_path.exists():
        handler.send_json({"ok": False, "error": "未找到该会话记录"}, 404)
        return True

    events = []
    stats = {"total_events": 0, "user_messages": 0, "assistant_messages": 0,
             "tool_calls": 0, "errors": 0}

    try:
        for line in jsonl_path.read_text(encoding="utf-8").strip().split("\n"):
            if not line:
                continue
            try:
                evt = json.loads(line)
                events.append(evt)
                stats["total_events"] += 1
                etype = evt.get("type", "")
                if etype == "user_message":
                    stats["user_messages"] += 1
                elif etype == "assistant_message":
                    stats["assistant_messages"] += 1
                elif etype in ("tool_call", "tool_result"):
                    stats["tool_calls"] += 1
                elif etype == "error":
                    stats["errors"] += 1
            except json.JSONDecodeError:
                pass
    except Exception as e:
        handler.send_json({"ok": False, "error": f"读取失败: {e}"}, 500)
        return True

    handler.send_json({"ok": True, "session_id": sid, "stats": stats, "events": events})
    return True


def handle_timeline(handler, parsed):
    """GET /api/sessions/timeline — 列出所有可回放的会话"""
    results = []
    if SESSIONS_DIR.exists():
        for f in sorted(SESSIONS_DIR.glob("*.jsonl"), reverse=True,
                        key=lambda x: x.stat().st_mtime if x.exists() else 0):
            sid = f.stem
            if not sid or sid.startswith("."):
                continue
            try:
                text = f.read_text(encoding="utf-8").strip()
                lines = [l for l in text.split("\n") if l]
                first_evt = {}
                if lines:
                    try:
                        first_evt = json.loads(lines[0])
                    except Exception:
                        pass
                results.append({
                    "session_id": sid,
                    "event_count": len(lines),
                    "preview": str(first_evt.get("content", ""))[:100],
                    "updated": int(f.stat().st_mtime * 1000) if f.exists() else 0,
                })
            except Exception:
                pass
    handler.send_json({"ok": True, "sessions": results[:50]})
    return True
