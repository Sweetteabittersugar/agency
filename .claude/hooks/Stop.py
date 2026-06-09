#!/usr/bin/env python3
"""Stop Hook — 会话结束时统计并清理"""
import json
import os
import sys
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_FILE = PROJECT_ROOT / "maestro" / "session_log.jsonl"
TASKS_DIR = PROJECT_ROOT / "maestro" / "tasks"
RESULTS_DIR = PROJECT_ROOT / "maestro" / "results"


def count_tasks():
    """统计任务数"""
    if not TASKS_DIR.exists():
        return 0, 0
    total = len(list(TASKS_DIR.glob("*.json")))
    completed = 0
    for tf in TASKS_DIR.glob("*.json"):
        try:
            data = json.loads(tf.read_text(encoding="utf-8"))
            if data.get("status") == "completed":
                completed += 1
        except Exception:
            pass
    return total, completed


def count_agent_calls():
    """统计 Agent 调用次数"""
    if not RESULTS_DIR.exists():
        return 0
    return len(list(RESULTS_DIR.glob("*.json")))


def estimate_tokens():
    """从 SessionStart hook 输出估算 token"""
    status_file = PROJECT_ROOT / "maestro" / "env_status.json"
    # 尝试从 Claude Code 项目目录读取会话信息
    home = Path.home()
    proj = str(PROJECT_ROOT)
    slug = proj.replace("\\", "/").rstrip("/").replace(":/", "--").replace("/", "-").lstrip("-")
    projects_dir = home / ".claude" / "projects" / slug
    total_tokens = 0
    if projects_dir.exists():
        for jf in sorted(projects_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:1]:
            try:
                for line in jf.read_text(encoding="utf-8").strip().split("\n"):
                    try:
                        entry = json.loads(line)
                        usage = entry.get("usage", {})
                        total_tokens += usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                    except Exception:
                        pass
            except Exception:
                pass
    return total_tokens


def cleanup_temp():
    """清理临时文件"""
    cleaned = 0
    # 清理 .compact_anchor.json 以外的临时文件
    temp_patterns = ["*.tmp", "*.temp", "__pycache__"]
    for pattern in temp_patterns:
        for f in PROJECT_ROOT.rglob(pattern):
            try:
                if f.is_file():
                    f.unlink()
                    cleaned += 1
                elif f.is_dir():
                    shutil.rmtree(str(f), ignore_errors=True)
                    cleaned += 1
            except Exception:
                pass
    return cleaned


def main():
    total_tasks, completed_tasks = count_tasks()
    agent_calls = count_agent_calls()
    tokens = estimate_tokens()
    cleaned = cleanup_temp()

    log_entry = {
        "session_end": datetime.now().isoformat(),
        "tasks_total": total_tasks,
        "tasks_completed": completed_tasks,
        "agent_calls": agent_calls,
        "tokens_estimate": tokens,
        "temp_files_cleaned": cleaned,
    }

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    print(json.dumps(log_entry))


if __name__ == "__main__":
    main()
