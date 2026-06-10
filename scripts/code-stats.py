#!/usr/bin/env python3
"""简单代码统计器 — 统计项目中各语言代码行数"""
import os
import sys
from collections import defaultdict
from pathlib import Path

# Windows 终端 UTF-8 编码修复
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 支持的语言后缀
EXT_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".html": "HTML",
    ".css": "CSS",
    ".md": "Markdown",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".sh": "Shell",
    ".bat": "Batch",
    ".ps1": "PowerShell",
    ".toml": "TOML",
}

# 要跳过的目录
SKIP_DIRS = {".git", ".claude", ".codex", ".cursor", ".gemini",
             ".github", ".pytest_cache", "node_modules", "__pycache__",
             ".venv", "venv", ".claude-isolated"}


def count_lines(filepath: str) -> tuple[int, int, int]:
    """返回 (总行数, 代码行数, 空行数)"""
    total = 0
    code = 0
    blank = 0
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                total += 1
                stripped = line.strip()
                if stripped == "":
                    blank += 1
                else:
                    code += 1
    except Exception:
        return 0, 0, 0
    return total, code, blank


def walk_and_count(root: str) -> dict:
    """遍历目录统计"""
    stats = defaultdict(lambda: {"files": 0, "total": 0, "code": 0, "blank": 0})
    root_path = Path(root)

    for dirpath, dirnames, filenames in os.walk(root_path):
        # 跳过指定目录
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        for filename in filenames:
            ext = Path(filename).suffix.lower()
            lang = EXT_MAP.get(ext)
            if lang is None:
                continue

            filepath = os.path.join(dirpath, filename)
            total, code, blank = count_lines(filepath)
            if total == 0:
                continue

            stats[lang]["files"] += 1
            stats[lang]["total"] += total
            stats[lang]["code"] += code
            stats[lang]["blank"] += blank

    return stats


def print_stats(stats: dict):
    """打印统计表格"""
    print(f"\n{'语言':<15} {'文件数':>8} {'总行数':>10} {'代码行':>10} {'空行':>8}  {'占比':>8}")
    print("-" * 65)

    total_code = sum(s["code"] for s in stats.values())
    total_files = sum(s["files"] for s in stats.values())
    total_lines = sum(s["total"] for s in stats.values())

    for lang, s in sorted(stats.items(), key=lambda x: -x[1]["code"]):
        pct = f"{s['code'] / total_code * 100:.1f}%" if total_code > 0 else "0%"
        print(f"{lang:<15} {s['files']:>8} {s['total']:>10} {s['code']:>10} "
              f"{s['blank']:>8}  {pct:>7}")

    print("-" * 65)
    print(f"{'合计':<15} {total_files:>8} {total_lines:>10} {total_code:>10}\n")


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    stats = walk_and_count(root)
    print_stats(stats)
