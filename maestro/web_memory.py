"""Agency 记忆文件管理"""
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def list_memory_files(project_root):
    """列出项目的记忆体系文件"""
    files = []
    candidates = [
        project_root / "CLAUDE.md",
        project_root / "AGENTS.md",
        project_root / "MEMORY.md",
        project_root / ".claude" / "project.md",
        project_root / ".claude" / "global.md",
        project_root / ".claude" / "context.md",
    ]
    rules_dir = project_root / ".claude" / "rules"
    if rules_dir.exists():
        candidates.extend(sorted(rules_dir.glob("*.md")))
    mem_dir = project_root / "memory"
    if not mem_dir.exists():
        mem_dir = Path.home() / ".claude" / "projects" / "D--agency" / "memory"
    if mem_dir.exists():
        candidates.extend(sorted(mem_dir.glob("*.md")))

    for f in candidates:
        if f.exists() and f.is_file():
            try:
                content = f.read_text(encoding="utf-8")
                files.append({
                    "path": str(f.resolve()),
                    "name": f.name,
                    "size": len(content),
                    "preview": content[:200],
                    "type": f.suffix.lstrip("."),
                })
            except Exception:
                pass
    return files


def get_memory_file(project_root, rel):
    """读取单个记忆文件。返回 (data_dict, http_status)"""
    fpath = (project_root / rel).resolve()
    allowed_dirs = [project_root.resolve(), (Path.home() / ".claude").resolve()]
    in_allowed = False
    for d in allowed_dirs:
        try:
            fpath.relative_to(d)
            in_allowed = True
            break
        except ValueError:
            continue
    if not in_allowed:
        return {"error": "无权访问该文件。只能操作项目目录和 .claude 目录下的文件"}, 403
    if fpath.exists() and fpath.is_file():
        try:
            content = fpath.read_text(encoding="utf-8")
            return {"path": str(fpath), "name": fpath.name, "content": content, "size": len(content)}, 200
        except Exception as e:
            return {"error": str(e)}, 500
    return {"error": "未找到该记忆文件。请检查文件名是否正确"}, 404


def save_memory_file(project_root, rel, content):
    """编辑记忆文件。返回 (data_dict, http_status)"""
    fpath = (project_root / rel).resolve()
    allowed_mem_dirs = [project_root.resolve(), (Path.home() / ".claude").resolve()]
    in_allowed = False
    for d in allowed_mem_dirs:
        try:
            fpath.relative_to(d)
            in_allowed = True
            break
        except ValueError:
            continue
    if not in_allowed:
        return {"error": "无权访问该文件。只能操作项目目录和 .claude 目录下的文件"}, 403
    if not fpath.exists():
        return {"error": "未找到该记忆文件。请检查文件名是否正确"}, 404
    if not content:
        return {"error": "缺少必填字段 content。请提供要保存的文件内容"}, 400
    try:
        fpath.write_text(content, encoding="utf-8")
        return {"ok": True, "path": str(fpath), "size": len(content)}, 200
    except Exception as e:
        return {"error": str(e)}, 500
