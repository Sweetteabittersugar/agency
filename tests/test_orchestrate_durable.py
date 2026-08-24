from __future__ import annotations

import pytest

from maestro.project_access import configure_project_roots
from maestro.routes import orchestrate
from maestro.run_ledger import LedgerError, RunResumeRejected


@pytest.fixture(autouse=True)
def reset_roots():
    configure_project_roots([])
    yield
    configure_project_roots([])


def test_prepare_run_rejects_invalid_run_id(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    configure_project_roots([str(project)])
    monkeypatch.setattr(orchestrate, "RUN_LEDGER_PATH", tmp_path / "runs.sqlite3")
    with pytest.raises(LedgerError, match="run_id"):
        orchestrate._prepare_run(
            {"task": "task", "proj_dir": str(project), "run_id": "../escape"}
        )


def test_prepare_run_rejects_task_or_project_mismatch(tmp_path, monkeypatch):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    configure_project_roots([str(first), str(second)])
    monkeypatch.setattr(orchestrate, "RUN_LEDGER_PATH", tmp_path / "runs.sqlite3")

    durable = orchestrate._prepare_run(
        {"task": "original", "proj_dir": str(first), "run_id": "resume-1"}
    )
    durable["ledger"].release_runner(
        durable["run_id"], durable["owner"], durable["fence"]
    )

    with pytest.raises(RunResumeRejected, match="different task or project"):
        orchestrate._prepare_run(
            {"task": "changed", "proj_dir": str(first), "run_id": "resume-1"}
        )
    with pytest.raises(RunResumeRejected, match="different task or project"):
        orchestrate._prepare_run(
            {"task": "original", "proj_dir": str(second), "run_id": "resume-1"}
        )
