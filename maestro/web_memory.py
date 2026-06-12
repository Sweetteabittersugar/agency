"""Agency 记忆文件管理"""
import json
import logging
import urllib.parse
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
    rel = urllib.parse.unquote(rel)
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
    rel = urllib.parse.unquote(rel)
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


def search_memory(project_root, query):
    """搜索所有记忆文件内容。返回 (data_dict, http_status)"""
    if not query:
        return {"ok": False, "error": "缺少搜索词 q"}, 400

    results = []
    search_dirs = [
        project_root,
        project_root / ".claude" / "rules",
    ]
    mem_dir = project_root / "memory"
    if not mem_dir.exists():
        mem_dir = Path.home() / ".claude" / "projects" / "D--agency" / "memory"
    if mem_dir.exists():
        search_dirs.append(mem_dir)

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for f in search_dir.rglob("*.md"):
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                lines = content.split("\n")
                matches = []
                for i, line in enumerate(lines):
                    if query.lower() in line.lower():
                        matches.append({"line": i + 1, "text": line.strip()[:200]})
                if matches:
                    results.append({
                        "name": f.name,
                        "path": str(f.relative_to(project_root)),
                        "matches": matches[:10],
                        "total_matches": len(matches),
                    })
            except Exception:
                pass

    results.sort(key=lambda r: r["total_matches"], reverse=True)
    return {"ok": True, "query": query, "results": results, "total_files": len(results)}, 200


def get_timeline(project_root):
    """记忆时间线。返回 (data_dict, http_status)"""
    entries = []

    # 收集 session 事件中的关键记忆
    sessions_dir = project_root / "maestro" / "sessions"
    if sessions_dir.exists():
        for f in sorted(sessions_dir.glob("*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                lines = []
                with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                    all_lines = fp.readlines()
                    for line in all_lines[-500:]:
                        if line.strip():
                            lines.append(line.strip())

                for line in lines:
                    try:
                        evt = json.loads(line)
                        if evt.get("type") in ("user_message", "agent_response", "route_decision", "task_complete", "feedback"):
                            entries.append({
                                "ts": evt.get("ts", 0),
                                "type": evt.get("type"),
                                "session": f.stem,
                                "summary": str(evt.get("data", {}))[:300],
                            })
                    except Exception:
                        pass
            except Exception:
                pass

    # 收集 routing feedback
    feedback_file = project_root / "maestro" / "routing_feedback.jsonl"
    if feedback_file.exists():
        try:
            with open(feedback_file, "r", encoding="utf-8") as fp:
                for line in fp.readlines()[-100:]:
                    if line.strip():
                        evt = json.loads(line)
                        entries.append({
                            "ts": evt.get("ts", 0),
                            "type": "routing_correction",
                            "session": "",
                            "summary": f"路由纠正: {evt.get('original_agent')} -> {evt.get('corrected_agent')} | {evt.get('task', '')[:200]}",
                        })
        except Exception:
            pass

    # 收集操作历史
    ops_file = project_root / "maestro" / "operations.jsonl"
    if ops_file.exists():
        try:
            with open(ops_file, "r", encoding="utf-8") as fp:
                for line in fp.readlines()[-100:]:
                    if line.strip():
                        evt = json.loads(line)
                        entries.append({
                            "ts": evt.get("ts", 0),
                            "type": "operation",
                            "session": "",
                            "summary": f"{evt.get('agent','')}: {evt.get('type','')} -> {evt.get('target','')} | {evt.get('detail','')[:200]}",
                        })
        except Exception:
            pass

    entries.sort(key=lambda e: e["ts"], reverse=True)

    return {
        "ok": True,
        "entries": entries[:100],
        "total": len(entries),
    }, 200
