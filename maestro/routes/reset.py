"""恢复默认 — 逐个/分类/全量重置用户自定义内容"""
import shutil
import subprocess
import json as _json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

USER_AGENTS_DIR = PROJECT_ROOT / ".claude" / "agents" / "user"
USER_SKILLS_DIR = PROJECT_ROOT / ".claude" / "skills" / "user"
SYSTEM_AGENTS_DIR = PROJECT_ROOT / ".claude" / "agents"
SYSTEM_SKILLS_DIR = PROJECT_ROOT / ".claude" / "skills"


def _list_user_files(directory: Path, suffix: str = ".md") -> list:
    if not directory.exists():
        return []
    return sorted([
        {
            "name": f.stem,
            "path": str(f.relative_to(PROJECT_ROOT)),
            "size_kb": round(f.stat().st_size / 1024, 1)
        }
        for f in directory.glob(f"*{suffix}")
        if f.is_file() and f.name != ".gitkeep"
    ])


def _list_system_categories(base_dir: Path) -> list:
    if not base_dir.exists():
        return []
    return sorted([
        d.name for d in base_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".") and d.name != "user"
    ])


def handle_reset_status(handler, parsed):
    """GET /api/reset/status"""
    user_agents = _list_user_files(USER_AGENTS_DIR)
    user_skills = _list_user_files(USER_SKILLS_DIR)
    agent_categories = _list_system_categories(SYSTEM_AGENTS_DIR)
    skill_categories = _list_system_categories(SYSTEM_SKILLS_DIR)

    can_reset_system = (PROJECT_ROOT / ".git").exists()

    handler.send_json({
        "ok": True,
        "user_customizations": {
            "agents": user_agents,
            "skills": user_skills,
            "total": len(user_agents) + len(user_skills)
        },
        "system_categories": {
            "agents": agent_categories,
            "skills": skill_categories
        },
        "can_reset_system": can_reset_system
    })
    return True


def handle_reset_user_file(handler, parsed):
    """POST /api/reset/user-file"""
    file_path = parsed.get("path", "").strip()
    if not file_path:
        handler.send_json({"ok": False, "error": "缺少 path"}, 400)
        return True

    full_path = (PROJECT_ROOT / file_path).resolve()

    # 安全检查：只允许在 user/ 目录下
    user_agents_resolved = USER_AGENTS_DIR.resolve()
    user_skills_resolved = USER_SKILLS_DIR.resolve()
    if not (str(full_path).startswith(str(user_agents_resolved)) or
            str(full_path).startswith(str(user_skills_resolved))):
        handler.send_json({"ok": False, "error": "只能删除 user/ 目录下的文件"}, 403)
        return True

    if not full_path.exists():
        handler.send_json({"ok": False, "error": "文件不存在"}, 404)
        return True

    try:
        full_path.unlink()
        handler.send_json({"ok": True, "deleted": file_path})
    except Exception as e:
        handler.send_json({"ok": False, "error": str(e)}, 500)
    return True


def handle_reset_user_all(handler, parsed):
    """POST /api/reset/user-all"""
    deleted = []

    for d in [USER_AGENTS_DIR, USER_SKILLS_DIR]:
        if d.exists():
            for f in d.glob("*.md"):
                if f.name != ".gitkeep":
                    try:
                        f.unlink()
                        deleted.append(str(f.relative_to(PROJECT_ROOT)))
                    except Exception:
                        pass

    handler.send_json({"ok": True, "deleted": deleted, "count": len(deleted)})
    return True


def handle_reset_system_category(handler, parsed):
    """POST /api/reset/system-category"""
    category = parsed.get("category", "").strip()
    cat_type = parsed.get("type", "agents").strip()

    if not category:
        handler.send_json({"ok": False, "error": "缺少 category"}, 400)
        return True

    if not category.replace("-", "").replace("_", "").isalnum():
        handler.send_json({"ok": False, "error": "无效的 category 名称"}, 400)
        return True

    if cat_type not in ("agents", "skills"):
        handler.send_json({"ok": False, "error": "type 必须是 agents 或 skills"}, 400)
        return True

    base = SYSTEM_AGENTS_DIR if cat_type == "agents" else SYSTEM_SKILLS_DIR
    target_dir = base / category

    if not target_dir.exists():
        handler.send_json({"ok": False, "error": f"分类 {category} 不存在"}, 404)
        return True

    try:
        rel_path = str(target_dir.relative_to(PROJECT_ROOT))
        result = subprocess.run(
            ["git", "checkout", "--", rel_path],
            capture_output=True, text=True, timeout=30,
            cwd=PROJECT_ROOT
        )
        if result.returncode == 0:
            handler.send_json({"ok": True, "restored": rel_path, "message": f"已恢复 {category}"})
        else:
            handler.send_json({"ok": False, "error": result.stderr.strip()}, 500)
    except FileNotFoundError:
        handler.send_json({"ok": False, "error": "git 不可用"}, 500)
    except Exception as e:
        handler.send_json({"ok": False, "error": str(e)}, 500)
    return True


def handle_reset_full(handler, parsed):
    """POST /api/reset/full"""
    results = []

    for d in [USER_AGENTS_DIR, USER_SKILLS_DIR]:
        if d.exists():
            for f in d.glob("*.md"):
                if f.name != ".gitkeep":
                    try:
                        f.unlink()
                    except Exception:
                        pass
    results.append("user/ 已清空")

    try:
        for pattern in [".claude/agents/L*/", ".claude/skills/"]:
            subprocess.run(
                ["git", "checkout", "--", pattern],
                capture_output=True, timeout=30,
                cwd=PROJECT_ROOT
            )
        results.append("系统文件已恢复到默认")
    except FileNotFoundError:
        results.append("git 不可用，系统文件未恢复")
    except Exception as e:
        results.append(f"系统文件恢复失败: {e}")

    handler.send_json({"ok": True, "message": " | ".join(results)})
    return True
