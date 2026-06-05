#!/usr/bin/env python3
"""
清理后台 claude.exe 子进程
- 保留主进程（内存最大）
- 杀掉运行超过 5 分钟的子进程
- 记录清理日志
- --kill <task_id>: 杀特定任务的 agent 进程
"""
import subprocess
import json
import sys
import os
from datetime import datetime

PROJECT_ROOT = os.environ.get("CLAUDE_PROJECT_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MAESTRO_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(MAESTRO_DIR, "cleanup.log")
STAMP_FILE = os.path.join(MAESTRO_DIR, ".cleanup-stamp")
TASKS_DIR = os.path.join(MAESTRO_DIR, "tasks")
MIN_AGE_MINUTES = 5
THROTTLE_SEC = 10 * 60  # 10 分钟节流，避免频繁执行


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_claude_processes() -> list[dict]:
    """通过 PowerShell 获取所有 claude.exe 进程详情"""
    ps_cmd = (
        'powershell -NoProfile -ExecutionPolicy Bypass -Command '
        '"Get-CimInstance Win32_Process -Filter \\"Name=\'claude.exe\'\\" | '
        'Select-Object ProcessId, CreationDate, WorkingSetSize | ConvertTo-Json"'
    )
    result = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=15, shell=True)
    if result.returncode != 0 or not result.stdout.strip():
        return []

    raw = result.stdout.strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    # 单个进程时 ConvertTo-Json 返回对象而非数组
    if isinstance(data, dict):
        data = [data]

    processes = []
    for p in data:
        pid = p.get("ProcessId")
        mem = p.get("WorkingSetSize") or 0
        created_str = p.get("CreationDate", "")
        try:
            # CreationDate 格式: "2026/6/1 17:57:54"（本地时间）
            created = datetime.strptime(created_str.strip(), "%Y/%m/%d %H:%M:%S")
        except (ValueError, IndexError):
            created = datetime(2000, 1, 1)  # 解析失败用极早时间，确保被清理

        processes.append({"pid": pid, "memory_kb": mem // 1024, "created": created, "raw_created": created_str})

    return processes


def identify_main(processes: list[dict]) -> dict | None:
    """主进程 = 内存最大的那个"""
    if not processes:
        return None
    return max(processes, key=lambda p: p["memory_kb"])


def kill_process(pid: int) -> bool:
    """强制终止进程"""
    result = subprocess.run(
        f"taskkill /PID {pid} /F",
        capture_output=True, text=True, timeout=10, shell=True
    )
    return result.returncode == 0


def kill_process_tree(pid: int) -> bool:
    """强制终止进程及其所有子进程"""
    result = subprocess.run(
        f"taskkill /PID {pid} /F /T",
        capture_output=True, text=True, timeout=10, shell=True
    )
    return result.returncode == 0


def find_task_processes(task_id: str) -> list[int]:
    """通过扫描进程命令行查找属于指定 task_id 的进程 PID 列表。

    策略：
    1. 查找 powershell.exe 命令行中含 _launch_{task_id} 的进程
    2. 查找 claude.exe 命令行中含 {task_id} 的进程
    """
    pids: list[int] = []

    # 方法1：查找 powershell 启动脚本
    ps_cmd1 = (
        'powershell -NoProfile -ExecutionPolicy Bypass -Command '
        f'"Get-CimInstance Win32_Process -Filter \\"Name=\'powershell.exe\'\\" | '
        f'Where-Object {{ $_.CommandLine -like \'*_launch_{task_id}*\' }} | '
        f'Select-Object ProcessId | ConvertTo-Json"'
    )
    result1 = subprocess.run(ps_cmd1, capture_output=True, text=True, timeout=15, shell=True)
    if result1.returncode == 0 and result1.stdout.strip():
        try:
            data = json.loads(result1.stdout.strip())
            if isinstance(data, dict):
                data = [data]
            for p in data:
                pid = p.get("ProcessId")
                if pid and pid not in pids:
                    pids.append(pid)
        except json.JSONDecodeError:
            pass

    # 方法2：查找 claude.exe 命令行中含 task_id 的进程
    ps_cmd2 = (
        'powershell -NoProfile -ExecutionPolicy Bypass -Command '
        f'"Get-CimInstance Win32_Process -Filter \\"Name=\'claude.exe\'\\" | '
        f'Where-Object {{ $_.CommandLine -like \'*{task_id}*\' }} | '
        f'Select-Object ProcessId | ConvertTo-Json"'
    )
    result2 = subprocess.run(ps_cmd2, capture_output=True, text=True, timeout=15, shell=True)
    if result2.returncode == 0 and result2.stdout.strip():
        try:
            data = json.loads(result2.stdout.strip())
            if isinstance(data, dict):
                data = [data]
            for p in data:
                pid = p.get("ProcessId")
                if pid and pid not in pids:
                    pids.append(pid)
        except json.JSONDecodeError:
            pass

    # 方法3：查找 cmd.exe / node.exe 命令行中含 task_id 的进程（reasonix 等）
    for proc_name in ("cmd.exe", "node.exe"):
        ps_cmd3 = (
            'powershell -NoProfile -ExecutionPolicy Bypass -Command '
            f'"Get-CimInstance Win32_Process -Filter \\"Name=\'{proc_name}\'\\" | '
            f'Where-Object {{ $_.CommandLine -like \'*{task_id}*\' }} | '
            f'Select-Object ProcessId | ConvertTo-Json"'
        )
        result3 = subprocess.run(ps_cmd3, capture_output=True, text=True, timeout=15, shell=True)
        if result3.returncode == 0 and result3.stdout.strip():
            try:
                data = json.loads(result3.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for p in data:
                    pid = p.get("ProcessId")
                    if pid and pid not in pids:
                        pids.append(pid)
            except json.JSONDecodeError:
                pass

    return pids


def kill_task(task_id: str) -> int:
    """读取任务 JSON，找到对应进程并终止。返回杀掉的进程数。"""
    task_file = os.path.join(TASKS_DIR, f"{task_id}.json")
    if not os.path.exists(task_file):
        log(f"任务文件不存在: {task_file}")
        print(f"错误: 任务 {task_id} 不存在 (文件未找到: {task_file})")
        return 0

    with open(task_file, "r", encoding="utf-8") as f:
        task = json.load(f)

    agent = task.get("agent", "?")
    status = task.get("status", "?")
    task_desc = task.get("task", "")[:60]
    log(f"kill_task: {task_id} agent={agent} status={status} task={task_desc}")

    # 优先使用 task JSON 中已记录的 PID
    recorded_pid = task.get("pid")
    if recorded_pid and kill_process_tree(recorded_pid):
        log(f"已通过记录 PID={recorded_pid} 终止 task={task_id}")
        return 1

    # 回退：扫描进程命令行
    pids = find_task_processes(task_id)
    if not pids:
        log(f"未找到 task={task_id} 的运行进程")
        print(f"未找到任务 {task_id} 的运行进程（agent={agent}, status={status}）")
        return 0

    killed = 0
    for pid in pids:
        log(f"终止进程 PID={pid} (task={task_id}, agent={agent})")
        if kill_process_tree(pid):
            log(f"  已终止 PID={pid} 及其子进程")
            killed += 1
            print(f"已终止进程 PID={pid}")
        else:
            log(f"  终止失败 PID={pid}")
            print(f"终止失败 PID={pid}")

    # 将找到的 PID 写回 task JSON，下次可直接用
    if killed > 0 and not recorded_pid:
        task["pid"] = pids[0]
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump(task, f, ensure_ascii=False, indent=2)

    return killed


def main():
    import argparse

    parser = argparse.ArgumentParser(description="清理后台 claude.exe 子进程")
    parser.add_argument("--kill", help="杀指定 task_id 的 agent 进程")
    args = parser.parse_args()

    # ── --kill 模式：定向杀进程 ──
    if args.kill:
        task_id = args.kill.strip()
        if not task_id:
            print("错误: 请提供有效的 task_id")
            sys.exit(1)
        log("=" * 50)
        log(f"--kill 模式: task_id={task_id}")
        killed = kill_task(task_id)
        log(f"kill 完成: 杀掉 {killed} 个进程")
        log("=" * 50)
        if killed == 0:
            sys.exit(1)
        return

    # === 节流检查：距上次执行不足 10 分钟则跳过 ===
    now_ts = datetime.now().timestamp()
    try:
        if os.path.exists(STAMP_FILE):
            with open(STAMP_FILE) as f:
                last_ts = float(f.read().strip())
            if now_ts - last_ts < THROTTLE_SEC:
                return  # 静默跳过
    except (ValueError, OSError):
        pass

    # 更新时间戳
    os.makedirs(os.path.dirname(STAMP_FILE), exist_ok=True)
    with open(STAMP_FILE, "w") as f:
        f.write(str(int(now_ts)))

    log("=" * 50)
    log("开始清理扫描")

    processes = get_claude_processes()
    log(f"发现 {len(processes)} 个 claude.exe 进程")

    if len(processes) <= 1:
        log("仅有主进程，无需清理")
        log("=" * 50)
        return

    main_proc = identify_main(processes)
    log(f"主进程: PID={main_proc['pid']}, 内存={main_proc['memory_kb']} KB")

    now = datetime.now()
    killed = 0
    skipped = 0

    for p in processes:
        if p["pid"] == main_proc["pid"]:
            continue

        age = now - p["created"]
        age_minutes = age.total_seconds() / 60

        if age_minutes >= MIN_AGE_MINUTES:
            log(f"清理子进程: PID={p['pid']}, 内存={p['memory_kb']} KB, 运行={age_minutes:.1f} 分钟")
            if kill_process(p["pid"]):
                log(f"  已终止 PID={p['pid']}")
                killed += 1
            else:
                log(f"  终止失败 PID={p['pid']}")
        else:
            log(f"跳过（运行仅 {age_minutes:.1f} 分钟）: PID={p['pid']}")
            skipped += 1

    log(f"清理完成: 杀掉 {killed} 个, 跳过 {skipped} 个, 保留主进程 PID={main_proc['pid']}")
    log("=" * 50)


if __name__ == "__main__":
    main()
