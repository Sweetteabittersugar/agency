"""Cron 定时任务调度器 — 基于线程 + JSON 持久化

为何不用 APScheduler：减少依赖，用标准库 threading + time 即可实现
简单的定时轮询。任务持久化到 cron_jobs.json。"""

import json, logging, threading, time
from pathlib import Path
from datetime import datetime

log = logging.getLogger(__name__)
CRON_FILE = Path(__file__).resolve().parent / "cron_jobs.json"
_watcher = None
_stop_flag = False


def _load_jobs():
    if CRON_FILE.exists():
        try:
            return json.loads(CRON_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_jobs(jobs):
    CRON_FILE.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")


def start_scheduler(chat_callback=None):
    """启动后台定时任务监控线程。不可移除——定时任务依赖此线程"""
    global _watcher, _stop_flag
    if _watcher and _watcher.is_alive():
        return
    _stop_flag = False

    def _watch():
        last_minute = -1
        while not _stop_flag:
            now = datetime.now()
            if now.minute != last_minute:
                last_minute = now.minute
                jobs = _load_jobs()
                for j in jobs:
                    if j.get("enabled", True) and _match_cron(j.get("cron_expr", ""), now):
                        log.info(f"CRON executing: {j.get('prompt', '')[:50]}...")
                        if chat_callback:
                            try:
                                chat_callback(j.get("prompt", ""), j.get("api_provider", "deepseek"))
                            except Exception as e:
                                log.error(f"CRON callback error: {e}")
            time.sleep(30)

    _watcher = threading.Thread(target=_watch, daemon=True)
    _watcher.start()
    log.info(f"Cron watcher started, {len(_load_jobs())} jobs loaded")


def _match_cron(expr, now):
    """简单 cron 匹配：minute hour day month weekday"""
    try:
        parts = expr.strip().split()
        if len(parts) != 5:
            return False
        return (
            _match_field(parts[0], now.minute)
            and _match_field(parts[1], now.hour)
            and _match_field(parts[2], now.day)
            and _match_field(parts[3], now.month)
            and _match_field(parts[4], now.weekday())
        )
    except Exception:
        return False


def _match_field(pattern, value):
    if pattern == "*":
        return True
    if str(value) == pattern:
        return True
    if "/" in pattern and pattern.startswith("*/"):
        step = int(pattern[2:])
        return value % step == 0
    return False


def add_job(job_id, prompt, cron_expr, api_provider="deepseek", enabled=True):
    jobs = _load_jobs()
    jobs = [j for j in jobs if j["id"] != job_id]
    new_job = {
        "id": job_id,
        "prompt": prompt,
        "cron_expr": cron_expr,
        "api_provider": api_provider,
        "enabled": enabled,
        "created_at": datetime.now().isoformat(),
    }
    jobs.append(new_job)
    _save_jobs(jobs)
    return new_job


def remove_job(job_id):
    jobs = [j for j in _load_jobs() if j["id"] != job_id]
    _save_jobs(jobs)


def list_jobs():
    return _load_jobs()
