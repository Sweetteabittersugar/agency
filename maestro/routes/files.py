"""文件浏览路由"""

import time
import logging
from urllib.parse import parse_qs
log = logging.getLogger(__name__)


def handle_list(handler, parsed):
    """GET /api/files — 文件浏览器"""
    from maestro.project_access import ProjectAccessError, authorize_project_path

    target = parse_qs(parsed.query).get("path", [None])[0]
    try:
        p = authorize_project_path(target, require_directory=True)
        entries = []
        for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                entries.append(
                    {
                        "name": child.name,
                        "is_dir": child.is_dir(),
                        "size": child.stat().st_size if child.is_file() else 0,
                        "mtime": time.strftime(
                            "%m-%d %H:%M", time.localtime(child.stat().st_mtime)
                        ),
                    }
                )
            except Exception:
                log.debug(f"Failed to list directory {p}", exc_info=True)
        handler.send_json(
            {"path": str(p), "entries": entries, "parent": str(p.parent) if p.parent != p else ""}
        )
    except ProjectAccessError as e:
        handler.send_json({"error": str(e), "code": e.code}, 403)
    except Exception as e:
        log.error(f"文件操作失败: {e}", exc_info=True)
        handler.send_json({"error": "文件操作失败，请稍后重试"}, 500)
    return True
