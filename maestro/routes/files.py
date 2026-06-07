"""文件浏览路由"""
import time
import logging
from urllib.parse import parse_qs
from pathlib import Path

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def handle_list(handler, parsed):
    """GET /api/files — 文件浏览器"""
    target = parse_qs(parsed.query).get("path", [str(PROJECT_ROOT)])[0]
    try:
        p = Path(target).resolve()
        if not p.exists():
            p = PROJECT_ROOT.resolve()
        else:
            try:
                p.relative_to(PROJECT_ROOT.resolve())
            except ValueError:
                handler.send_json({"error": "forbidden"}, 403)
                return True
        entries = []
        for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                entries.append({
                    "name": child.name,
                    "is_dir": child.is_dir(),
                    "size": child.stat().st_size if child.is_file() else 0,
                    "mtime": time.strftime("%m-%d %H:%M", time.localtime(child.stat().st_mtime)),
                })
            except Exception:
                log.debug(f"Failed to list directory {p}", exc_info=True)
        handler.send_json({"path": str(p), "entries": entries, "parent": str(p.parent) if p.parent != p else ""})
    except Exception as e:
        handler.send_json({"error": str(e)}, 500)
    return True
