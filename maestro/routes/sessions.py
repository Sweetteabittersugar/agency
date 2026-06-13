"""会话管理 API — 事件溯源持久化"""

from urllib.parse import parse_qs
from maestro.session_store import (
    append_event,
    get_session,
    list_sessions,
    delete_session,
    search_sessions,
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
    rest = path[len(prefix) :]
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
    session_id = path[len(prefix) :]
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


def handle_kill(handler, body):
    """POST /api/sessions/kill — 终止 Claude 进程（关闭面板时调用，先提炼记忆）"""
    sid = body.get("session_id", "").strip()
    if not sid:
        handler.send_json({"ok": False, "error": "缺少 session_id"}, 400)
        return True

    from maestro.claude_session import _sessions as session_registry
    from maestro.memory_engine import save_memory_file
    from maestro.shared import PROJECT_ROOT
    import logging

    log = logging.getLogger(__name__)

    memories_saved = 0
    cs = session_registry.get(sid)
    if cs and cs.is_alive() and len(cs._transcript) >= 2:
        try:
            memories = cs.extract_memories()
            project_root = body.get("proj_root", "") or str(
                getattr(cs, "project_root", str(PROJECT_ROOT))
            )
            for mem in memories:
                saved = save_memory_file(project_root, mem)
                if saved:
                    memories_saved += 1
        except Exception as e:
            log.warning(f"记忆提炼失败: {e}")

    from maestro.claude_session import terminate

    killed = terminate(sid)
    result = {"ok": killed, "killed": killed}
    if memories_saved > 0:
        result["memories_saved"] = memories_saved
    handler.send_json(result)
    return True


def handle_list_processes(handler, parsed):
    """GET /api/sessions/processes — 列出所有活跃的 Claude 进程"""
    from maestro.claude_session import list_sessions

    procs = list_sessions()
    handler.send_json({"ok": True, "processes": procs, "count": len(procs)})
    return True
