"""Coordinator — 任务协调器：失败重试/回滚/死锁检测/升级策略"""

import json
import time
import logging
from pathlib import Path
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)

CHECKPOINTS = ["plan_approved", "implement_started", "implement_done", "review_passed"]


class Coordinator:
    """任务协调器 — 失败重试/回滚/死锁检测/升级策略"""

    def __init__(self, logs_dir: Optional[Path] = None):
        self.logs_dir = Path(logs_dir) if logs_dir else Path(__file__).parent / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._escalations_file = self.logs_dir / "escalations.jsonl"
        self._episodic_file = self.logs_dir / "episodic.jsonl"
        self._checkpoints: dict[str, dict] = {}

    # ── a) 智能重试（指数退避）──
    def retry_with_backoff(
        self, fn: Callable, max_retries: int = 3, base_delay: float = 2.0
    ) -> tuple[bool, Any]:
        delays = [base_delay, base_delay * 2.5, base_delay * 5.0]
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                result = fn(attempt=attempt)
                self._log_episodic("retry", {"attempt": attempt, "status": "success"})
                return True, result
            except Exception as e:
                last_error = e
                self._log_episodic(
                    "retry", {"attempt": attempt, "status": "failed", "error": str(e)[:200]}
                )
                if attempt < max_retries:
                    wait = delays[min(attempt, len(delays) - 1)]
                    log.warning("重试 %d/%d，等待 %.1fs: %s", attempt + 1, max_retries, wait, e)
                    time.sleep(wait)
        return False, last_error

    # ── b) 回滚机制 ──
    def save_checkpoint(self, task_id: str, checkpoint_name: str, context_snapshot: dict = None):
        if checkpoint_name not in CHECKPOINTS:
            log.warning("未知 checkpoint: %s (已知: %s)", checkpoint_name, CHECKPOINTS)
        self._checkpoints[task_id] = {
            "name": checkpoint_name,
            "snapshot": context_snapshot or {},
            "timestamp": time.time(),
        }

    def rollback_to_checkpoint(
        self, task_id: str, checkpoint_name: str, context_layer=None
    ) -> Optional[dict]:
        cp = self._checkpoints.get(task_id)
        if not cp:
            log.warning("无 checkpoint: task=%s", task_id)
            return None
        if cp["name"] != checkpoint_name:
            log.warning(
                "checkpoint 不匹配: task=%s want=%s got=%s", task_id, checkpoint_name, cp["name"]
            )
            return None
        if context_layer and cp["snapshot"]:
            try:
                context_layer.restore_snapshot(cp["snapshot"])
            except Exception as e:
                log.warning("ContextLayer 恢复失败: %s", e)
        return cp["snapshot"]

    # ── c) 死锁检测 ──
    def detect_deadlock(self, agent_states: dict) -> bool:
        """
        agent_states: {agent_name: {"waiting_for": agent|None, "last_output_ts": float}}
        """
        now = time.time()
        # 超时停滞：超过 300 秒无输出
        for name, state in agent_states.items():
            last_ts = state.get("last_output_ts", 0)
            if last_ts > 0 and (now - last_ts) > 300:
                log.warning("死锁检测: %s 停滞 %.0fs", name, now - last_ts)
                return True
        # 循环等待：构建等待图，检测环
        wait_graph = {}
        for name, state in agent_states.items():
            target = state.get("waiting_for")
            if target and target in agent_states:
                wait_graph[name] = target
        visited = set()

        def _has_cycle(node: str, path: set) -> bool:
            if node in path:
                return True
            if node in visited:
                return False
            visited.add(node)
            nxt = wait_graph.get(node)
            return _has_cycle(nxt, path | {node}) if nxt else False

        for node in wait_graph:
            if _has_cycle(node, set()):
                log.warning("死锁检测: 循环等待 %s", node)
                return True
        return False

    # ── d) 升级策略 ──
    def escalate(self, task_id: str, reason: str, severity: str) -> dict:
        """
        severity: warn(记录继续) | block(暂停确认) | abort(终止回滚)
        """
        if severity not in ("warn", "block", "abort"):
            severity = "warn"
        entry = {
            "task_id": task_id,
            "reason": reason,
            "severity": severity,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            with open(self._escalations_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            log.error("升级记录写入失败: %s", e)
        log.info("升级: task=%s severity=%s reason=%s", task_id, severity, reason)
        return entry

    # ── 内部日志 ──
    def _log_episodic(self, event_type: str, data: dict):
        entry = {"type": event_type, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), **data}
        try:
            with open(self._episodic_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as _e:
            # log failed writes instead of silently dropping episodic events
            log.debug(f"情景日志写入失败: {_e}")
