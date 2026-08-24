from __future__ import annotations

from maestro.execution_dag import DagNode, ExecutionDAG
from maestro.run_ledger import RunLedger, task_digest


def _ledger_and_claim(tmp_path):
    ledger = RunLedger(tmp_path / "runs.sqlite3")
    run_id = ledger.create_run(
        task_digest_value=task_digest("task"), project_path=str(tmp_path)
    )
    fence = ledger.claim_runner(run_id, "runner", lease_seconds=60)
    return ledger, run_id, fence


def _nodes(plan_digest="plan-v1"):
    return [
        DagNode("plan", "plan", input_digest=plan_digest),
        DagNode("implement", "write", ("plan",), "implementation-v1"),
        DagNode("verify", "verify", ("implement",), "verification-v1"),
    ]


def test_dag_resumes_completed_nodes_after_restart(tmp_path):
    ledger, run_id, fence = _ledger_and_claim(tmp_path)
    dag = ExecutionDAG(ledger, run_id, _nodes(), runner_fence=fence)
    dag.start("plan")
    dag.complete("plan", output_ref="artifact://plan", output_digest="a" * 64)

    reopened = ExecutionDAG(RunLedger(ledger.path), run_id, _nodes(), runner_fence=fence)
    assert reopened.state()["plan"]["status"] == "completed"
    assert reopened.ready_nodes() == ["implement"]


def test_upstream_input_change_invalidates_downstream(tmp_path):
    ledger, run_id, fence = _ledger_and_claim(tmp_path)
    dag = ExecutionDAG(ledger, run_id, _nodes(), runner_fence=fence)
    dag.start("plan")
    dag.complete("plan", output_ref="artifact://plan", output_digest="a" * 64)
    dag.start("implement")
    dag.complete("implement", output_ref="artifact://implement", output_digest="b" * 64)

    changed = ExecutionDAG(
        ledger, run_id, _nodes(plan_digest="plan-v2"), runner_fence=fence
    )
    assert {item["status"] for item in changed.state().values()} == {"stale"}
