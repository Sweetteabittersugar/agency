"""会话 Fork — 从指定位置分叉出新会话"""
import json
import time
import uuid
from pathlib import Path

SESSION_DIR = Path(__file__).resolve().parent.parent / "sessions"


def handle_fork(handler, body):
    """POST /api/sessions/fork — 从指定消息位置分叉出新会话

    fork_point 是前端消息数组的索引（0-based），后端映射到 JSONL 行号。
    """
    session_id = body.get("session_id", "").strip()
    fork_point = body.get("fork_point", 0)  # 前端消息索引
    fork_label = body.get("label", "").strip()

    if not session_id:
        handler.send_json({"ok": False, "error": "缺少 session_id"}, 400)
        return True

    src_file = SESSION_DIR / f"{session_id}.jsonl"
    if not src_file.exists():
        handler.send_json({"ok": False, "error": "会话不存在"}, 404)
        return True

    try:
        with open(src_file, "r", encoding="utf-8") as f:
            events = [json.loads(l.strip()) for l in f.readlines() if l.strip()]
    except Exception as e:
        handler.send_json({"ok": False, "error": str(e)}, 500)
        return True

    # 将前端消息索引映射到 JSONL 行号
    msg_idx = 0
    fork_line = min(fork_point, len(events) - 1)
    for i, evt in enumerate(events):
        if evt.get("type") in ("user_message", "agent_response"):
            if msg_idx == fork_point:
                fork_line = i
                break
            msg_idx += 1

    base_events = []
    for i, evt in enumerate(events):
        evt_line = json.dumps(evt, ensure_ascii=False)
        base_events.append(evt_line)
        if i == fork_line:
            break

    new_id = f"fork_{session_id}_{uuid.uuid4().hex[:8]}"
    new_file = SESSION_DIR / f"{new_id}.jsonl"

    try:
        with open(new_file, "w", encoding="utf-8") as f:
            for line in base_events:
                f.write(line + "\n")
            fork_event = json.dumps({
                "ts": time.time(),
                "type": "fork",
                "data": {
                    "forked_from": session_id,
                    "fork_point": fork_point,
                    "label": fork_label or f"分叉 {new_id[:8]}",
                    "base_event_count": len(base_events)
                }
            }, ensure_ascii=False)
            f.write(fork_event + "\n")
    except Exception as e:
        handler.send_json({"ok": False, "error": str(e)}, 500)
        return True

    handler.send_json({
        "ok": True,
        "forked": True,
        "new_session_id": new_id,
        "base_events": len(base_events),
        "fork_label": fork_label or f"分叉 {new_id[:8]}"
    })
    return True


def handle_list_forks(handler, parsed):
    """GET /api/sessions/<sid>/forks — 列出某会话的所有分叉"""
    path = parsed.path
    prefix_end = path.rfind("/forks")
    if prefix_end < 0:
        handler.send_json({"ok": False, "error": "无效路径"}, 400)
        return True

    # 提取 sid：/api/sessions/<sid>/forks -> <sid>
    prefix = "/api/sessions/"
    if not path.startswith(prefix):
        handler.send_json({"ok": False, "error": "无效路径"}, 400)
        return True
    sid = path[len(prefix):prefix_end]

    forks = []
    if SESSION_DIR.exists():
        for f in sorted(SESSION_DIR.glob(f"fork_{sid}_*.jsonl"),
                       key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    for line in fp:
                        if '"type":"fork"' in line or '"type": "fork"' in line:
                            evt = json.loads(line.strip())
                            forks.append({
                                "session_id": f.stem,
                                "fork_data": evt.get("data", {}),
                                "created": f.stat().st_mtime
                            })
                            break
            except Exception:
                pass

    handler.send_json({"ok": True, "forks": forks, "count": len(forks)})
    return True
