#!/usr/bin/env python3
"""Code formatter — format Python (ruff), JS/TS/CSS/HTML/JSON/MD (prettier)."""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Fix Windows terminal encoding
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Config ──────────────────────────────────────────────
PY_EXTS = {".py"}
WEB_EXTS = {".js", ".ts", ".jsx", ".tsx", ".css", ".scss", ".html", ".json", ".md", ".yaml", ".yml"}
# Non-Python files misnamed as .py (excluded from ruff)
SKIP_PY_FILES = {"webui/app_test.py"}

SKIP_DIRS = {
    ".git",
    ".claude",
    ".claude-isolated",
    ".codex",
    ".cursor",
    ".gemini",
    ".github",
    ".pytest_cache",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".mypy_cache",
    ".ruff_cache",
}

# ── Helpers ─────────────────────────────────────────────


def find_tool(name: str) -> str | None:
    """Find executable in PATH."""
    return shutil.which(name)


def collect_files(root: str, extensions: set[str]) -> list[str]:
    """Walk directory tree and collect files with matching extensions."""
    files: list[str] = []
    base = Path(root).resolve()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if Path(fname).suffix.lower() in extensions:
                full = os.path.join(dirpath, fname)
                # Skip misnamed non-Python files
                try:
                    rel = Path(full).resolve().relative_to(base).as_posix()
                except ValueError:
                    rel = full
                if rel in SKIP_PY_FILES:
                    continue
                files.append(full)
    return sorted(files)


def run_tool(cmd: list[str], label: str) -> bool:
    """Run a formatting tool and report result."""
    print(f"  [{label}] {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode == 0:
        return True
    stderr = result.stderr.strip() if result.stderr else ""
    stdout = result.stdout.strip() if result.stdout else ""
    if stderr:
        print(f"    ⚠ {stderr[:300]}")
    elif stdout:
        # ruff outputs info to stdout on success
        for line in stdout.splitlines()[:5]:
            print(f"    {line}")
        if len(stdout.splitlines()) > 5:
            print(f"    ... ({len(stdout.splitlines()) - 5} more lines)")
    return False


def find_ruff() -> list[str] | None:
    """Return ruff command as list, preferring CLI then module fallback."""
    if shutil.which("ruff"):
        return ["ruff"]
    # Fallback to python -m ruff
    try:
        subprocess.run(
            [sys.executable, "-m", "ruff", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        return [sys.executable, "-m", "ruff"]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


# ── Python formatter (ruff) ─────────────────────────────


def format_python(paths: list[str], check_only: bool = False) -> dict:
    """Format Python files with ruff.

    Uses project's pyproject.toml config (line-length=100, py310).
    """
    if not paths:
        return {"ok": True, "files": 0, "changed": 0}
    ruff_cmd = find_ruff()
    if not ruff_cmd:
        print("  ✗ ruff not found. Install: pip install ruff")
        return {"ok": False, "files": len(paths), "changed": 0}

    # ruff format (black-compatible)
    fmt_cmd = ruff_cmd + ["format"]
    if check_only:
        fmt_cmd.append("--check")
    fmt_cmd.extend(paths)
    print(f"\n📏 ruff format ({len(paths)} files)...")
    fmt_ok = run_tool(fmt_cmd, "format")

    # ruff check --fix (auto-fix lint issues, non-zero exit on unfixable issues is OK)
    lint_cmd = ruff_cmd + ["check", "--fix", "--select=E,F"]
    lint_cmd.extend(paths)
    print(f"\n🔍 ruff check ({len(paths)} files)...")
    run_tool(lint_cmd, "lint")  # allowed to fail — unfixable issues are informational

    return {"ok": fmt_ok, "files": len(paths), "changed": len(paths)}


# ── Web formatter (prettier) ────────────────────────────


def format_web(paths: list[str], check_only: bool = False) -> dict:
    """Format web files with prettier."""
    if not paths:
        return {"ok": True, "files": 0, "changed": 0}

    # Try local node_modules/.bin/prettier first, then global
    prettier = find_tool("prettier")
    if not prettier:
        local = Path(
            "node_modules/.bin/prettier.cmd"
            if sys.platform == "win32"
            else "node_modules/.bin/prettier"
        )
        prettier = str(local) if local.exists() else None

    if not prettier:
        print("  ⚠ prettier not found, skipping web files. Install: npm i -g prettier")
        return {"ok": True, "files": 0, "changed": 0}

    cmd = [prettier, "--write" if not check_only else "--check"]
    cmd.extend(paths)
    print(f"\n🎨 prettier ({len(paths)} files)...")
    ok = run_tool(cmd, "prettier")
    return {"ok": ok, "files": len(paths), "changed": len(paths)}


# ── Main ────────────────────────────────────────────────


def main():
    check_only = "--check" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--check"]

    targets = args if args else ["."]
    print(f"{'🔎 Checking' if check_only else '📝 Formatting'} targets: {targets}")

    # Collect files
    py_files: list[str] = []
    web_files: list[str] = []
    for target in targets:
        root = target if os.path.isdir(target) else "."
        if os.path.isdir(target):
            py_files.extend(collect_files(target, PY_EXTS))
            web_files.extend(collect_files(target, WEB_EXTS))
        elif os.path.isfile(target):
            ext = Path(target).suffix.lower()
            if ext in PY_EXTS:
                py_files.append(target)
            elif ext in WEB_EXTS:
                web_files.append(target)

    py_files = sorted(set(py_files))
    web_files = sorted(set(web_files))

    # Format
    py_result = format_python(py_files, check_only)
    web_result = format_web(web_files, check_only)

    # Summary
    total = py_result["files"] + web_result["files"]
    print(f"\n{'=' * 50}")
    print(f"  Total: {total} files processed")
    print(f"  Python: {py_result['files']} (ruff)")
    print(f"  Web:    {web_result['files']} (prettier)")
    if check_only:
        ok = py_result["ok"] and web_result["ok"]
        if ok:
            print("  ✅ All files are properly formatted.")
        else:
            print("  ❌ Some files need formatting. Run without --check to fix.")
    else:
        print("  ✅ Formatting complete.")
    print(f"{'=' * 50}\n")

    return 0 if (py_result["ok"] and web_result["ok"]) else 1


if __name__ == "__main__":
    sys.exit(main())
