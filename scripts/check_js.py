#!/usr/bin/env python3
"""Run Node's parser over every tracked JavaScript source file."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    node = shutil.which("node")
    if not node:
        print("node is required for JavaScript syntax validation", file=sys.stderr)
        return 1
    files = sorted((ROOT / "webui" / "js").rglob("*.js"))
    for path in files:
        result = subprocess.run(
            [node, "--check", str(path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            print(result.stdout, end="")
            print(result.stderr, end="", file=sys.stderr)
            return result.returncode
    print(f"JavaScript syntax: {len(files)} files passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
