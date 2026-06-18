#!/usr/bin/env python3
"""
Codex CLI 持久会话管理 — 对齐 ClaudeSession 接口。

Codex 与 CC 的不同：
  - 非持久进程：每轮一个 `codex exec`，通过 `resume <UUID>` 接续
  - NDJSON 事件流：thread.started → turn.started → item.* → turn.completed
  - 无 total_cost_usd：费用由 token × pricing.py 计算（与 CC 一致）
  - stdin 陷阱：裸调 `codex exec` 会在子进程中卡死，必须 `</dev/null`
"""
from __future__ import annotations

import json
import logging
import subprocess
import threading
import time
from pathlib import Path

log = logging.getLogger(__name__)

# 全局会话注册表
_sessions: dict[str, "CodexSession"] = {}


class CodexSession:
    """Codex CLI 会话——每轮新进程，靠 UUID 接续上下文。"""

    @classmethod
    def get(cls, session_id: str) -> "CodexSession | None":
        return _sessions.get(session_id)

    @property
    def in_tokens(self) -> int:
        return self._total_in_tokens

    @property
    def out_tokens(self) -> int:
        return self._total_out_tokens

    @property
    def cost(self) -> float:
        return self._total_cost

    @property
    def transcript(self) -> list:
        return list(self._transcript)

    @property
    def model(self) -> str:
        return self._detected_model or "unknown"

    def __init__(self, session_id: str, project_root: str, env: dict):
        self.session_id = session_id
        self.project_root = project_root
        self.env = env
        self.busy = False
        self._created = time.time()
        self._last_used = time.time()
        self._total_turns = 0
        self._transcript: list[dict] = []
        self._total_in_tokens = 0
        self._total_out_tokens = 0
        self._total_cache_read = 0
        self._total_cost = 0.0
        self._detected_model = ""
        self._codex_uuid: str | None = None  # Codex 内部会话 UUID，用于 resume
        self._proc: subprocess.Popen | None = None

        _sessions[session_id] = self

    def is_alive(self) -> bool:
        return True  # Codex 无持久进程，总可通过 resume 接续

    def stop(self):
        self.busy = False
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
            except Exception:
                pass

    # ── 核心接口：与 ClaudeSession.send_and_read 签名一致 ──

    def send_and_read(self, task: str, timeout: float = 600) -> list[dict]:
        """发送任务，阻塞读取 Codex NDJSON 输出，返回标准化事件列表。"""
        self.busy = True
        self._last_used = time.time()
        self._total_turns += 1

        timer = threading.Timer(timeout, self._kill_proc)
        timer.start()

        try:
            events = self._run_codex(task)
        finally:
            timer.cancel()
            self.busy = False

        return events

    # ── 内部实现 ──

    def _run_codex(self, task: str) -> list[dict]:
        """启动 Codex 子进程，解析 NDJSON 事件。"""
        # 构建命令：首轮用 codex exec，后续用 resume
        if self._codex_uuid is None:
            cmd = ["codex", "exec", task]
        else:
            # resume 模式：通过 stdin 传入新任务
            cmd = ["codex", "exec", "resume", self._codex_uuid]

        try:
            self._proc = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                env=self.env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )

            if self._codex_uuid is not None:
                # 通过 stdin 传入新任务文本
                try:
                    self._proc.stdin.write(task + "\n")
                    self._proc.stdin.close()
                except Exception:
                    pass

            return self._parse_events()
        except FileNotFoundError:
            log.error("codex 命令未找到，请先安装: npm install -g @openai/codex")
            return [{"error": "codex CLI 未安装"}]
        except Exception as e:
            log.error(f"Codex 进程异常: {e}")
            return [{"error": str(e)}]

    def _parse_events(self) -> list[dict]:
        """解析 Codex NDJSON stdout，映射到 Agency 标准事件格式。"""
        events: list[dict] = []
        assistant_text = ""
        done_data: dict = {}

        if self._proc is None or self._proc.stdout is None:
            return [{"error": "Codex 进程未启动"}]

        for line in self._proc.stdout:
            line = line.strip()
            if not line:
                continue

            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue

            evt_type = evt.get("type", "")

            # ── 会话初始化 ──
            if evt_type == "thread.started":
                uid = evt.get("thread_id") or evt.get("session_id") or ""
                if uid and self._codex_uuid is None:
                    self._codex_uuid = uid

            # ── 文本内容流 ──
            elif evt_type in ("item.updated", "item.completed"):
                item = evt.get("item", {})
                if item.get("type") == "agent_message":
                    delta = ""
                    # Codex 可能用 delta 或 content 字段
                    if "delta" in item:
                        delta = item["delta"]
                    elif "content" in item:
                        content = item["content"]
                        if isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    delta += block.get("text", "")
                        elif isinstance(content, str):
                            delta = content

                    if delta:
                        assistant_text += delta
                        # 去重：只在有增量时才加事件
                        events.append({"content": delta})

            # ── 轮次完成（含 token 统计） ──
            elif evt_type == "turn.completed":
                usage = evt.get("usage", {})
                in_tok = usage.get("input_tokens", 0)
                out_tok = usage.get("output_tokens", 0)
                cache_read = usage.get("cached_input_tokens", 0)

                # 模型名——可能来自不同路径
                model = evt.get("model", "")
                if not model:
                    # 从 thread.started 或其他事件获取
                    model = self._detected_model or "gpt-5"

                # 标准化模型名
                from maestro.pricing import normalize_model_name as _norm
                model_norm = _norm(model)
                self._detected_model = model_norm

                # 费用计算——Codex 不报 total_cost_usd，自己 token × 定价表
                from maestro.pricing import estimate_cost as _estimate
                cost, _saved, _hit = _estimate(
                    model_norm, in_tok, out_tok, cache_read=cache_read
                )

                # 累计
                self._total_in_tokens += in_tok
                self._total_out_tokens += out_tok
                self._total_cache_read += cache_read
                self._total_cost += cost

                done_data = {
                    "elapsed": round(evt.get("duration_ms", 0) / 1000, 1),
                    "cost": cost,
                    "in_tokens": in_tok,
                    "out_tokens": out_tok,
                    "cache_read": cache_read,
                    "session_id": self.session_id,
                    "model": model_norm,
                    "total_in": self._total_in_tokens,
                    "total_out": self._total_out_tokens,
                    "total_cost": round(self._total_cost, 6),
                }

            # ── 错误 ──
            elif evt_type in ("turn.failed", "error"):
                err_msg = evt.get("message") or evt.get("error", "Codex 执行失败")
                events.append({"error": str(err_msg)})
                break

            # ── token_count（补充 token 快照） ──
            elif evt_type == "token_count":
                # 可用于实时 token 面板展示
                pass

        # 等待进程结束
        try:
            self._proc.wait(timeout=10)
        except Exception:
            self._proc.terminate()

        # 检查 stderr 是否有错误信息
        stderr_output = ""
        if self._proc.stderr:
            try:
                stderr_output = self._proc.stderr.read()
            except Exception:
                pass

        if self._proc.returncode != 0 and not done_data:
            err = stderr_output.strip() or f"Codex 进程异常退出 (code={self._proc.returncode})"
            log.warning(f"Codex session={self.session_id}: {err}")
            events.append({"error": err})
            return events

        # 追加 done 事件
        if done_data:
            events.append({"done": done_data})

        self._transcript.append({"role": "user", "content": "(task)"})
        self._transcript.append({"role": "assistant", "content": assistant_text})

        return events

    def _kill_proc(self):
        """超时回调——强制终止进程。"""
        if self._proc and self._proc.poll() is None:
            log.warning(f"Codex session={self.session_id} 超时，强制终止")
            try:
                self._proc.kill()
            except Exception:
                pass


def stop_all():
    """停止所有 CodexSession（服务关闭时调用）。"""
    for sid, s in list(_sessions.items()):
        try:
            s.stop()
        except Exception:
            pass
    _sessions.clear()
