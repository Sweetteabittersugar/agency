"""统一的 Agent .md 解析"""
import yaml
from pathlib import Path


def parse_agent_md(filepath: Path) -> dict:
    """解析 Agent 的 .md 文件，返回 {name, description, model, tools, body}"""
    content = filepath.read_text(encoding="utf-8")
    fm = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
            except Exception:
                pass
            body = parts[2].strip() if len(parts) > 2 else ""
    return {
        "name": filepath.stem,
        "description": fm.get("description", ""),
        "model": fm.get("model", ""),
        "tools": fm.get("tools", []),
        "body": body,
    }
