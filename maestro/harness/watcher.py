"""
Harness Watcher — SSE 事件广播 + JSONL tail 守护线程
所有 Harness 前端共享一个 /api/harness/stream SSE 长连接，
后端通过此模块的 broadcast() 推送事件到所有客户端。
"""
import json, threading, time, os
from pathlib import Path
from queue import Queue, Empty


class HarnessBus:
    """单例事件总线：生产者 push，消费者 listen"""

    def __init__(self):
        self._queues: list[Queue] = []
        self._lock = threading.Lock()
        self._event_log: list[dict] = []  # 最近 500 条事件
        self._max_log = 500

    def broadcast(self, event_type: str, data: dict):
        """推送事件到所有连接的 SSE 客户端"""
        payload = json.dumps({"type": event_type, "data": data, "ts": time.time()},
                             ensure_ascii=False)
        # 记入滚动日志
        self._event_log.append({"type": event_type, "data": data, "ts": time.time()})
        if len(self._event_log) > self._max_log:
            self._event_log = self._event_log[-self._max_log:]

        with self._lock:
            dead = []
            for q in self._queues:
                try:
                    q.put_nowait(payload)
                except Exception:
                    dead.append(q)
            for q in dead:
                self._queues.remove(q)

    def listen(self):
        """返回一个 Queue，调用方从中 get() 事件"""
        q = Queue(maxsize=200)
        with self._lock:
            self._queues.append(q)
        return q

    def unlisten(self, q):
        with self._lock:
            if q in self._queues:
                self._queues.remove(q)

    def recent_events(self, event_type: str = None, limit: int = 50):
        """查询最近事件"""
        if event_type:
            filtered = [e for e in self._event_log if e["type"] == event_type]
            return filtered[-limit:]
        return self._event_log[-limit:]


# 全局单例
bus = HarnessBus()
