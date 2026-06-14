"""终端 PTY 管理器 — 每个面板一个独立伪终端进程

为何用 PTY 而非管道：PTY 提供完整的终端模拟（支持颜色、信号、
交互式命令），子进程以为是真实终端，兼容性最好。"""

import os
import pty
import logging
import threading

log = logging.getLogger(__name__)


class TerminalSession:
    """单个终端会话，包装一个 PTY 子进程"""

    def __init__(self, sid, cwd):
        self.sid = sid
        self.cwd = cwd
        self.fd = None  # PTY master fd
        self.pid = None
        self.alive = False
        self._spawn()

    def _spawn(self):
        """启动 PTY 子进程。不可移除——终端所有 I/O 基于此 fd"""
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            # 子进程：启动 bash
            os.chdir(self.cwd)
            os.environ["TERM"] = "xterm-256color"
            os.execvp("bash", ["bash", "--norc"])
        # 父进程：设置非阻塞读
        import fcntl

        fl = fcntl.fcntl(self.fd, fcntl.F_GETFL)
        fcntl.fcntl(self.fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        self.alive = True
        log.info(f"TERM spawn: sid={self.sid} pid={self.pid}")

    def read(self, size=4096):
        """从 PTY 读取输出，非阻塞"""
        try:
            return os.read(self.fd, size)
        except (OSError, BlockingIOError):
            return b""

    def write(self, data):
        """向 PTY 写入输入"""
        if self.alive:
            os.write(self.fd, data.encode() if isinstance(data, str) else data)

    def resize(self, rows, cols):
        """调整终端窗口大小"""
        if self.alive:
            import fcntl
            import termios
            import struct

            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsize)

    def kill(self):
        if self.pid:
            try:
                os.kill(self.pid, 9)
            except Exception:
                pass
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
