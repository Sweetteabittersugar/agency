"""会话持久化 — 事件溯源模式 (JSONL + 快照压缩)"""
import json
import time
import os
from pathlib import Path

STORE_DIR = Path(__file__).resolve().parent / "sessions"
from maestro.app_config import SESSION_SNAPSHOT_THRESHOLD as SNAPSHOT_THRESHOLD  # JSONL 超过 2MB 时压缩快照


def _ensure_dir():
    STORE_DIR.mkdir(parents=True, exist_ok=True)


def _session_path(session_id: str) -> Path:
    _ensure_dir()
    safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_.")
    return STORE_DIR / f"{safe_id}.jsonl"


def _snapshot_path(session_id: str) -> Path:
    safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_.")
    return STORE_DIR / f"{safe_id}.snapshot.json"


def append_event(session_id: str, event_type: str, data: dict) -> dict:
    """追加事件到会话日志"""
    event = {
        "ts": time.time(),
        "type": event_type,
        "data": data
    }
    path = _session_path(session_id)
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        return {"ok": False, "error": str(e)}

    try:
        if path.stat().st_size > SNAPSHOT_THRESHOLD:
            _compress_snapshot(session_id)
    except Exception:
        pass

    return {"ok": True, "event": event}


def _compress_snapshot(session_id: str):
    """将 JSONL 压缩为快照：保留关键事件，丢弃中间过程"""
    path = _session_path(session_id)
    if not path.exists():
        return

    events = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
    except Exception:
        return

    keep_types = {"user_message", "agent_selected", "agent_response", "route_decision",
                  "task_complete", "error", "feedback"}

    snapshot = [e for e in events if e.get("type") in keep_types]

    snap_path = _snapshot_path(session_id)
    try:
        with open(snap_path, "w", encoding="utf-8") as f:
            json.dump({
                "compressed_at": time.time(),
                "original_count": len(events),
                "compressed_count": len(snapshot),
                "events": snapshot
            }, f, ensure_ascii=False)
    except Exception:
        return

    try:
        os.replace(snap_path, path)
    except Exception:
        pass


def get_session(session_id: str) -> dict:
    """获取会话全部事件"""
    path = _session_path(session_id)
    if not path.exists():
        return {"session_id": session_id, "events": [], "count": 0}

    events = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
    except Exception:
        return {"session_id": session_id, "events": [], "count": 0, "error": "读取失败"}

    return {"session_id": session_id, "events": events, "count": len(events)}


def list_sessions() -> list:
    """列出所有会话"""
    _ensure_dir()
    sessions = []
    for f in sorted(STORE_DIR.glob("*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True):
        name = f.stem
        try:
            size = f.stat().st_size
            with open(f, "r", encoding="utf-8") as fp:
                first_line = fp.readline()
                fp.seek(max(0, size - 2048))
                remaining = fp.read()
                last_line = remaining.strip().split("\n")[-1] if remaining.strip() else first_line

            first_ts = json.loads(first_line).get("ts", 0) if first_line else 0
            last_ts = json.loads(last_line).get("ts", 0) if last_line else 0

            msg_count = 0
            with open(f, "r", encoding="utf-8") as fp:
                for line in fp:
                    if '"user_message"' in line or '"agent_response"' in line:
                        msg_count += 1

            sessions.append({
                "id": name,
                "size_kb": round(size / 1024, 1),
                "events": msg_count,
                "created": first_ts,
                "updated": last_ts
            })
        except Exception:
            sessions.append({"id": name, "size_kb": 0, "events": 0, "created": 0, "updated": 0})
    return sessions


def delete_session(session_id: str) -> dict:
    """删除会话"""
    path = _session_path(session_id)
    if path.exists():
        try:
            path.unlink()
            return {"ok": True, "deleted": session_id}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    return {"ok": False, "error": "会话不存在"}
