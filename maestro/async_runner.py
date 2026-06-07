#!/usr/bin/env python3
"""
Async Runner — 后台异步任务执行
支持 lead agent 委派子任务，后台执行，不阻塞主线程。

用法:
  python maestro/async_runner.py start --task "实现认证模块" --agent coder
  python maestro/async_runner.py status <task_id>
  python maestro/async_runner.py list
  python maestro/async_runner.py cancel <task_id>
"""

import os, sys, json, time, uuid, threading, queue
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "maestro"))

# Load .env
from maestro.env_loader import load_dotenv
load_dotenv(PROJECT_ROOT)

from main import route_task, load_agent
from models import get_provider_config

TASKS_DIR = PROJECT_ROOT / "maestro" / "async_tasks"
TASKS_DIR.mkdir(exist_ok=True)

# In-memory task store
_tasks = {}
_tasks_lock = threading.Lock()
_result_queue = queue.Queue()


def create_task(task_text, agent_name=None, parent_id=None):
    """创建异步任务，返回 task_id"""
    task_id = str(uuid.uuid4())[:8]

    if not agent_name:
        agent_name, score, conf = route_task(task_text)

    system_prompt, model = load_agent(agent_name)
    actual_model = model  # load_agent 已通过 resolve_model 解析

    task = {
        "id": task_id,
        "task": task_text,
        "agent": agent_name,
        "model": actual_model,
        "status": "pending",  # pending/running/done/failed/cancelled
        "parent_id": parent_id,
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "finished_at": None,
        "result": None,
        "error": None,
        "system_prompt": system_prompt,
    }

    with _tasks_lock:
        _tasks[task_id] = task

    # Save to disk
    _save_task(task)

    # Start background thread
    thread = threading.Thread(target=_run_task, args=(task_id,), daemon=True)
    thread.start()

    return task_id


def _run_task(task_id):
    """后台执行任务"""
    with _tasks_lock:
        task = _tasks.get(task_id)
        if not task:
            return
        task["status"] = "running"
        task["started_at"] = datetime.now().isoformat()

    try:
        import requests as req
        base_url, api_key, headers = get_provider_config()

        if not base_url:
            with _tasks_lock:
                task["status"] = "failed"
                task["error"] = "未配置 API Key"
            _save_task(task)
            return

        resp = req.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json={
                "model": task["model"],
                "messages": [
                    {"role": "system", "content": task["system_prompt"]},
                    {"role": "user", "content": task["task"]},
                ],
                "temperature": 0.7,
                "max_tokens": 4096,
            },
            timeout=300,
        )

        if resp.status_code == 200:
            result = resp.json()
            content = result["choices"][0]["message"]["content"]
            task["status"] = "done"
            task["result"] = content
        else:
            task["status"] = "failed"
            task["error"] = f"API error {resp.status_code}: {resp.text[:200]}"

    except Exception as e:
        task["status"] = "failed"
        task["error"] = str(e)

    task["finished_at"] = datetime.now().isoformat()
    _save_task(task)
    _result_queue.put(task_id)


def _save_task(task):
    task_file = TASKS_DIR / f"{task['id']}.json"
    # Create a safe copy for serialization (remove prompt to save space)
    safe = {k: v for k, v in task.items() if k != "system_prompt"}
    task_file.write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")


def get_task(task_id):
    with _tasks_lock:
        return _tasks.get(task_id)


def list_tasks(status=None):
    with _tasks_lock:
        tasks = list(_tasks.values())
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    return sorted(tasks, key=lambda t: t["created_at"], reverse=True)


def cancel_task(task_id):
    with _tasks_lock:
        task = _tasks.get(task_id)
        if task and task["status"] in ("pending", "running"):
            task["status"] = "cancelled"
            _save_task(task)
            return True
    return False


def wait_for_task(task_id, timeout=300):
    """阻塞等待任务完成"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        task = get_task(task_id)
        if task and task["status"] in ("done", "failed", "cancelled"):
            return task
        time.sleep(1)
    return get_task(task_id)


# CLI
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "start":
        task_text = None
        agent = None
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--task" and i + 1 < len(sys.argv):
                task_text = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--agent" and i + 1 < len(sys.argv):
                agent = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        if not task_text:
            task_text = input("任务: ").strip()
            if not task_text:
                print("任务不能为空")
                sys.exit(1)
        tid = create_task(task_text, agent)
        print(f"Task {tid} started ({agent or 'auto'})")

    elif cmd == "status":
        if len(sys.argv) < 3:
            print("用法: python maestro/async_runner.py status <task_id>")
            sys.exit(1)
        tid = sys.argv[2]
        task = get_task(tid)
        if task:
            print(json.dumps({k: task[k] for k in ["id", "status", "agent", "task", "error"]},
                             ensure_ascii=False, indent=2))
        else:
            print(f"Task {tid} not found")

    elif cmd == "list":
        tasks = list_tasks()
        if not tasks:
            print("  没有后台任务")
        for t in tasks[:20]:
            print(f"  [{t['status']:>9}] {t['id']}  {t['agent']:<20}  {t['task'][:50]}")

    elif cmd == "cancel":
        if len(sys.argv) < 3:
            print("用法: python maestro/async_runner.py cancel <task_id>")
            sys.exit(1)
        tid = sys.argv[2]
        if cancel_task(tid):
            print(f"Task {tid} cancelled")
        else:
            print(f"Cannot cancel {tid}")

    elif cmd == "wait":
        if len(sys.argv) < 3:
            print("用法: python maestro/async_runner.py wait <task_id>")
            sys.exit(1)
        tid = sys.argv[2]
        task = wait_for_task(tid)
        if task and task["status"] == "done":
            print(task["result"])
        elif task:
            print(f"Task failed: {task.get('error')}")

    else:
        print(f"未知命令: {cmd}")
        print(__doc__)
