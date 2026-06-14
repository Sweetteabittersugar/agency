"""终端管理器 — 每个面板一个独立伪终端进程

跨平台适配：Unix 用 pty（完整终端模拟），Windows 用 subprocess（管道模式，
无颜色但可交互）。不可移除——面板💻按钮依赖此模块。"""

import os
import sys
import logging
import threading

log = logging.getLogger(__name__)

# 平台检测
IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import subprocess
    import msvcrt
else:
    import pty
    import fcntl
    import termios
    import struct


class TerminalSession:
    """单个终端会话，封装一个子进程。平台自动适配"""

    def __init__(self, sid, cwd):
        self.sid = sid
        self.cwd = cwd
        self.fd = None  # 主端 fd（Unix）或 stdout 管道（Windows）
        self.pid = None
        self.alive = False
        self._stdin = None  # Windows: stdin 写入管道
        self._spawn()

    def _spawn(self):
        """启动子进程。不可移除——终端所有 I/O 基于此"""
        if IS_WINDOWS:
            self._spawn_windows()
        else:
            self._spawn_unix()

    def _spawn_windows(self):
        """Windows: subprocess + 管道模式。不支持颜色，但可交互"""
        self._proc = subprocess.Popen(
            "cmd.exe",
            cwd=self.cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )
        self.pid = self._proc.pid
        # 设置 stdout 为非阻塞
        try:
            handle = msvcrt.get_osfhandle(self._proc.stdout.fileno())
            import ctypes
            DWORD = ctypes.c_ulong
            kernel32 = ctypes.windll.kernel32
            # 设置管道为非阻塞：设置超时为0
            PIPE_NOWAIT = 0x00000001
            kernel32.SetNamedPipeHandleState(
                ctypes.c_void_p(handle),
                ctypes.byref(DWORD(PIPE_NOWAIT)),
                None, None
            )
        except Exception:
            pass  # 非阻塞设置失败也可继续
        self.alive = True
        log.info(f"TERM spawn (Windows): sid={self.sid} pid={self.pid}")

    def _spawn_unix(self):
        """Unix: pty.fork 完整终端模拟"""
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.chdir(self.cwd)
            os.environ["TERM"] = "xterm-256color"
            os.execvp("bash", ["bash", "--norc"])
        fl = fcntl.fcntl(self.fd, fcntl.F_GETFL)
        fcntl.fcntl(self.fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        self.alive = True
        log.info(f"TERM spawn (Unix): sid={self.sid} pid={self.pid}")

    def read(self, size=4096):
        """非阻塞读取子进程输出"""
        if IS_WINDOWS:
            if not self.alive or self._proc.poll() is not None:
                self.alive = False
                return b""
            try:
                # Windows: 用 peek 检查是否有数据，避免阻塞
                import ctypes
                kernel32 = ctypes.windll.kernel32
                handle = msvcrt.get_osfhandle(self._proc.stdout.fileno())
                bytes_avail = ctypes.c_ulong(0)
                if kernel32.PeekNamedPipe(
                    ctypes.c_void_p(handle), None, 0, None,
                    ctypes.byref(bytes_avail), None
                ) and bytes_avail.value > 0:
                    return self._proc.stdout.read(min(size, bytes_avail.value))
                return b""
            except Exception:
                return b""
        else:
            try:
                return os.read(self.fd, size)
            except (OSError, BlockingIOError):
                return b""

    def write(self, data):
        """写入子进程 stdin"""
        if IS_WINDOWS:
            if self.alive and self._proc.poll() is None:
                try:
                    self._proc.stdin.write(
                        data.encode() if isinstance(data, str) else data
                    )
                    self._proc.stdin.flush()
                except Exception:
                    self.alive = False
        else:
            if self.alive:
                os.write(self.fd, data.encode() if isinstance(data, str) else data)

    def resize(self, rows, cols):
        """调整终端窗口大小（仅 Unix 支持）"""
        if not IS_WINDOWS and self.alive:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsize)

    def kill(self):
        if self.pid:
            try:
                os.kill(self.pid, 9)
            except Exception:
                pass
        if IS_WINDOWS:
            try:
                self._proc.terminate()
            except Exception:
                pass
        else:
            if self.fd:
                try:
                    os.close(self.fd)
                except Exception:
                    pass
        self.alive = False


# 全局终端注册表（最多 8 个，配合面板上限）
_terminals: dict[str, TerminalSession] = {}


def get_or_create_terminal(sid, cwd):
    if sid in _terminals and _terminals[sid].alive:
        return _terminals[sid]
    ts = TerminalSession(sid, cwd)
    _terminals[sid] = ts
    return ts


def kill_terminal(sid):
    if sid in _terminals:
        _terminals[sid].kill()
        del _terminals[sid]
