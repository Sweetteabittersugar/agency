"""持久化 Claude 会话 — stream-json 双向管道，同进程多轮复用"""

import subprocess
import json
import time
import logging
import threading
from pathlib import Path

log = logging.getLogger(__name__)

CLAUDE_BIN = None
for _p in [
    r"C:\Users\lenovo\AppData\Roaming\npm\claude.CMD",
    r"C:\Users\lenovo\AppData\Roaming\npm\claude",
]:
    if Path(_p).exists():
        CLAUDE_BIN = _p
        break
if not CLAUDE_BIN:
    import shutil

    CLAUDE_BIN = shutil.which("claude") or "claude"

_sessions: dict[str, "ClaudeSession"] = {}
_lock = threading.Lock()
MAX_SESSIONS = 4


class ClaudeSession:
    """单个持久化 Claude 进程，stdin/stdout 双向 stream-json"""

    def __init__(self, session_id: str, project_root: str, env: dict):
        self.session_id = session_id
        self.project_root = project_root
        self.env = env
        self.proc: subprocess.Popen | None = None
        self.busy = False
        self._created = time.time()
        self._last_used = time.time()
        self._total_turns = 0
        self._transcript: list[dict] = []  # 对话记录 [{"role":"user","content":...}, ...]
        # Token 累计追踪——按面板独立统计，供仪表盘上下文面板展示
        self._total_in_tokens = 0
        self._total_out_tokens = 0
        self._total_cache_read = 0
        self._total_cost = 0.0
        self._detected_model = ""  # 从 Claude result 事件读取的真实模型名

    def spawn(self) -> bool:
        """启动 Claude 进程"""
        cmd = [
            CLAUDE_BIN,
            "-p",
            "--input-format",
            "stream-json",
            "--output-format",
            "stream-json",
            "--verbose",
            "--permission-mode",
            "auto",
        ]
        try:
            self.proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,  # 行缓冲，避免 OS 默认 4-8K 缓冲增加响应延迟
                cwd=str(self.project_root),
                env=self.env,
            )
            log.info(f"ClaudeSession spawned pid={self.proc.pid} sid={self.session_id}")
            return True
        except Exception as e:
            log.warning(f"ClaudeSession spawn failed: {e}")
            return False

    def send_and_read(self, task: str, timeout: float = 300) -> list[dict]:
        """发送任务，返回 SSE 事件列表。调用方负责流式输出。

        timeout: 单次请求最大等待秒数（默认5分钟），超时后强制杀进程"""
        self.busy = True
        self._last_used = time.time()
        self._total_turns += 1
        events = []

        # 记录用户消息
        self._transcript.append({"role": "user", "content": task})

        # 发送 stream-json 格式的用户消息
        payload = (
            json.dumps(
                {
                    "type": "user",
                    "message": {"role": "user", "content": task},
                },
                ensure_ascii=False,
            )
            + "\n"
        )

        try:
            self.proc.stdin.write(payload.encode("utf-8"))
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            log.warning(f"ClaudeSession stdin write failed: {e}")
            self.busy = False
            return [{"error": "进程已断开，请重试"}]

        # 超时保护：readline 阻塞时，后台定时器杀进程 → readline 返回 EOF
        timed_out = [False]

        def _on_timeout():
            timed_out[0] = True
            try:
                self.proc.kill()
            except Exception:
                pass

        timer = threading.Timer(timeout, _on_timeout)
        timer.daemon = True
        timer.start()

        try:
            # 读取响应直到 result 事件
            assistant_text = ""
            for line in iter(self.proc.stdout.readline, b""):
                if timed_out[0]:
                    events.append({"error": f"请求超时（{int(timeout)}秒无响应），请重试"})
                    break

                stripped = line.decode("utf-8", errors="replace").strip()
                if not stripped:
                    continue
                try:
                    evt = json.loads(stripped)
                except json.JSONDecodeError:
                    continue

                evt_type = evt.get("type", "")

                if evt_type == "assistant":
                    for block in evt.get("message", {}).get("content", []):
                        if block.get("type") == "text":
                            assistant_text += block["text"]
                            events.append({"content": block["text"]})

                elif evt_type == "result":
                    usage = evt.get("usage", {})
                    in_tok = usage.get("input_tokens", 0)
                    out_tok = usage.get("output_tokens", 0)
                    cache_read = usage.get("cache_read_input_tokens", 0)
                    cost = round(evt.get("total_cost_usd", 0), 6)
                    model = evt.get("model", "")
                    # accumulate token counters for per-panel tracking in dashboard
                    self._total_in_tokens += in_tok
                    self._total_out_tokens += out_tok
                    self._total_cache_read += cache_read
                    self._total_cost += cost
                    if model:
                        # 2026-06：标准化模型名——Claude Code 可能报简称如 "sonnet"，
                        # 统一到 PRICING 表键名如 "claude-sonnet-4-6"，避免聚合统计出错
                        from maestro.models import normalize_model_name
                        self._detected_model = normalize_model_name(model)
                    events.append(
                        {
                            "done": {
                                "elapsed": round(evt.get("duration_ms", 0) / 1000, 1),
                                "cost": cost,
                                "in_tokens": in_tok,
                                "out_tokens": out_tok,
                                "cache_read": cache_read,
                                "session_id": evt.get("session_id", ""),
                                "model": model,
                                "total_in": self._total_in_tokens,
                                "total_out": self._total_out_tokens,
                                "total_cost": round(self._total_cost, 6),
                            }
                        }
                    )
                    break  # end of turn, process keeps waiting for next message


                elif evt_type == "system":
                    pass  # 忽略系统事件

            self._transcript.append({"role": "assistant", "content": assistant_text})

        finally:
            timer.cancel()

        self.busy = False
        return events

    def extract_memories(self) -> list[str]:
        """向 Claude 发送提炼提示，返回记忆文本块列表（解析由 memory_engine 负责）"""
        if not self.is_alive() or len(self._transcript) < 2:
            return []

        # 只取最近 20 轮避免 token 浪费
        recent = self._transcript[-40:]
        conversation_text = "\n".join(
            f"[{'用户' if t['role'] == 'user' else '助手'}]: {t['content'][:500]}" for t in recent
        )

        from maestro.memory_engine import MEMORY_EXTRACT_PROMPT

        prompt = f"{conversation_text}\n\n{MEMORY_EXTRACT_PROMPT}"
        events = self.send_and_read(prompt)
        response = "".join(evt["content"] for evt in events if "content" in evt)

        from maestro.memory_engine import parse_memory_blocks

        return parse_memory_blocks(response)

    def compaction_status(self) -> dict:
        """按模型窗口容量+累计用量判断是否需要压缩。
        70% 警告 / 85% 强制压缩，阈值在 models.py 统一定义。"""
        from maestro.models import check_compaction
        model = self._detected_model or "deepseek-v4-flash"
        return check_compaction(model, self._total_in_tokens)

    def is_alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def kill(self):
        if self.proc:
            try:
                self.proc.stdin.close()
                self.proc.terminate()
            except Exception:
                pass
            try:
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()
            self.proc = None


