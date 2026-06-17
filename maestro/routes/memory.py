"""记忆文件路由"""

import logging
from pathlib import Path
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def handle_list(handler, parsed):
    """GET /api/memory — 记忆文件列表"""
    from maestro.web_memory import list_memory_files

    try:
        files = list_memory_files(PROJECT_ROOT)
    except Exception as e:
        logger.error("memory list failed: %s", e)
        handler.send_json({"ok": False, "error": "加载记忆列表失败"}, 500)
        return True
    handler.send_json({"files": files})
    return True


def handle_get(handler, parsed):
    """GET /api/memory/{path} — 读取记忆文件"""
    from maestro.web_memory import get_memory_file

    rel = parsed["path"][len("/api/memory/"):]
    try:
        data, code = get_memory_file(PROJECT_ROOT, rel)
    except Exception as e:
        logger.error("memory get failed rel=%s: %s", rel, e)
        handler.send_json({"ok": False, "error": "读取记忆失败"}, 500)
        return True
    handler.send_json(data, code)
    return True


def handle_save(handler, body):
    """POST /api/memory/{path} — 保存记忆文件"""
    from maestro.web_memory import save_memory_file

    rel = urlparse(handler.path).path[len("/api/memory/") :]
    content = body.get("content", "")
    try:
        data, code = save_memory_file(PROJECT_ROOT, rel, content)
    except Exception as e:
        logger.error("memory save failed rel=%s: %s", rel, e)
        handler.send_json({"ok": False, "error": "保存记忆失败"}, 500)
        return True
    handler.send_json(data, code)
    return True


def handle_search(handler, parsed):
    """GET /api/memory/search?q=xxx — 搜索所有记忆文件"""
    from maestro.web_memory import search_memory

    query = parse_qs(parsed.query).get("q", [""])[0].strip()
    try:
        data, code = search_memory(PROJECT_ROOT, query)
    except Exception as e:
        logger.error("memory search failed q=%s: %s", query, e)
        handler.send_json({"ok": False, "error": "搜索记忆失败"}, 500)
        return True
    handler.send_json(data, code)
    return True


def handle_timeline(handler, parsed):
    """GET /api/memory/timeline — 记忆时间线"""
    from maestro.web_memory import get_timeline

    try:
        data, code = get_timeline(PROJECT_ROOT)
    except Exception as e:
        logger.error("memory timeline failed: %s", e)
        handler.send_json({"ok": False, "error": "加载时间线失败"}, 500)
        return True
    handler.send_json(data, code)
    return True
