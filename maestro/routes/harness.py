"""Harness 路由 — 权限 / 上下文 / SubAgent / Hooks / 事件"""
import json
import time
import threading
import logging
import os
from urllib.parse import parse_qs, urlparse
from pathlib import Path
from queue import Empty

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def handle_stream(handler, parsed):
    """GET /api/harness/stream — SSE 长连接"""
    from maestro.harness.watcher import bus
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "close")
    handler.end_headers()
    q = bus.listen()
    try:
        while True:
            payload = q.get(timeout=30)
            try:
                handler.wfile.write(f"event: harness\ndata: {payload}\n\n".encode())
                handler.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                break
    except Empty:
        pass
    finally:
        bus.unlisten(q)
    return True


def handle_permissions_allowlist(handler, parsed):
    """GET /api/permissions/allowlist — 读取 allow 规则"""
    settings_path = PROJECT_ROOT / ".claude" / "settings.json"
    rules = []
    if settings_path.exists():
        try:
            s = json.loads(settings_path.read_text(encoding="utf-8"))
            rules = s.get("permissions", {}).get("allow", [])
        except Exception:
            log.warning("Failed to read permission allowlist from settings.json")
    handler.send_json({"rules": rules})
    return True


def handle_permissions_history(handler, parsed):
    """GET /api/permissions/history — 权限决策历史"""
    from maestro.web import _permission_log, _permission_log_lock, get_permission_stats
    limit = int(parse_qs(parsed.query).get("limit", ["50"])[0])
    with _permission_log_lock:
        hist = _permission_log[-limit:]
    stats = get_permission_stats()
    handler.send_json({"history": list(reversed(hist)), "stats": stats})
    return True


def handle_permissions_stats(handler, parsed):
    """GET /api/permissions/stats — 权限统计"""
    from maestro.web import get_permission_stats
    handler.send_json(get_permission_stats())
    return True


def handle_context(handler, parsed):
    """GET /api/harness/context — Token 窗口分析"""
    import re
    from maestro.harness.jsonl_parser import find_latest_session, analyze_session
    try:
        sid = parse_qs(parsed.query).get("session", [""])[0]
        if sid and not re.match(r'^[a-fA-F0-9\-]+$', sid):
            handler.send_json({"total_tokens": 0, "session_id": sid, "error": "invalid session id", "should_compact": False})
            return True
        proj = str(PROJECT_ROOT)
        if sid:
            home = Path.home()
            slug = proj.replace("\\", "/").rstrip("/").replace(":/", "--").replace("/", "-").lstrip("-")
            jsonl_path = home / ".claude" / "projects" / slug / f"{sid}.jsonl"
            if jsonl_path.exists():
                result = analyze_session(str(jsonl_path))
                result["should_compact"] = result.get("total_tokens", 0) > 300000
                handler.send_json(result)
            else:
                handler.send_json({"total_tokens": 0, "session_id": sid, "error": "session not found", "should_compact": False})
        else:
            session_info = find_latest_session(proj)
            if session_info and os.path.exists(session_info["path"]):
                result = analyze_session(session_info["path"])
                result["should_compact"] = result.get("total_tokens", 0) > 300000
                handler.send_json(result)
            else:
                handler.send_json({"total_tokens": 0, "session_id": "", "last_update": time.strftime("%H:%M:%S"), "should_compact": False})
    except Exception as e:
        handler.send_json({"total_tokens": 0, "error": str(e)[:100], "should_compact": False})
    return True


def handle_subagents(handler, parsed):
    """GET /api/harness/subagents — 子 Agent 任务树"""
    from maestro.harness.jsonl_parser import find_latest_session
    from maestro.shared import _scan_subagents
    sid = parse_qs(parsed.query).get("session", [""])[0]
    proj = str(PROJECT_ROOT)
    tree = []
    if not sid:
        info = find_latest_session(proj)
        sid = info["session_id"] if info else ""
    if sid:
        tree += _scan_subagents(proj, sid)
    user_proj = os.environ.get("AGENCY_USER_PROJ", "")
    if user_proj and os.path.isdir(user_proj):
        user_info = find_latest_session(user_proj)
        if user_info:
            tree += _scan_subagents(user_proj, user_info["session_id"])
    handler.send_json({"tree": tree, "stats": {"total": len(tree), "running": 0, "done": len(tree), "failed": 0}})
    return True


def handle_events(handler, parsed):
    """GET /api/harness/events — 事件日志"""
    from maestro.harness.watcher import bus
    evt_type = parse_qs(parsed.query).get("type", [None])[0]
    limit = int(parse_qs(parsed.query).get("limit", ["50"])[0])
    events = bus.recent_events(evt_type, limit)
    handler.send_json({"events": events})
    return True


def handle_hooks_callback(handler, body):
    """POST /api/hooks/{event} — 接收 Hook 回调"""
    from maestro.harness.hooks_receiver import handle_hook_callback
    event = urlparse(handler.path).path[len("/api/hooks/"):]
    result = handle_hook_callback(event, body)
    handler.send_json(result)
    return True


def handle_permissions_allowlist_post(handler, body):
    """POST /api/permissions/allowlist — 添加 allow 规则"""
    rule = body.get("rule", "")
    if not rule:
        handler.send_json({"error": "rule required"}, 400)
        return True
    settings_path = PROJECT_ROOT / ".claude" / "settings.json"
    settings = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            log.warning("Failed to read settings.json for allowlist update")
    perms = settings.setdefault("permissions", {})
    allow_list = perms.setdefault("allow", [])
    if rule not in allow_list:
        allow_list.append(rule)
    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    handler.send_json({"ok": True, "rule": rule})
    return True


def handle_permissions_decision(handler, body):
    """POST /api/permissions/decision — 权限决策回调"""
    from maestro.harness.watcher import bus
    from maestro.web import record_permission
    decision = body.get("decision", "deny")
    tool_name = body.get("tool_name", "")
    risk = body.get("risk", {})
    reason = body.get("reason", "")
    record_permission(tool_name, decision, risk, reason)
    bus.broadcast("permission_decision", {
        "tool_name": tool_name, "decision": decision, "reason": reason,
        "timestamp": time.strftime("%H:%M:%S"),
    })
    handler.send_json({"ok": True})
    return True


def handle_hooks_config(handler, parsed):
    """GET /api/hooks/config — 已配置的 Hook 脚本列表"""
    hooks_dir = PROJECT_ROOT / ".claude" / "hooks"
    scripts = []
    if hooks_dir.exists():
        for f in sorted(hooks_dir.glob("*.sh")):
            scripts.append({"name": f.name, "size": f.stat().st_size})
    handler.send_json({"scripts": scripts, "events": []})
    return True


def handle_session_delete(handler, body):
    """POST /api/session/delete"""
    session_id = body.get("session_id", "")
    if not session_id or len(session_id) < 8:
        handler.send_json({"error": "session_id required"}, 400)
        return True
    import shutil
    home = Path.home()
    deleted = 0
    projects_dir = home / ".claude" / "projects"
    if projects_dir.exists():
        for proj_dir in projects_dir.iterdir():
            if not proj_dir.is_dir():
                continue
            for f in proj_dir.glob(f"*{session_id[:8]}*.jsonl"):
                f.unlink()
                deleted += 1
            sd = proj_dir / "subagents" / session_id
            if sd.exists():
                shutil.rmtree(str(sd))
                deleted += 1
    handler.send_json({"ok": True, "deleted": deleted})
    return True
