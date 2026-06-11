"""会话管理 API — 事件溯源持久化"""
import json
from urllib.parse import urlparse, parse_qs
from maestro.session_store import (
    append_event, get_session, list_sessions, delete_session, search_sessions
)


def handle_list(handler, parsed):
    """GET /api/sessions — 列出所有会话"""
    sessions = list_sessions()
    handler.send_json({"ok": True, "sessions": sessions})
    return True


def handle_get(handler, parsed):
    """GET /api/sessions/{id} 或 /api/sessions/{id}/forks"""
    path = parsed.path
    prefix = "/api/sessions/"
    if not path.startswith(prefix) or len(path) <= len(prefix):
        handler.send_json({"ok": False, "error": "缺少 session_id"}, 400)
        return True
    rest = path[len(prefix):]
    if rest.endswith("/forks"):
        from maestro.routes.session_fork import handle_list_forks
        return handle_list_forks(handler, parsed)
    session_id = rest
    result = get_session(session_id)
    handler.send_json({"ok": True, **result})
    return True


def handle_append(handler, body):
    """POST /api/sessions/append — 追加事件"""
    session_id = body.get("session_id", "").strip()
    event_type = body.get("type", "").strip()
    data = body.get("data", {})

    if not session_id or not event_type:
        handler.send_json({"ok": False, "error": "缺少必填字段: session_id, type"}, 400)
        return True

    result = append_event(session_id, event_type, data)
    handler.send_json(result, 200 if result["ok"] else 500)
    return True


def handle_delete(handler, parsed):
    """DELETE /api/sessions/{id} — 删除会话"""
    path = parsed.path
    prefix = "/api/sessions/"
    if not path.startswith(prefix) or len(path) <= len(prefix):
        handler.send_json({"ok": False, "error": "缺少 session_id"}, 400)
        return True
    session_id = path[len(prefix):]
    result = delete_session(session_id)
    handler.send_json(result, 200 if result["ok"] else 404)
    return True


def handle_search(handler, parsed):
    """GET /api/sessions/search?q=xxx"""
    query = parse_qs(parsed.query).get("q", [""])[0].strip()
    if not query:
        handler.send_json({"ok": False, "error": "缺少搜索词 q"}, 400)
        return True

    results = search_sessions(query)
    handler.send_json({"ok": True, "query": query, "results": results, "count": len(results)})
    return True
