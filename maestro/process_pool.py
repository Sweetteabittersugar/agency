"""Claude 进程池 — stdin/stdout 长连接复用

设计思路：
- 每个 worker 是一个持久化的 claude 子进程，通过 stdin/stdout 管道通信
- 进程启动时注入完整环境（CLAUDE.md + rules + agent 定义）
- 任务以 JSON 格式通过 stdin 发送，stdout 读取 SSE 格式输出
- claude CLI 本身是一次性的（-p 模式），但我们在 Python 层做持久化：
  通过多轮交互保持进程存活，预加载环境减少重复开销
- 如果 claude CLI 不可用，返回 None，调用方回退到传统 subprocess.Popen

架构：
    ClaudeProcessPool
    ├── Worker 1: claude subprocess (stdin/stdout pipes)
    ├── Worker 2: claude subprocess (stdin/stdout pipes)
    └── Worker N: claude subprocess (stdin/stdout pipes)

协议：
    输入: {"task": "...", "agent": "...", "model": "...", "session_id": "...", ...}
    输出: SSE 行流，以 {"type":"done"} 或 {"type":"error"} 结束
"""

import json
import os
import shutil
import signal
import subprocess
import threading
import time
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# ── 检测 Claude CLI ──
_CLAUDE_BIN = shutil.which("claude")
if not _CLAUDE_BIN:
    for _p in [
        os.path.expanduser("~/AppData/Roaming/npm/claude.cmd"),
        os.path.expanduser("~/AppData/Roaming/npm/claude"),
    ]:
        if os.path.isfile(_p):
            _CLAUDE_BIN = _p
            break

# 默认最大并发数 = CPU 核数 - 1，至少为 1
_MAX_WORKERS = max(1, (os.cpu_count() or 2) - 1)


class WorkerState:
    """单个 worker 的状态"""
    IDLE = "idle"
    BUSY = "busy"
    DEAD = "dead"