def get_or_create(session_id: str, project_root: str, env: dict) -> ClaudeSession | None:
    """获取或创建持久化会话"""
    with _lock:
        # 清理已死会话
        dead = [sid for sid, s in _sessions.items() if not s.is_alive()]
        for sid in dead:
            log.warning(f"清理已死会话: {sid[:8]}...")
            _sessions[sid].kill()
            del _sessions[sid]

        if session_id and session_id in _sessions:
            s = _sessions[session_id]
            if s.is_alive() and not s.busy:
                log.info(f"复用已有会话: {session_id[:8]}... (第{s._total_turns + 1}轮)")
                return s
            if s.is_alive() and s.busy:
                log.warning(f"会话忙碌，拒绝并发请求: {session_id[:8]}...")
                return None  # 调用方应返回"请等待上一请求完成"
            # 进程已死，重建
            log.warning(f"会话进程已死，重建: {session_id[:8]}...")
            del _sessions[session_id]

        # 限制最大会话数
        if len(_sessions) >= MAX_SESSIONS:
            oldest = min(_sessions.keys(), key=lambda k: _sessions[k]._last_used)
            log.warning(f"超过最大会话数，淘汰最旧: {oldest[:8]}...")
            _sessions[oldest].kill()
            del _sessions[oldest]

        log.info(f"创建新会话: {session_id[:8]}... (当前{len(_sessions)}个)")
        s = ClaudeSession(session_id, project_root, env)
        if s.spawn():
            _sessions[session_id] = s
            return s
        log.error(f"Claude 进程启动失败: {session_id[:8]}...")
        return None


def terminate(session_id: str) -> bool:
    """关闭指定会话进程"""
    with _lock:
        s = _sessions.pop(session_id, None)
        if s:
            log.info(f"终止会话: {session_id[:8]}...")
            s.kill()
            return True
        return False


def cleanup_all():
    """关闭所有会话"""
    with _lock:
        for s in list(_sessions.values()):
            s.kill()
        _sessions.clear()


def list_sessions() -> list[dict]:
    """列出所有活跃会话——含 token 累计和压缩状态"""
    with _lock:
        return [
            {
                "session_id": sid[:8] + "...",
                "turns": s._total_turns,
                "alive": s.is_alive(),
                "age_seconds": round(time.time() - s._created, 1),
                "model": s._detected_model or "unknown",
                "total_tokens": s._total_in_tokens + s._total_out_tokens,
                "total_cost": round(s._total_cost, 6),
                "compaction": s.compaction_status(),
            }
            for sid, s in _sessions.items()
        ]
