"""会话持久化 — 事件溯源模式 (JSONL + 快照压缩)"""
import json
import time
import os
import logging
from pathlib import Path

log = logging.getLogger(__name__)

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
        log.debug(f"session_store append_event: {e}")
        return {"ok": False, "error": str(e)}

    try:
        if path.stat().st_size > SNAPSHOT_THRESHOLD:
            _compress_snapshot(session_id)
    except Exception as e:
        log.debug(f"session_store snap threshold check: {e}")

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
    except Exception as e:
        log.debug(f"session_store compress read: {e}")
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
    except Exception as e:
        log.debug(f"session_store compress write: {e}")
        return

    try:
        os.replace(snap_path, path)
    except Exception as e:
        log.debug(f"session_store replace snapshot: {e}")


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
    except Exception as e:
        log.debug(f"session_store get_session: {e}")
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
        except Exception as e:
            log.debug(f"session_store list_sessions: {e}")
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
            log.debug(f"session_store delete_session: {e}")
            return {"ok": False, "error": str(e)}
    return {"ok": False, "error": "会话不存在"}


def search_sessions(query: str, limit: int = 20) -> list:
    """全文搜索所有会话"""
    results = []
    if not STORE_DIR.exists():
        return results

    q = query.lower()
    for f in STORE_DIR.glob("*.jsonl"):
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                for line in fp:
                    if q in line.lower():
                        evt = json.loads(line)
                        results.append({
                            "session_id": f.stem,
                            "ts": evt.get("ts", 0),
                            "type": evt.get("type", "?"),
                            "snippet": str(evt.get("data", ""))[:200],
                            "full_event": evt,
                        })
                        if len(results) >= limit * 5:
                            break
        except Exception as e:
            log.debug(f"session_store search_sessions: {e}")

    seen = set()
    unique = []
    for r in sorted(results, key=lambda x: x["ts"], reverse=True):
        key = r["session_id"] + str(r["ts"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
        if len(unique) >= limit:
            break

    return unique
