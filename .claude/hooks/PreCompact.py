#!/usr/bin/env python3
"""PreCompact Hook — 上下文压缩前提取关键信息"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ANCHOR_FILE = PROJECT_ROOT / "maestro" / ".compact_anchor.json"


def extract_from_stdin():
    """从 stdin 读取当前对话内容"""
    try:
        if not sys.stdin.isatty():
            return sys.stdin.read()
    except Exception:
        pass
    return ""


def extract_pending_tasks(text):
    """提取未完成任务 ID"""
    task_ids = []
    # 匹配常见任务 ID 模式
    patterns = [
        r"任务\s*[#＃]?\s*(\d+)",
        r"task[_\s]?(\d+)",
        r"#(\d{2,})",
        r"TODO.*?(\d+)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        task_ids.extend(matches)
    return list(set(task_ids))[:20]


def extract_last_user_request(text):
    """提取用户最后要求"""
    lines = text.strip().split("\n")
    # 从后往前找用户消息
    user_markers = ["用户:", "User:", "Human:", ">>>"]
    for line in reversed(lines):
        stripped = line.strip()
        if any(stripped.startswith(m) for m in user_markers):
            content = stripped.split(":", 1)[-1].strip()
            return content[:500] if content else ""
        if stripped and not stripped.startswith(("Assistant:", "AI:", "Claude:")):
            if len(stripped) > 20:
                return stripped[:500]
    return ""


def extract_current_branch(text):
    """提取当前分支"""
    match = re.search(r"(?:branch|分支)[:\s]+(\S+)", text, re.IGNORECASE)
    if match:
        return match.group(1)
    return "master"


def main():
    text = extract_from_stdin()
    if not text:
        # 无 stdin 时使用环境变量
        text = os.environ.get("CLAUDE_CODE_SESSION_CONTEXT", "")

    anchor = {
        "pending_task_ids": extract_pending_tasks(text),
        "last_user_request": extract_last_user_request(text),
        "current_branch": extract_current_branch(text),
        "compacted_at": datetime.now().isoformat(),
        "text_length": len(text),
    }

    ANCHOR_FILE.parent.mkdir(parents=True, exist_ok=True)
    ANCHOR_FILE.write_text(
        json.dumps(anchor, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"status": "compact_anchor_saved", "tasks": len(anchor["pending_task_ids"])}))


if __name__ == "__main__":
    main()
