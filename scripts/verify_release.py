#!/usr/bin/env python3
"""Validate the public source release metadata and portability boundary."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
EXPECTED_VERSION = "0.5.0"
TEXT_SUFFIXES = {
    ".bat", ".css", ".html", ".js", ".json", ".md", ".ps1",
    ".py", ".sh", ".toml", ".txt", ".yaml", ".yml",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    agent_registry = yaml.safe_load((ROOT / "agent.yaml").read_text(encoding="utf-8"))
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    require(version == EXPECTED_VERSION, "VERSION is not the expected release version")
    require(pyproject["project"]["version"] == version, "Python version does not match VERSION")
    require(package["version"] == version, "Node metadata does not match VERSION")
    require(agent_registry["version"] == version, "Agent metadata does not match VERSION")
    require(
        re.search(rf"^## \[{re.escape(version)}\]", changelog, re.MULTILINE) is not None,
        "CHANGELOG has no release heading",
    )
    for installer in ("install.sh", "install.ps1", "install.bat"):
        require(
            f"v{version}" in (ROOT / installer).read_text(encoding="utf-8"),
            f"{installer} version does not match VERSION",
        )

    agents = agent_registry.get("agents", {})
    require(isinstance(agents, dict) and len(agents) == 33, "agent.yaml must contain 33 agents")
    missing_agent_files = [
        item.get("file", "") for item in agents.values()
        if not (ROOT / str(item.get("file", ""))).is_file()
    ]
    require(not missing_agent_files, f"missing agent files: {missing_agent_files}")
    skills = [path for path in (ROOT / "skills").iterdir() if path.is_dir()]
    require(len(skills) == 7, "skills directory must contain 7 skills")

    require(package.get("private") is True, "package.json must be private")
    require("publishConfig" not in package, "npm publishing must remain disabled")
    require("postinstall" not in package.get("scripts", {}), "automatic postinstall is forbidden")
    require(not (ROOT / ".context").exists(), "private .context directory is present")
    require(not (ROOT / "maestro" / "control_plane_bridge.py").exists(), "private bridge is present")

    forbidden = {
        "workspace drive path": "D:" + "/ai",
        "workspace command": "task" + "ctl",
        "private evidence path": ".context" + "/evidence",
        "personal home path": "C:" + "\\" + "Users" + "\\" + "lenovo",
    }
    violations: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(
            part in {".claude-isolated", ".git", ".pytest_cache", ".venv", "node_modules"}
            for part in path.parts
        ):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for label, marker in forbidden.items():
            if marker.lower() in text.lower():
                violations.append(f"{path.relative_to(ROOT)}: {label}")
    require(not violations, "forbidden public-tree content: " + ", ".join(violations))

    print(f"Release metadata: {version}; agents: {len(agents)}; skills: {len(skills)}")
    print("Public source boundary: passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"release verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
