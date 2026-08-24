"""Durable, local execution ledger for resumable Agency runs.

The ledger stores only Agency-owned runtime facts.  A run is bound to the
digest of the requested task and to one authorized project directory; it has
no dependency on a workspace-specific task system or external control plane.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any


class LedgerError(RuntimeError):
    """Base error for durable runner state failures."""


class RunResumeRejected(LedgerError):
    """The supplied run id is not compatible with this request."""


class RunnerClaimConflict(LedgerError):
    """A live runner already owns the run or the supplied fence is stale."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validate_run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", run_id
    ):
        raise LedgerError("run_id must be 1-64 ASCII letters, digits, underscores, or hyphens")
    return run_id


def task_digest(task: str) -> str:
    return hashlib.sha256(task.encode("utf-8")).hexdigest()


class RunLedger:
    """SQLite WAL ledger with append-only events and fenced runner claims."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    task_digest TEXT NOT NULL,
                    project_path TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    runner_required INTEGER NOT NULL CHECK (runner_required IN (0, 1)),
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    run_id TEXT NOT NULL REFERENCES runs(run_id),
                    seq INTEGER NOT NULL,
                    event_id TEXT NOT NULL UNIQUE,
                    event_type TEXT NOT NULL,
                    idempotency_key TEXT,
                    payload_json TEXT NOT NULL,
                    payload_digest TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (run_id, seq),
                    UNIQUE (run_id, event_type, idempotency_key)
                );

                CREATE TABLE IF NOT EXISTS runner_claims (
                    run_id TEXT PRIMARY KEY REFERENCES runs(run_id),
                    owner TEXT NOT NULL,
                    fence_id TEXT NOT NULL,
                    claimed_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS snapshots (
                    run_id TEXT PRIMARY KEY REFERENCES runs(run_id),
                    last_seq INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    state_digest TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TRIGGER IF NOT EXISTS events_reject_update
                BEFORE UPDATE ON events
                BEGIN
                    SELECT RAISE(ABORT, 'events are append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS events_reject_delete
                BEFORE DELETE ON events
                BEGIN
                    SELECT RAISE(ABORT, 'events are append-only');
                END;
                """
            )

    @staticmethod
    def _require_runner(
        connection: sqlite3.Connection,
        run_id: str,
        runner_fence: str | None,
        *,
        now: float,
    ) -> None:
        run = connection.execute(
            "SELECT runner_required FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if run is None:
            raise LedgerError(f"unknown run: {run_id}")
        if not bool(run["runner_required"]):
            return
        claim = connection.execute(
            "SELECT fence_id, expires_at FROM runner_claims WHERE run_id = ?", (run_id,)
        ).fetchone()
        if (
            claim is None
            or not isinstance(runner_fence, str)
            or not secrets.compare_digest(str(claim["fence_id"]), runner_fence)
            or float(claim["expires_at"]) <= now
        ):
            raise RunnerClaimConflict("runner fence is missing, stale, or expired")

    def _append_event(
        self,
        connection: sqlite3.Connection,
        run_id: str,
        event_type: str,
        payload: dict[str, Any],
        *,
        event_id: str | None = None,
        idempotency_key: str | None = None,
        runner_fence: str | None = None,
        now: float | None = None,
    ) -> dict[str, Any]:
        if not event_type or not isinstance(payload, dict):
            raise LedgerError("event type and mapping payload are required")
        validate_run_id(run_id)
        now = time.time() if now is None else now
        self._require_runner(connection, run_id, runner_fence, now=now)
        event_id = event_id or uuid.uuid4().hex
        payload_json = _canonical_json(payload)
        payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

        duplicate = connection.execute(
            """SELECT seq, event_id, payload_digest, payload_json
               FROM events
               WHERE run_id = ? AND event_type = ? AND idempotency_key = ?""",
            (run_id, event_type, idempotency_key),
        ).fetchone() if idempotency_key is not None else None
        if duplicate is not None:
            if duplicate["payload_digest"] != payload_hash or duplicate["payload_json"] != payload_json:
                raise LedgerError("idempotency key was reused with different content")
            return {
                "run_id": run_id,
                "seq": int(duplicate["seq"]),
                "event_id": str(duplicate["event_id"]),
                "event_type": event_type,
                "payload": payload,
            }

        event_duplicate = connection.execute(
            "SELECT payload_digest, payload_json FROM events WHERE event_id = ?", (event_id,)
        ).fetchone()
        if event_duplicate is not None:
            if (
                event_duplicate["payload_digest"] != payload_hash
                or event_duplicate["payload_json"] != payload_json
            ):
                raise LedgerError("event id was reused with different content")
            raise LedgerError("event id is already used by another event")

        seq = int(
            connection.execute(
                "SELECT COALESCE(MAX(seq), 0) + 1 FROM events WHERE run_id = ?", (run_id,)
            ).fetchone()[0]
        )
        connection.execute(
            """INSERT INTO events
               (run_id, seq, event_id, event_type, idempotency_key,
                payload_json, payload_digest, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, seq, event_id, event_type, idempotency_key, payload_json, payload_hash, now),
        )
        connection.execute("UPDATE runs SET updated_at = ? WHERE run_id = ?", (now, run_id))
        return {
            "run_id": run_id,
            "seq": seq,
            "event_id": event_id,
            "event_type": event_type,
            "payload": payload,
        }

    def has_run(self, run_id: str) -> bool:
        validate_run_id(run_id)
        with self._connect() as connection:
            return connection.execute(
                "SELECT 1 FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone() is not None

    def create_run(
        self,
        *,
        task_digest_value: str,
        project_path: str,
        run_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        run_id = validate_run_id(run_id or uuid.uuid4().hex)
        if not re.fullmatch(r"[0-9a-f]{64}", task_digest_value):
            raise LedgerError("task digest must be a SHA-256 digest")
        if not isinstance(project_path, str):
            raise LedgerError("project path must be a string")
        metadata_json = _canonical_json(metadata or {})
        now = time.time()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT task_digest, project_path, metadata_json FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if existing is not None:
                connection.rollback()
                raise RunResumeRejected("run_id already exists; resume it explicitly")
            connection.execute(
                """INSERT INTO runs
                   (run_id, status, task_digest, project_path, metadata_json,
                    runner_required, created_at, updated_at)
                   VALUES (?, 'running', ?, ?, ?, 0, ?, ?)""",
                (run_id, task_digest_value, project_path, metadata_json, now, now),
            )
            self._append_event(
                connection,
                run_id,
                "RUN_CREATED",
                {"task_digest": task_digest_value, "project_path": project_path},
                idempotency_key="run-created",
                now=now,
            )
            connection.commit()
        return run_id

    def resume_run(self, run_id: str, *, task_digest_value: str, project_path: str) -> dict[str, Any]:
        validate_run_id(run_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        if row is None:
            raise RunResumeRejected("unknown run_id")
        if row["task_digest"] != task_digest_value or row["project_path"] != project_path:
            raise RunResumeRejected("run_id is bound to a different task or project")
        result = dict(row)
        result["metadata"] = json.loads(result.pop("metadata_json"))
        return result

    def append_event(
        self,
        run_id: str,
        event_type: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        runner_fence: str | None = None,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            event = self._append_event(
                connection,
                run_id,
                event_type,
                payload,
                idempotency_key=idempotency_key,
                runner_fence=runner_fence,
            )
            connection.commit()
            return event

    def events(self, run_id: str) -> list[dict[str, Any]]:
        validate_run_id(run_id)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM events WHERE run_id = ? ORDER BY seq", (run_id,)
            ).fetchall()
        return [
            {
                "run_id": row["run_id"],
                "seq": int(row["seq"]),
                "event_id": row["event_id"],
                "event_type": row["event_type"],
                "idempotency_key": row["idempotency_key"],
                "payload": json.loads(row["payload_json"]),
                "created_at": float(row["created_at"]),
            }
            for row in rows
        ]

    def claim_runner(self, run_id: str, owner: str, *, lease_seconds: int = 900) -> str:
        validate_run_id(run_id)
        if not owner or lease_seconds < 1:
            raise LedgerError("runner owner and positive lease are required")
        now = time.time()
        fence = secrets.token_hex(32)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            claim = connection.execute(
                "SELECT owner, expires_at FROM runner_claims WHERE run_id = ?", (run_id,)
            ).fetchone()
            if claim is not None and float(claim["expires_at"]) > now:
                connection.rollback()
                raise RunnerClaimConflict(f"run is already owned by {claim['owner']}")
            connection.execute("DELETE FROM runner_claims WHERE run_id = ?", (run_id,))
            connection.execute(
                """INSERT INTO runner_claims
                   (run_id, owner, fence_id, claimed_at, expires_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (run_id, owner, fence, now, now + lease_seconds),
            )
            connection.execute(
                "UPDATE runs SET runner_required = 1, updated_at = ? WHERE run_id = ?",
                (now, run_id),
            )
            self._append_event(
                connection,
                run_id,
                "RUNNER_CLAIMED",
                {"owner": owner, "lease_seconds": lease_seconds},
                runner_fence=fence,
                now=now,
            )
            connection.commit()
        return fence

    def renew_runner(
        self, run_id: str, owner: str, runner_fence: str, *, lease_seconds: int = 900
    ) -> float:
        now = time.time()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            claim = connection.execute(
                "SELECT owner, fence_id, expires_at FROM runner_claims WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if (
                claim is None
                or claim["owner"] != owner
                or not secrets.compare_digest(str(claim["fence_id"]), runner_fence)
                or float(claim["expires_at"]) <= now
            ):
                connection.rollback()
                raise RunnerClaimConflict("runner claim owner, fence, or lease does not match")
            expires_at = now + lease_seconds
            connection.execute(
                "UPDATE runner_claims SET expires_at = ? WHERE run_id = ? AND fence_id = ?",
                (expires_at, run_id, runner_fence),
            )
            connection.commit()
        return expires_at

    def release_runner(self, run_id: str, owner: str, runner_fence: str) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            claim = connection.execute(
                "SELECT owner, fence_id FROM runner_claims WHERE run_id = ?", (run_id,)
            ).fetchone()
            if (
                claim is None
                or claim["owner"] != owner
                or not secrets.compare_digest(str(claim["fence_id"]), runner_fence)
            ):
                connection.rollback()
                raise RunnerClaimConflict("runner claim owner or fence does not match")
            self._append_event(
                connection,
                run_id,
                "RUNNER_RELEASED",
                {"owner": owner},
                runner_fence=runner_fence,
            )
            connection.execute(
                "DELETE FROM runner_claims WHERE run_id = ? AND fence_id = ?",
                (run_id, runner_fence),
            )
            connection.commit()

    def record_action_intent(
        self,
        run_id: str,
        action: str,
        idempotency_key: str,
        payload: dict[str, Any],
        *,
        side_effect: bool,
        runner_fence: str,
    ) -> dict[str, Any]:
        return self.append_event(
            run_id,
            "ACTION_INTENT",
            {"action": action, "payload": payload, "side_effect": bool(side_effect)},
            idempotency_key=idempotency_key,
            runner_fence=runner_fence,
        )

    def record_action_result(
        self,
        run_id: str,
        idempotency_key: str,
        result: dict[str, Any],
        *,
        runner_fence: str,
    ) -> dict[str, Any]:
        intents = {
            event["idempotency_key"]
            for event in self.events(run_id)
            if event["event_type"] == "ACTION_INTENT"
        }
        if idempotency_key not in intents:
            raise LedgerError("action result has no matching intent")
        return self.append_event(
            run_id,
            "ACTION_RESULT",
            {"result": result},
            idempotency_key=idempotency_key,
            runner_fence=runner_fence,
        )

    def unresolved_side_effects(self, run_id: str) -> list[dict[str, Any]]:
        events = self.events(run_id)
        results = {
            event["idempotency_key"]
            for event in events
            if event["event_type"] == "ACTION_RESULT"
        }
        return [
            event
            for event in events
            if event["event_type"] == "ACTION_INTENT"
            and event["payload"].get("side_effect") is True
            and event["idempotency_key"] not in results
        ]

    def latest_action_result(self, run_id: str, action: str) -> dict[str, Any] | None:
        intents = {
            event["idempotency_key"]: event
            for event in self.events(run_id)
            if event["event_type"] == "ACTION_INTENT"
            and event["payload"].get("action") == action
        }
        for event in reversed(self.events(run_id)):
            if event["event_type"] == "ACTION_RESULT" and event["idempotency_key"] in intents:
                return event["payload"]["result"]
        return None

    def save_checkpoint(
        self, run_id: str, state: dict[str, Any], *, runner_fence: str
    ) -> None:
        encoded = _canonical_json(state)
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            event = self._append_event(
                connection,
                run_id,
                "CHECKPOINT_SAVED",
                {"state_digest": digest},
                runner_fence=runner_fence,
            )
            connection.execute(
                """INSERT INTO snapshots (run_id, last_seq, state_json, state_digest, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(run_id) DO UPDATE SET
                     last_seq=excluded.last_seq, state_json=excluded.state_json,
                     state_digest=excluded.state_digest, updated_at=excluded.updated_at""",
                (run_id, event["seq"], encoded, digest, time.time()),
            )
            connection.commit()

    def load_checkpoint(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT state_json FROM snapshots WHERE run_id = ?", (run_id,)
            ).fetchone()
        return json.loads(row["state_json"]) if row is not None else None

    def finish_run(self, run_id: str, status: str, *, runner_fence: str) -> None:
        if status not in {"completed", "failed", "paused"}:
            raise LedgerError("invalid terminal run status")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._append_event(
                connection,
                run_id,
                "RUN_FINISHED",
                {"status": status},
                runner_fence=runner_fence,
            )
            connection.execute(
                "UPDATE runs SET status = ?, updated_at = ? WHERE run_id = ?",
                (status, time.time(), run_id),
            )
            connection.commit()

    def run_status(self, run_id: str) -> str:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        if row is None:
            raise LedgerError(f"unknown run: {run_id}")
        return str(row["status"])