class PoolWorker:
    """单个 claude 持久化进程包装"""

    def __init__(self, worker_id: int, project_root: str, isolated_config: str):
        self.worker_id = worker_id
        self.project_root = project_root
        self.isolated_config = isolated_config
        self.proc: subprocess.Popen | None = None
        self.state = WorkerState.IDLE
        self.last_active = time.time()
        self.restart_count = 0
        self.max_restarts = 2
        self._lock = threading.Lock()

    def start(self, env: dict | None = None) -> bool:
        """启动 claude 子进程，建立 stdin/stdout 管道"""
        with self._lock:
            if self.proc is not None and self.proc.poll() is None:
                return True  # 已经在运行

            try:
                iso_env = (env or os.environ).copy()
                iso_env["CLAUDE_CODE_CONFIG_DIR"] = self.isolated_config

                # 使用 claude -p 进入非交互模式，但通过 stdin 持续发送任务
                # 注意：claude CLI 的 -p 模式是单次执行，完成后进程退出
                # 我们用 "--resume" 模式配合 session 来模拟持久化：
                # 进程启动后等待 stdin 输入，执行完一个任务后等待下一个
                cmd = [
                    _CLAUDE_BIN,
                    "-p",
                    "",  # 初始空任务，等待 stdin 输入真正的任务
                    "--bare",
                    "--permission-mode", "auto",
                ]
                self.proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    cwd=self.project_root,
                    env=iso_env,
                )
                self.state = WorkerState.IDLE
                self.last_active = time.time()
                self.restart_count = 0
                log.info(f"POOL worker-{self.worker_id} started PID={self.proc.pid}")
                return True
            except Exception as e:
                log.error(f"POOL worker-{self.worker_id} start failed: {e}")
                self.proc = None
                self.state = WorkerState.DEAD
                return False

    def execute(self, task_payload: dict, timeout: float = 300) -> str | None:
        """通过 stdin 发送任务 JSON，从 stdout 读取 SSE 直到结束标记

        返回完整的输出文本，或 None 表示失败
        """
        with self._lock:
            if self.proc is None or self.proc.poll() is not None:
                log.warning(f"POOL worker-{self.worker_id} dead, attempting restart")
                if not self._restart():
                    return None

            self.state = WorkerState.BUSY
            self.last_active = time.time()

        try:
            # 发送任务 JSON 到 stdin
            task_json = json.dumps(task_payload, ensure_ascii=False) + "\n"
            try:
                self.proc.stdin.write(task_json)
                self.proc.stdin.flush()
            except (BrokenPipeError, OSError) as e:
                log.error(f"POOL worker-{self.worker_id} stdin write failed: {e}")
                self._mark_dead()
                if self._restart():
                    # 重试一次
                    try:
                        self.proc.stdin.write(task_json)
                        self.proc.stdin.flush()
                    except Exception:
                        return None
                else:
                    return None

            # 读取 stdout 直到结束标记
            output_lines = []
            deadline = time.time() + timeout
            done_marker = '{"type":"done"}'
            error_marker = '{"type":"error"}'

            while time.time() < deadline:
                # 检查进程是否存活
                if self.proc.poll() is not None:
                    log.warning(f"POOL worker-{self.worker_id} exited prematurely (rc={self.proc.returncode})")
                    self._mark_dead()
                    return None

                try:
                    line = self._read_line(timeout=1.0)
                except TimeoutError:
                    continue

                if line is None:
                    # 进程 stdout 关闭
                    break

                stripped = line.rstrip("\n\r")
                if not stripped:
                    continue

                output_lines.append(stripped)

                # 检查结束标记
                if stripped == done_marker or stripped == error_marker:
                    break

            else:
                # 超时
                log.warning(f"POOL worker-{self.worker_id} task timeout {timeout}s")
                self._kill()
                self._mark_dead()
                return None

            # 归还到空闲状态
            with self._lock:
                self.state = WorkerState.IDLE
                self.last_active = time.time()

            return "\n".join(output_lines)

        except Exception as e:
            log.error(f"POOL worker-{self.worker_id} execute failed: {e}")
            self._mark_dead()
            return None

    def health_check(self) -> bool:
        """心跳检测：进程是否存活且响应"""
        with self._lock:
            if self.proc is None:
                return False
            rc = self.proc.poll()
            if rc is not None:
                log.warning(f"POOL worker-{self.worker_id} died (rc={rc})")
                self._mark_dead()
                return False
            # 检查空闲超时
            idle_time = time.time() - self.last_active
            if idle_time > 30 and self.state == WorkerState.BUSY:
                log.warning(f"POOL worker-{self.worker_id} stuck for {idle_time:.0f}s, killing")
                self._kill()
                self._mark_dead()
                return False
            return True

    def is_idle(self) -> bool:
        return self.state == WorkerState.IDLE and self.proc is not None and self.proc.poll() is None

    def is_alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def idle_seconds(self) -> float:
        return time.time() - self.last_active

    def shutdown(self):
        """优雅关闭"""
        with self._lock:
            if self.proc:
                try:
                    # 发送关闭信号
                    try:
                        self.proc.stdin.write('{"type":"shutdown"}\n')
                        self.proc.stdin.flush()
                    except Exception:
                        pass
                    # 给进程时间优雅退出
                    try:
                        self.proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        pass
                except Exception:
                    pass
                self._kill()
                self.proc = None
                self.state = WorkerState.DEAD

    def _restart(self) -> bool:
        """自动重启（最多 max_restarts 次）"""
        if self.restart_count >= self.max_restarts:
            log.error(f"POOL worker-{self.worker_id} exceeded max restarts ({self.max_restarts})")
            return False
        self._kill()
        self.restart_count += 1
        log.info(f"POOL worker-{self.worker_id} restart attempt {self.restart_count}/{self.max_restarts}")
        time.sleep(0.5)  # 短暂等待后重启
        return self.start()

    def _kill(self):
        """强制终止"""
        if self.proc:
            try:
                if self.proc.poll() is None:
                    self.proc.kill()
                    self.proc.wait(timeout=5)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None

    def _mark_dead(self):
        self.state = WorkerState.DEAD

    def _read_line(self, timeout: float = 1.0) -> str | None:
        """从 stdout 读取一行，带超时"""
        if self.proc is None or self.proc.stdout is None:
            return None

        import select
        if hasattr(select, "select"):
            ready, _, _ = select.select([self.proc.stdout], [], [], timeout)
            if not ready:
                raise TimeoutError()
        else:
            # Windows fallback: 轮询
            deadline = time.time() + timeout
            while time.time() < deadline:
                import msvcrt
                if msvcrt.kbhit():
                    break
                time.sleep(0.05)
            else:
                raise TimeoutError()

        try:
            line = self.proc.stdout.readline()
            if not line:
                return None  # EOF
            return line
        except Exception:
            return None


