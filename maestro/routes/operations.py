"""操作历史 — 记录 Agent 的文件/命令操作"""

import json
import time
from pathlib import Path

OPS_FILE = Path(__file__).resolve().parent.parent / "operations.jsonl"


def record_operation(agent: str, op_type: str, target: str, detail: str = ""):
    """记录一次操作"""
    entry = {
        "ts": time.time(),
        "agent": agent,
        "type": op_type,  # file_write, file_delete, command_run, etc.
        "target": target,
        "detail": detail[:500],
    }
    try:
        with open(OPS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def handle_list(handler, parsed):
    """GET /api/operations — 最近 50 条操作记录"""
    if not OPS_FILE.exists():
        handler.send_json({"ok": True, "operations": []})
        return True

    ops = []
    try:
        with open(OPS_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines[-50:]:
            if line.strip():
                ops.append(json.loads(line))
        ops.reverse()
    except Exception:
        pass

    handler.send_json({"ok": True, "operations": ops})
    return True
