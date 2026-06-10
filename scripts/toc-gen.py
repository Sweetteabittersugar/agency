#!/usr/bin/env python3
"""Markdown TOC Generator - scan all .md files and generate a linked index."""

import os
import re
from pathlib import Path


def get_title(md_path: str) -> str:
    """Extract the first # heading from a .md file, fallback to filename."""
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            for line in f:
                m = re.match(r"^#\s+(.+)", line)
                if m:
                    return m.group(1).strip()
    except Exception:
        pass
    return Path(md_path).stem.replace("-", " ").replace("_", " ")


def scan_md(root: str = ".") -> list[str]:
    """Recursively find all .md files, skipping hidden directories."""
    result = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in sorted(filenames):
            if fn.endswith(".md") and not fn.startswith("."):
                result.append(os.path.join(dirpath, fn))
    return result


def gen_toc(files: list[str], root: str = ".") -> str:
    """Generate a Markdown table-of-contents from a list of file paths."""
    lines = [
        "# 📚 Project Document Index",
        "",
        f"Total: **{len(files)}** documents",
        "",
    ]
    current_dir = ""

    for fp in files:
        rel = os.path.relpath(fp, root)
        dirname = os.path.dirname(rel)
        filename = os.path.basename(fp)
        title = get_title(fp)

        if dirname != current_dir:
            current_dir = dirname
            label = f"📁 {dirname}/" if dirname else "📄 Root"
            lines.append(f"### {label}")
            lines.append("")

        link = rel.replace("\\", "/")
        lines.append(f"- [{title}]({link})  `{filename}`")

    return "\n".join(lines) + "\n"


def main() -> None:
    files = scan_md(".")
    toc = gen_toc(files)

    out_path = "docs/TOC.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(toc)

    print(f"Done: {out_path} ({len(files)} files indexed)")


if __name__ == "__main__":
    main()
