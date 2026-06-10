"""Git Worktree 管理器 — Agent 工作目录隔离"""
import subprocess
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKTREE_BASE = PROJECT_ROOT / "maestro" / "worktrees"


def _run_git(args, cwd=None):
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, timeout=30,
            cwd=cwd or PROJECT_ROOT
        )
        return {"ok": result.returncode == 0, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
    except Exception as e:
        return {"ok": False, "stderr": str(e)}


def list_worktrees():
    result = _run_git(["worktree", "list", "--porcelain"])
    if not result["ok"]:
        return []

    trees = []
    current = {}
    for line in result["stdout"].split("\n"):
        if line.startswith("worktree "):
            if current:
                trees.append(current)
            current = {"path": line.split("worktree ", 1)[1]}
        elif line.startswith("HEAD "):
            current["head"] = line.split("HEAD ", 1)[1]
        elif line.startswith("branch "):
            current["branch"] = line.split("branch ", 1)[1].replace("refs/heads/", "")
    if current:
        trees.append(current)
    return trees


def create_worktree(name, base_branch="main"):
    path = WORKTREE_BASE / name
    if path.exists():
        return {"ok": False, "error": f"Worktree '{name}' 已存在"}

    WORKTREE_BASE.mkdir(parents=True, exist_ok=True)
    branch_name = f"wt/{name}"

    result = _run_git(["worktree", "add", "-b", branch_name, str(path), base_branch])
    if not result["ok"]:
        result = _run_git(["worktree", "add", str(path), base_branch])

    if result["ok"]:
        return {"ok": True, "name": name, "path": str(path), "branch": branch_name}
    return {"ok": False, "error": result["stderr"]}


def remove_worktree(name, force=False):
    path = WORKTREE_BASE / name
    if not path.exists():
        return {"ok": False, "error": f"Worktree '{name}' 不存在"}

    args = ["worktree", "remove"]
    if force:
        args.append("--force")
    args.append(str(path))

    result = _run_git(args)

    if path.exists():
        try:
            shutil.rmtree(path, ignore_errors=True)
        except Exception:
            pass

    if result["ok"]:
        return {"ok": True, "name": name, "removed": True}
    return {"ok": False, "error": result["stderr"]}


def cleanup_stale_worktrees():
    trees = list_worktrees()
    cleaned = []
    for t in trees:
        p = Path(t["path"])
        if p.resolve() == PROJECT_ROOT.resolve():
            continue
        if WORKTREE_BASE.resolve() not in p.resolve().parents and str(p.resolve()) != str(PROJECT_ROOT.resolve()):
            continue
        if not p.exists():
            _run_git(["worktree", "prune"])
            cleaned.append({"path": t["path"], "action": "pruned"})

    return {"ok": True, "cleaned": cleaned}


def get_worktree_status():
    trees = list_worktrees()
    main_tree = None
    agent_trees = []

    for t in trees:
        p = Path(t["path"])
        if p.resolve() == PROJECT_ROOT.resolve():
            main_tree = {"path": str(p), "branch": t.get("branch", ""), "head": t.get("head", "")}
        elif WORKTREE_BASE.resolve() in p.resolve().parents:
            exists = p.exists()
            agent_trees.append({
                "name": p.name,
                "path": str(p),
                "branch": t.get("branch", ""),
                "head": t.get("head", ""),
                "exists": exists,
                "size_mb": _dir_size(p) if exists else 0
            })

    return {
        "main": main_tree,
        "agents": agent_trees,
        "count": len(agent_trees),
        "base_path": str(WORKTREE_BASE)
    }


def _dir_size(path):
    total = 0
    try:
        for f in path.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
    except Exception:
        pass
    return round(total / (1024 * 1024), 2)


# ── HTTP 处理函数 ──

def worktree_handle_list(handler, parsed):
    """GET /api/worktrees"""
    status = get_worktree_status()
    handler.send_json({"ok": True, **status})


def worktree_handle_create(handler, body):
    """POST /api/worktrees/create"""
    name = (body.get("name") or "").strip()
    base = (body.get("base") or "main").strip()

    if not name:
        handler.send_json({"ok": False, "error": "缺少 name"}, 400)
        return

    if not name.replace("-", "").replace("_", "").isalnum():
        handler.send_json({"ok": False, "error": "名称只能含字母、数字、连字符、下划线"}, 400)
        return

    result = create_worktree(name, base)
    handler.send_json(result, 200 if result["ok"] else 400)


def worktree_handle_remove(handler, body):
    """POST /api/worktrees/remove"""
    name = (body.get("name") or "").strip()
    force = body.get("force", False)

    if not name:
        handler.send_json({"ok": False, "error": "缺少 name"}, 400)
        return

    result = remove_worktree(name, force)
    handler.send_json(result, 200 if result["ok"] else 400)


def worktree_handle_cleanup(handler, body):
    """POST /api/worktrees/cleanup"""
    result = cleanup_stale_worktrees()
    handler.send_json(result)
