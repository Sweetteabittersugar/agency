from __future__ import annotations

import sqlite3

import pytest

from maestro.run_ledger import (
    LedgerError,
    RunLedger,
    RunnerClaimConflict,
    RunResumeRejected,
    task_digest,
    validate_run_id,
)


@pytest.mark.parametrize("value", ["", " spaces", "../escape", "x" * 65, "é"])
def test_invalid_run_id_is_rejected(value):
    with pytest.raises(LedgerError):
        validate_run_id(value)


def test_resume_requires_the_same_task_and_project(tmp_path):
    ledger = RunLedger(tmp_path / "runs.sqlite3")
    run_id = ledger.create_run(
        run_id="run-1",
        task_digest_value=task_digest("build it"),
        project_path=str(tmp_path),
    )
    assert ledger.resume_run(
        run_id,
        task_digest_value=task_digest("build it"),
        project_path=str(tmp_path),
    )["run_id"] == run_id
    with pytest.raises(RunResumeRejected, match="different task or project"):
        ledger.resume_run(
            run_id,
            task_digest_value=task_digest("different"),
            project_path=str(tmp_path),
        )


def test_one_live_runner_owns_a_run(tmp_path):
    ledger = RunLedger(tmp_path / "runs.sqlite3")
    run_id = ledger.create_run(
        task_digest_value=task_digest("task"), project_path=str(tmp_path)
    )
    fence = ledger.claim_runner(run_id, "runner-a", lease_seconds=60)
    with pytest.raises(RunnerClaimConflict, match="runner-a"):
        ledger.claim_runner(run_id, "runner-b", lease_seconds=60)
    ledger.release_runner(run_id, "runner-a", fence)
    ledger.claim_runner(run_id, "runner-b", lease_seconds=60)


def test_unresolved_side_effect_survives_restart(tmp_path):
    path = tmp_path / "runs.sqlite3"
    ledger = RunLedger(path)
    run_id = ledger.create_run(
        task_digest_value=task_digest("task"), project_path=str(tmp_path)
    )
    fence = ledger.claim_runner(run_id, "runner", lease_seconds=60)
    ledger.record_action_intent(
        run_id,
        "implement",
        "implement:0",
        {"path": "a.py"},
        side_effect=True,
        runner_fence=fence,
    )

    reopened = RunLedger(path)
    assert [item["idempotency_key"] for item in reopened.unresolved_side_effects(run_id)] == [
        "implement:0"
    ]


def test_action_result_clears_reconciliation_requirement(tmp_path):
    ledger = RunLedger(tmp_path / "runs.sqlite3")
    run_id = ledger.create_run(
        task_digest_value=task_digest("task"), project_path=str(tmp_path)
    )
    fence = ledger.claim_runner(run_id, "runner", lease_seconds=60)
    ledger.record_action_intent(
        run_id,
        "implement",
        "implement:0",
        {},
        side_effect=True,
        runner_fence=fence,
    )
    ledger.record_action_result(
        run_id,
        "implement:0",
        {"status": "completed"},
        runner_fence=fence,
    )
    assert ledger.unresolved_side_effects(run_id) == []


def test_events_are_database_enforced_append_only(tmp_path):
    path = tmp_path / "runs.sqlite3"
    ledger = RunLedger(path)
    run_id = ledger.create_run(
        task_digest_value=task_digest("task"), project_path=str(tmp_path)
    )
    with sqlite3.connect(path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM events WHERE run_id = ?", (run_id,))
