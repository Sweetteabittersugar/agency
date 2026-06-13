"""对话持久化 — 服务端存储，替代前端 localStorage"""

import json
import time
from pathlib import Path

CONVOS_FILE = Path(__file__).resolve().parent.parent / "conversations.json"
MAX_CONVOS = 50


def _load():
    if CONVOS_FILE.exists():
        try:
            return json.loads(CONVOS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save(convos):
    CONVOS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONVOS_FILE.write_text(json.dumps(convos, ensure_ascii=False, indent=2), encoding="utf-8")


def handle_list(handler, parsed):
    """GET /api/conversations — 只返回未归档的对话（archived=true 的被过滤）"""
    convos = _load()
    convos = [c for c in convos if not c.get("archived")]  # 归档的不显示在主列表
    summaries = []
    for c in convos:
        preview = ""
        if c.get("messages"):
            first = c["messages"][0]
            preview = (first.get("content", "") if isinstance(first, dict) else str(first))[:60]
        summaries.append(
            {
                "id": c.get("id"),
                "title": c.get("title", "新对话"),
                "sessionId": c.get("sessionId", ""),
                "updated": c.get("updated", 0),
                "preview": preview,
                "msgCount": len(c.get("messages", [])),
            }
        )
    handler.send_json({"ok": True, "conversations": summaries})
    return True


def handle_get(handler, parsed):
    """GET /api/conversations/<id>"""
    path = parsed.path
    prefix = "/api/conversations/"
    if not path.startswith(prefix) or len(path) <= len(prefix):
        handler.send_json({"ok": False, "error": "缺少 id"}, 400)
        return True
    convo_id = path[len(prefix) :]
    convos = _load()
    for c in convos:
        if str(c.get("id")) == convo_id:
            handler.send_json({"ok": True, "conversation": c})
            return True
    handler.send_json({"ok": False, "error": "未找到"}, 404)
    return True


def handle_save(handler, body):
    """POST /api/conversations/save"""
    convo = {
        "id": body.get("id"),
        "title": body.get("title", ""),
        "messages": body.get("messages", []),
        "sessionId": body.get("sessionId", ""),
        "updated": int(time.time() * 1000),
    }
    if not convo["id"]:
        handler.send_json({"ok": False, "error": "缺少 id"}, 400)
        return True
    trimmed = []
    for m in convo["messages"]:
        if isinstance(m, dict):
            trimmed.append({**m, "content": str(m.get("content", ""))[:5000]})
        else:
            trimmed.append({"role": "user", "content": str(m)[:5000]})
    convo["messages"] = trimmed
    convos = _load()
    found = False
    for i, c in enumerate(convos):
        if c.get("id") == convo["id"]:
            convos[i] = convo
            found = True
            break
    if not found:
        convos.insert(0, convo)
    if len(convos) > MAX_CONVOS:
        convos = convos[:MAX_CONVOS]
    _save(convos)
    handler.send_json({"ok": True})
    return True


def handle_delete(handler, parsed):
    """DELETE /api/conversations/<id> — 软删除：标记 archived=true 而非真删除

    设计：对话不丢，只是从侧边栏隐藏。需要时可通过 /api/conversations/archived 查询。
    避免用户误删后无法恢复。"""
    path = parsed.path
    prefix = "/api/conversations/"
    if not path.startswith(prefix) or len(path) <= len(prefix):
        handler.send_json({"ok": False, "error": "缺少 id"}, 400)
        return True
    convo_id = path[len(prefix):]
    convos = _load()
    found = False
    for c in convos:
        if str(c.get("id")) == convo_id:
            c["archived"] = True
            c["archived_at"] = int(time.time() * 1000)
            found = True
            break
    if found:
        _save(convos)
        handler.send_json({"ok": True, "archived": True})
    else:
        handler.send_json({"ok": False, "error": "未找到该对话"}, 404)
    return True


def handle_archived_list(handler, parsed):
    """GET /api/conversations/archived — 列出已归档的对话"""
    convos = _load()
    archived = [c for c in convos if c.get("archived")]
    handler.send_json({"ok": True, "conversations": archived, "count": len(archived)})
    return True