class ClaudeProcessPool:
    """Claude 进程池 — 管理多个持久化 claude 子进程

    用法:
        pool = ClaudeProcessPool(max_workers=3)
        pool.initialize(project_root="/path/to/project")

        # 执行任务
        result = pool.execute({"task": "写个 hello world", "agent": "coder"})
        if result is None:
            # 池不可用，回退到传统 subprocess.Popen
            pass

        # 关闭
        pool.shutdown()
    """

    def __init__(self, max_workers: int | None = None):
        self.max_workers = max_workers or min(_MAX_WORKERS, 4)
        self.workers: list[PoolWorker] = []
        self.project_root: str = ""
        self.isolated_config: str = ""
        self._initialized = False
        self._lock = threading.Lock()
        self._shutdown_event = threading.Event()
        self._reaper_thread: threading.Thread | None = None
        self._pool_env: dict | None = None

    @property
    def available(self) -> bool:
        """池是否可用（CLI 已安装且已初始化）"""
        return _CLAUDE_BIN is not None and self._initialized

    def initialize(self, project_root: str, isolated_config: str = "", env: dict | None = None) -> bool:
        """初始化进程池，预启动所有 worker

        返回 True 表示可用，False 表示应回退到传统方式
        """
        if not _CLAUDE_BIN:
            log.warning("POOL Claude CLI not found, pool disabled")
            return False

        with self._lock:
            if self._initialized:
                return True

            self.project_root = project_root
            self.isolated_config = isolated_config or str(Path(project_root) / ".claude-isolated")
            self._pool_env = env or os.environ.copy()

            # 预启动所有 worker
            success_count = 0
            for i in range(self.max_workers):
                worker = PoolWorker(i, project_root, self.isolated_config)
                if worker.start(self._pool_env):
                    self.workers.append(worker)
                    success_count += 1

            if success_count == 0:
                log.warning("POOL all workers failed to start, pool disabled")
                return False

            self._initialized = True

            # 启动后台回收线程
            self._reaper_thread = threading.Thread(target=self._reaper_loop, daemon=True)
            self._reaper_thread.start()

            log.info(f"POOL initialized {success_count}/{self.max_workers} workers")
            return True

    def execute(self, task_payload: dict, timeout: float = 300) -> str | None:
        """执行任务：从池中获取空闲 worker，发送任务，返回输出

        返回 None 表示池不可用或执行失败，调用方应回退到传统方式
        """
        if not self.available:
            return None

        # 查找空闲 worker
        worker = self._acquire_worker()
        if worker is None:
            log.warning("POOL no idle worker available")
            return None

        try:
            result = worker.execute(task_payload, timeout=timeout)
            return result
        finally:
            # worker 已在 execute 内部归还到空闲状态
            pass

    def health_check(self) -> dict:
        """健康检查：返回所有 worker 状态"""
        status = {"available": self.available, "workers": []}
        with self._lock:
            for w in self.workers:
                alive = w.health_check()
                status["workers"].append({
                    "id": w.worker_id,
                    "state": w.state,
                    "alive": alive,
                    "idle_seconds": round(w.idle_seconds(), 1),
                    "restarts": w.restart_count,
                })
        return status

    def shutdown(self):
        """优雅关闭所有 worker 进程"""
        self._shutdown_event.set()
        with self._lock:
            for w in self.workers:
                w.shutdown()
            self.workers.clear()
            self._initialized = False
            log.info("POOL all workers shut down")

    def _acquire_worker(self) -> PoolWorker | None:
        """获取一个空闲 worker"""
        with self._lock:
            for w in self.workers:
                # 先做健康检查
                if not w.health_check():
                    # 尝试重启
                    if w.restart_count < w.max_restarts:
                        if w.start(self._pool_env):
                            continue
                    continue
                if w.is_idle():
                    return w
            return None

    def _reaper_loop(self):
        """后台线程：30s 间隔健康检查 + 10min 空闲回收"""
        while not self._shutdown_event.wait(timeout=30):
            with self._lock:
                for w in list(self.workers):
                    # 健康检查：30s 无响应则重启
                    if not w.health_check():
                        if w.restart_count < w.max_restarts:
                            log.info(f"POOL reaper restarting worker-{w.worker_id}")
                            w.start(self._pool_env)
                        else:
                            log.warning(f"POOL reaper removing dead worker-{w.worker_id}")
                            self.workers.remove(w)
                            # 补充新 worker
                            if len(self.workers) < self.max_workers:
                                new_id = max((w2.worker_id for w2 in self.workers), default=-1) + 1
                                new_worker = PoolWorker(new_id, self.project_root, self.isolated_config)
                                if new_worker.start(self._pool_env):
                                    self.workers.append(new_worker)

                    # 空闲 10min 自动回收
                    if w.is_idle() and w.idle_seconds() > 600:
                        if len(self.workers) > 1:  # 至少保留一个 worker
                            log.info(f"POOL reaper recycling idle worker-{w.worker_id} ({w.idle_seconds():.0f}s)")
                            w.shutdown()
                            self.workers.remove(w)


# ── 模块级单例 ──
_pool_instance: ClaudeProcessPool | None = None
_pool_lock = threading.Lock()


def get_pool(max_workers: int | None = None) -> ClaudeProcessPool | None:
    """获取（懒初始化）进程池单例"""
    global _pool_instance
    if _pool_instance is not None:
        return _pool_instance if _pool_instance.available else None

    with _pool_lock:
        if _pool_instance is not None:
            return _pool_instance if _pool_instance.available else None

        if not _CLAUDE_BIN:
            log.warning("Claude CLI not found, process pool disabled")
            return None

        _pool_instance = ClaudeProcessPool(max_workers=max_workers)
        return _pool_instance


def init_pool(project_root: str, isolated_config: str = "", max_workers: int | None = None,
              env: dict | None = None) -> ClaudeProcessPool | None:
    """显式初始化进程池（在应用启动时调用）"""
    pool = get_pool(max_workers=max_workers)
    if pool is None:
        return None
    ok = pool.initialize(project_root, isolated_config, env)
    return pool if ok else None


def shutdown_pool():
    """关闭进程池单例"""
    global _pool_instance
    if _pool_instance:
        _pool_instance.shutdown()
        _pool_instance = None
