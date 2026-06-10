"""记忆文件路由"""
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def handle_list(handler, parsed):
    """GET /api/memory — 记忆文件列表"""
    from maestro.web_memory import list_memory_files
    handler.send_json({"files": list_memory_files(PROJECT_ROOT)})
    return True


def handle_get(handler, parsed):
    """GET /api/memory/{path} — 读取记忆文件"""
    from maestro.web_memory import get_memory_file
    rel = parsed.path[len("/api/memory/"):]
    data, code = get_memory_file(PROJECT_ROOT, rel)
    handler.send_json(data, code)
    return True


def handle_save(handler, body):
    """POST /api/memory/{path} — 保存记忆文件"""
    from maestro.web_memory import save_memory_file
    rel = urlparse(handler.path).path[len("/api/memory/"):]
    content = body.get("content", "")
    data, code = save_memory_file(PROJECT_ROOT, rel, content)
    handler.send_json(data, code)
    return True


def handle_search(handler, parsed):
    """GET /api/memory/search?q=xxx — 搜索所有记忆文件"""
    from maestro.web_memory import search_memory
    query = parse_qs(parsed.query).get("q", [""])[0].strip()
    data, code = search_memory(PROJECT_ROOT, query)
    handler.send_json(data, code)
    return True


def handle_timeline(handler, parsed):
    """GET /api/memory/timeline — 记忆时间线"""
    from maestro.web_memory import get_timeline
    data, code = get_timeline(PROJECT_ROOT)
    handler.send_json(data, code)
    return True
