#!/usr/bin/env python3
"""Install the source tree in a fresh venv and exercise non-starting CLI paths."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {command!r}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="agency-source-smoke-") as temp:
        temp_path = Path(temp)
        venv_path = temp_path / "venv"
        venv.EnvBuilder(with_pip=True).create(venv_path)
        scripts = venv_path / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        agency = scripts / ("agency.exe" if os.name == "nt" else "agency")
        _run([str(python), "-m", "pip", "install", "--no-deps", str(ROOT)], cwd=temp_path)
        version = _run([str(agency), "--version"], cwd=temp_path)
        if version.stdout.strip() != "0.5.0":
            raise RuntimeError(f"unexpected version output: {version.stdout!r}")
        help_result = _run([str(agency), "--help"], cwd=temp_path)
        if "start" not in help_result.stdout:
            raise RuntimeError("agency --help did not describe the start command")
    print("Source install smoke: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
