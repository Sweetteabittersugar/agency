"""多 Agent 共享记忆黑板 — 短期+长期+情景三层记忆"""

import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_EPISODIC_DIR_NAME = "episodic"
_MEMORY_DIR_NAME = "memory"


class ContextLayer:
    """多 Agent 共享记忆黑板

    三层记忆：
    - 短期（内存 dict，单次任务生命周期）
    - 长期（JSONL 持久化，跨会话积累）
    - 情景（操作日志，审计/调试用）
    """

    def __init__(self, task_id: str, project_root: Path):
        self.task_id = task_id
        self.project_root = Path(project_root)
        self._short_term: dict = {}
        self._versions: dict[str, int] = {}
        self._long_loaded = False
        self._long_cache: dict[str, str] = {}
        self._long_path = (
            self.project_root / "maestro" / _MEMORY_DIR_NAME / f"{self._proj_hash()}.jsonl"
        )
        self._ep_path = (
            self.project_root / "maestro" / "logs" / _EPISODIC_DIR_NAME / f"{task_id}.jsonl"
        )

    # ── 内部 ──

    def _proj_hash(self) -> str:
        h = hashlib.sha256(str(self.project_root.resolve()).encode()).hexdigest()[:12]
        return h

    def _ensure_dir(self, p: Path):
        p.parent.mkdir(parents=True, exist_ok=True)

    def _load_long(self):
        if self._long_loaded:
            return
        self._long_cache.clear()
        if self._long_path.exists():
            try:
                for line in self._long_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    k = rec.get("key", "")
                    if k:
                        self._long_cache[k] = rec.get("value", "")
            except Exception as e:
                log.warning("加载长期记忆失败: %s", e)
        self._long_loaded = True

    def _flush_long(self):
        self._ensure_dir(self._long_path)
        lines = [
            json.dumps({"key": k, "value": v, "ts": time.time()}, ensure_ascii=False)
            for k, v in self._long_cache.items()
        ]
        self._long_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ── 短期记忆 ──

    def get_short_term(self) -> dict:
        return dict(self._short_term)

    def set_short_term(self, key: str, value, expected_version: Optional[int] = None) -> bool:
        """写入短期记忆。提供 expected_version 时做乐观锁检查，冲突返回 False。"""
        if expected_version is not None:
            cur = self._versions.get(key, 0)
            if cur != expected_version:
                return False
        self._versions[key] = self._versions.get(key, 0) + 1
        self._short_term[key] = value
        return True

    def get_version(self, key: str) -> int:
        return self._versions.get(key, 0)

    # ── 长期记忆 ──

    def get_long_term(self, key: str) -> Optional[str]:
        self._load_long()
        return self._long_cache.get(key)

    def set_long_term(self, key: str, value: str):
        self._load_long()
        self._long_cache[key] = value
        self._flush_long()

    # ── 情景记忆 ──

    def log_episodic(
        self, agent: str, action: str, result: str, elapsed_ms: float = 0, tokens: int = 0
    ):
        entry = {
            "ts": time.time(),
            "agent": agent,
            "action": action,
            "result_summary": result[:500],
            "elapsed_ms": round(elapsed_ms, 1),
            "tokens": tokens,
        }
        self._ensure_dir(self._ep_path)
        with open(self._ep_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ── Agent 上下文 ──

    def get_context_for_agent(self, agent_name: str) -> str:
        """生成注入 prompt 的上下文摘要（按 Agent 角色过滤相关短期记忆）。"""
        st = self.get_short_term()
        parts: list[str] = []

        # 上游阶段产出（全量，让 Agent 自行筛选）
        stage_keys = ["research_result", "plan", "implemented_files", "review_findings"]
        for k in stage_keys:
            v = st.get(k)
            if v is not None:
                label = {
                    "research_result": "研究结果",
                    "plan": "实施方案",
                    "implemented_files": "已修改文件",
                    "review_findings": "审查发现",
                }.get(k, k)
                val_str = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
                parts.append(f"【{label}】\n{val_str[:2000]}")

        # 通用上下文
        for k, v in st.items():
            if k in stage_keys:
                continue
            val_str = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
            parts.append(f"【{k}】\n{val_str[:500]}")

        # 附加长期记忆中项目级知识
        long_keys = ["project_conventions", "known_pitfalls", "common_patterns"]
        for lk in long_keys:
            lv = self.get_long_term(lk)
            if lv:
                parts.append(f"【项目知识/{lk}】\n{lv[:1000]}")

        return "\n\n".join(parts) if parts else ""

    # ── 快照 ──

    def snapshot(self) -> dict:
        return {
            "task_id": self.task_id,
            "short_term": self.get_short_term(),
            "versions": dict(self._versions),
            "long_term_keys": list(self._long_cache.keys()),
            "episodic_path": str(self._ep_path),
        }

    def restore_snapshot(self, snap: dict) -> None:
        """从 snapshot() 输出恢复短期记忆和版本号（用于回滚）"""
        if not snap:
            return
        self._short_term = dict(snap.get("short_term", {}))
        self._versions = dict(snap.get("versions", {}))
