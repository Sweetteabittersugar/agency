#!/usr/bin/env python3
"""任务跟踪系统 — 任务列表、查任务、进度查询。
用法:
  python task-tracker.py --list              # 任务列表（最近20条）
  python task-tracker.py --list --all        # 全部任务
  python task-tracker.py --task <id>         # 查单个任务详情
  python task-tracker.py --progress          # 总体进度
  python task-tracker.py --agent <name>      # 按 agent 筛选
  python task-tracker.py --sync              # 从 tasks/ + results/ 重新扫描同步 board
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = os.environ.get(
    "CLAUDE_PROJECT_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

MAESTRO_DIR = Path(PROJECT_ROOT) / "maestro"
BOARD_FILE = MAESTRO_DIR / "task-board.json"
TASKS_DIR = MAESTRO_DIR / "tasks"
RESULTS_DIR = MAESTRO_DIR / "results"


def sync_board():
    """扫描 tasks/ 和 results/ 目录，更新 task-board.json"""
    tasks = []

    if TASKS_DIR.exists():
        for f in sorted(TASKS_DIR.glob("*.json")):
            try:
                with open(f, encoding="utf-8") as fp:
                    t = json.load(fp)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

            tid = t.get("task_id", f.stem)
            result_file = RESULTS_DIR / f"{tid}.txt"
            status = t.get("status", "dispatched")
            completed_at = t.get("completed_at")

            # 根据结果文件自动判断状态
            if result_file.exists():
                try:
                    raw = result_file.read_text(encoding="utf-8-sig")
                    first_line = raw.split("\n")[0].strip() if raw else ""
                    if "DONE" in first_line:
                        status = "done"
                        if not completed_at:
                            completed_at = datetime.fromtimestamp(
                                result_file.stat().st_mtime, tz=timezone.utc
                            ).isoformat()
                    elif "FAILED" in first_line:
                        status = "failed"
                        if not completed_at:
                            completed_at = datetime.fromtimestamp(
                                result_file.stat().st_mtime, tz=timezone.utc
                            ).isoformat()
                except Exception as _e:
                    # log corrupted result files instead of silently skipping them
                    print(f"[task-tracker] result read failed: {_e}", file=__import__('sys').stderr)
            elif status == "done" or status == "failed":
                # 结果文件已被删除但状态还标记为完成
                status = "dispatched"

            task_entry = {
                "task_id": tid,
                "agent": t.get("agent", "?"),
                "task": t.get("task", "")[:60],
                "status": status,
                "created_at": t.get("created_at", ""),
                "completed_at": completed_at,
                "result": None,
                "summary": None,
            }

            # 提取结果摘要
            if result_file.exists():
                try:
                    raw = result_file.read_text(encoding="utf-8-sig")
                    first_line = raw.split("\n")[0].strip() if raw else ""
                    task_entry["result"] = first_line

                    # 提取用户摘要
                    in_summary = False
                    summary_lines = []
                    for line in raw.split("\n")[1:]:
                        if line.strip().startswith("## 用户摘要"):
                            in_summary = True
                            continue
                        if in_summary:
                            if line.strip().startswith("## ") and "用户摘要" not in line:
                                break
                            summary_lines.append(line)
                    if summary_lines:
                        task_entry["summary"] = "\n".join(summary_lines).strip()[:120]
                except Exception as _e:
                    # log corrupted result files instead of silently skipping them
                    print(f"[task-tracker] result read failed: {_e}", file=__import__('sys').stderr)

            tasks.append(task_entry)

    # 统计
    stats = {
        "total": len(tasks),
        "done": sum(1 for t in tasks if t["status"] == "done"),
        "failed": sum(1 for t in tasks if t["status"] == "failed"),
        "in_progress": sum(1 for t in tasks if t["status"] == "in_progress"),
        "dispatched": sum(1 for t in tasks if t["status"] == "dispatched"),
    }

    board = {
        "version": "1.0",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "tasks": tasks,
        "stats": stats,
    }

    with open(BOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(board, f, ensure_ascii=False, indent=2)

    return board


def load_board():
    if BOARD_FILE.exists():
        with open(BOARD_FILE, encoding="utf-8") as f:
            return json.load(f)
    return sync_board()


def list_tasks(show_all=False, agent_filter=None):
    board = load_board()
    tasks = board["tasks"]
    if agent_filter:
        tasks = [t for t in tasks if t["agent"] == agent_filter]
    limit = None if show_all else 20
    tasks = tasks[-limit:] if limit else tasks

    stats = board.get("stats", {})
    print("=== 任务看板 ===")
    print(
        f"总计:{stats.get('total', '?')} 完成:{stats.get('done', '?')} 失败:{stats.get('failed', '?')} 进行中:{stats.get('in_progress', '?')} 待处理:{stats.get('dispatched', '?')}"
    )
    print()

    status_icon = {
        "done": "[OK]",
        "failed": "[XX]",
        "in_progress": "[>>]",
        "dispatched": "[  ]",
    }

    for t in tasks:
        icon = status_icon.get(t["status"], "[?]")
        print(f"  {icon} {t['agent']:10s} {t['task_id']}  {t['task'][:50]}")
        if t.get("summary"):
            print(f"     摘要: {t['summary'][:80]}")
    print()


def query_task(task_id):
    board = load_board()
    for t in board["tasks"]:
        if t["task_id"] == task_id:
            print(f"=== 任务 {task_id} ===")
            print(f"  Agent:    {t['agent']}")
            print(f"  状态:     {t['status']}")
            print(f"  创建:     {t['created_at']}")
            if t.get("completed_at"):
                print(f"  完成:     {t['completed_at']}")
            print(f"  任务:     {t['task']}")
            if t.get("result"):
                print(f"  结果:     {t['result']}")
            if t.get("summary"):
                print(f"  摘要:     {t['summary']}")
            return
    print(f"未找到任务: {task_id}")


def show_progress():
    board = load_board()
    stats = board.get("stats", {})
    total = stats.get("total", 0)
    done = stats.get("done", 0)
    failed = stats.get("failed", 0)
    in_prog = stats.get("in_progress", 0)
    dispatched = stats.get("dispatched", 0)

    completed = done + failed
    pct = (completed / total * 100) if total > 0 else 0

    print("=== 总体进度 ===")
    print(f"  总任务数:   {total}")
    print(f"  已完成:     {done}  (成功)")
    print(f"  已失败:     {failed}")
    print(f"  进行中:     {in_prog}")
    print(f"  待处理:     {dispatched}")
    print(f"  完成率:     {pct:.0f}%  ({completed}/{total})")

    # 按 agent 分布
    print()
    print("=== 按 Agent 分布 ===")
    agents = {}
    for t in board["tasks"]:
        a = t["agent"]
        if a not in agents:
            agents[a] = {"done": 0, "failed": 0, "other": 0}
        if t["status"] == "done":
            agents[a]["done"] += 1
        elif t["status"] == "failed":
            agents[a]["failed"] += 1
        else:
            agents[a]["other"] += 1

    for name, cnt in sorted(agents.items()):
        total_a = cnt["done"] + cnt["failed"] + cnt["other"]
        bar = "#" * cnt["done"] + "." * cnt["other"]
        if cnt["failed"]:
            bar += f"  X{cnt['failed']}"
        print(f"  {name:12s} [{bar}] {total_a}")

    # 最近完成
    print()
    print("=== 最近完成 (最多5条) ===")
    done_tasks = [t for t in board["tasks"] if t["status"] == "done"]
    for t in sorted(done_tasks, key=lambda x: x.get("completed_at") or "", reverse=True)[:5]:
        print(f"  {t['task_id']}  {t['agent']:10s}  {t['task'][:45]}")


def main():
    parser = argparse.ArgumentParser(description="任务跟踪系统")
    parser.add_argument("--list", action="store_true", help="任务列表")
    parser.add_argument("--all", action="store_true", help="显示全部（配合 --list）")
    parser.add_argument("--task", help="查询指定任务 ID")
    parser.add_argument("--progress", action="store_true", help="总体进度")
    parser.add_argument("--agent", help="按 agent 筛选（配合 --list）")
    parser.add_argument("--sync", action="store_true", help="同步 board（扫描磁盘）")
    args = parser.parse_args()

    if args.sync:
        board = sync_board()
        print(f"同步完成: {board['stats']['total']} 条任务")
        return

    if args.task:
        query_task(args.task)
    elif args.progress:
        show_progress()
    elif args.list or args.agent:
        list_tasks(show_all=args.all, agent_filter=args.agent)
    else:
        # 默认显示进度 + 最近列表
        show_progress()
        print()
        list_tasks()


if __name__ == "__main__":
    main()
