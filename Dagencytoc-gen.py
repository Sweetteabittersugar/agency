#!/usr/bin/env python3
"""
Markdown 文件目录生成器
扫描当前目录所有 .md 文件，生成一个带链接的目录索引。
"""

import os
import re
from pathlib import Path


def get_title(md_path: str) -> str:
    """提取 md 文件的第一个 # 标题，没有则用文件名"""
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            for line in f:
                match = re.match(r"^#\s+(.+)", line)
                if match:
                    return match.group(1).strip()
    except Exception:
        pass
    return Path(md_path).stem.replace("-", " ").replace("_", " ")


def scan_md_files(root: str = ".") -> list[str]:
    """递归扫描所有 .md 文件"""
    md_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for f in filenames:
            if f.endswith(".md") and not f.startswith("."):
                full = os.path.join(dirpath, f)
                md_files.append(full)
    return sorted(md_files)


def generate_toc(md_files: list[str], root: str = ".") -> str:
    """生成目录 Markdown"""
    lines = ["# 📚 项目文档索引\n", f"共 {len(md_files)} 个文档\n"]
    current_dir = ""

    for f in md_files:
        rel = os.path.relpath(f, root)
        d = os.path.dirname(rel)
        name = os.path.basename(f)
        title = get_title(f)

        if d != current_dir:
            current_dir = d
            label = f"📁 {d}/" if d else "📄 根目录"
            lines.append(f"\n### {label}\n")

        link = rel.replace("\\", "/")
        lines.append(f"- [{title}]({link})  `{name}`")

    return "\n".join(lines) + "\n"


def main():
    root = "."
    md_files = scan_md_files(root)
    toc = generate_toc(md_files, root)

    out_path = "TOC.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(toc)

    print(f"✅ 已生成 {out_path}（{len(md_files)} 个文档）")


if __name__ == "__main__":
    main()
