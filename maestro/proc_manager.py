"""子进程追踪 — 防止 Claude Code 子进程泄漏"""
import threading

_proc_lock = threading.Lock()
MAX_PROCS = 8
_proc_registry = []  # list of subprocess.Popen


def track_proc(proc):
    with _proc_lock:
        _proc_registry.append(proc)
        if len(_proc_registry) > MAX_PROCS:
            _proc_registry[:] = [p for p in _proc_registry if p.poll() is None]


def untrack_proc(proc):
    with _proc_lock:
        try:
            _proc_registry.remove(proc)
        except ValueError:
            pass


def kill_proc(proc):
    """强制终止子进程，不管理注册表（由调用方负责）"""
    try:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def cleanup_all_procs():
    """清理所有子进程 — 自己管理锁和注册表，避免死锁"""
    with _proc_lock:
        for p in list(_proc_registry):
            try:
                if p.poll() is None:
                    p.kill()
                    p.wait(timeout=5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        _proc_registry.clear()
