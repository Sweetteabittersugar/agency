"""Execution DAG reconstructed from the local durable run ledger."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable

from maestro.run_ledger import RunLedger


class DagError(RuntimeError):
    """Invalid DAG definition or transition."""


@dataclass(frozen=True)
class DagNode:
    node_id: str
    kind: str
    dependencies: tuple[str, ...] = ()
    input_digest: str = ""


def _digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class ExecutionDAG:
    def __init__(
        self,
        ledger: RunLedger,
        run_id: str,
        nodes: Iterable[DagNode],
        *,
        runner_fence: str,
    ):
        self.ledger = ledger
        self.run_id = run_id
        self.runner_fence = runner_fence
        node_list = list(nodes)
        self.nodes = {node.node_id: node for node in node_list}
        if not self.nodes:
            raise DagError("DAG requires at least one node")
        if len(self.nodes) != len(node_list):
            raise DagError("DAG node ids must be unique")
        for node in self.nodes.values():
            missing = set(node.dependencies) - set(self.nodes)
            if missing:
                raise DagError(f"unknown dependencies for {node.node_id}: {sorted(missing)}")
        self._assert_acyclic()
        self._define_or_reconcile()

    def _definition(self) -> dict[str, Any]:
        return {
            "nodes": [
                {
                    "node_id": node.node_id,
                    "kind": node.kind,
                    "dependencies": list(node.dependencies),
                    "input_digest": node.input_digest,
                }
                for node in self.nodes.values()
            ]
        }

    def _assert_acyclic(self) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise DagError("DAG contains a cycle")
            if node_id in visited:
                return
            visiting.add(node_id)
            for dependency in self.nodes[node_id].dependencies:
                visit(dependency)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in self.nodes:
            visit(node_id)

    def _define_or_reconcile(self) -> None:
        definitions = [
            event for event in self.ledger.events(self.run_id)
            if event["event_type"] == "DAG_DEFINED"
        ]
        current = self._definition()
        if not definitions:
            self.ledger.append_event(
                self.run_id,
                "DAG_DEFINED",
                {**current, "definition_digest": _digest(current)},
                idempotency_key="dag-definition",
                runner_fence=self.runner_fence,
            )
            return
        original_nodes = {
            item["node_id"]: item for item in definitions[0]["payload"]["nodes"]
        }
        if set(original_nodes) != set(self.nodes):
            raise DagError("DAG topology changed for an existing run")
        latest_inputs = {
            node_id: item.get("input_digest", "") for node_id, item in original_nodes.items()
        }
        for event in self.ledger.events(self.run_id):
            if event["event_type"] == "NODE_INPUT_CHANGED":
                latest_inputs[event["payload"]["node_id"]] = event["payload"]["input_digest"]
        for node_id, node in self.nodes.items():
            old = original_nodes[node_id]
            if old["kind"] != node.kind or tuple(old["dependencies"]) != node.dependencies:
                raise DagError("DAG topology changed for an existing run")
            if latest_inputs[node_id] != node.input_digest:
                self.invalidate(node_id, node.input_digest)

    def state(self) -> dict[str, dict[str, Any]]:
        state = {
            node_id: {
                "status": "pending",
                "input_digest": node.input_digest,
                "output_digest": None,
                "output_ref": None,
            }
            for node_id, node in self.nodes.items()
        }
        for event in self.ledger.events(self.run_id):
            payload = event["payload"]
            node_id = payload.get("node_id")
            if node_id not in state:
                continue
            if event["event_type"] == "NODE_STARTED":
                state[node_id]["status"] = "running"
            elif event["event_type"] == "NODE_COMPLETED":
                state[node_id].update(
                    status="completed",
                    output_digest=payload.get("output_digest"),
                    output_ref=payload.get("output_ref"),
                )
            elif event["event_type"] == "NODE_FAILED":
                state[node_id]["status"] = "failed"
            elif event["event_type"] == "NODE_BLOCKED":
                state[node_id]["status"] = "blocked"
            elif event["event_type"] == "NODE_INPUT_CHANGED":
                state[node_id]["input_digest"] = payload["input_digest"]
            elif event["event_type"] == "NODE_INVALIDATED":
                state[node_id].update(status="stale", output_digest=None, output_ref=None)
        return state

    def ready_nodes(self) -> list[str]:
        state = self.state()
        return [
            node_id for node_id, node in self.nodes.items()
            if state[node_id]["status"] in {"pending", "stale", "failed", "blocked", "running"}
            and all(state[dep]["status"] == "completed" for dep in node.dependencies)
        ]

    def start(self, node_id: str) -> None:
        if node_id not in self.ready_nodes():
            raise DagError(f"node is not ready: {node_id}")
        self.ledger.append_event(
            self.run_id,
            "NODE_STARTED",
            {"node_id": node_id},
            runner_fence=self.runner_fence,
        )

    def complete(self, node_id: str, *, output_ref: str, output_digest: str) -> None:
        if self.state()[node_id]["status"] != "running":
            raise DagError(f"node is not running: {node_id}")
        self.ledger.append_event(
            self.run_id,
            "NODE_COMPLETED",
            {
                "node_id": node_id,
                "output_ref": output_ref,
                "output_digest": output_digest,
            },
            runner_fence=self.runner_fence,
        )
        self.ledger.save_checkpoint(self.run_id, self.state(), runner_fence=self.runner_fence)

    def fail(self, node_id: str, reason: str) -> None:
        self.ledger.append_event(
            self.run_id,
            "NODE_FAILED",
            {"node_id": node_id, "reason": reason[:500]},
            runner_fence=self.runner_fence,
        )
        self.ledger.save_checkpoint(self.run_id, self.state(), runner_fence=self.runner_fence)

    def block(self, node_id: str, reason: str) -> None:
        self.ledger.append_event(
            self.run_id,
            "NODE_BLOCKED",
            {"node_id": node_id, "reason": reason[:500]},
            runner_fence=self.runner_fence,
        )
        self.ledger.save_checkpoint(self.run_id, self.state(), runner_fence=self.runner_fence)

    def invalidate(self, node_id: str, new_input_digest: str) -> None:
        if node_id not in self.nodes:
            raise DagError(f"unknown node: {node_id}")
        self.ledger.append_event(
            self.run_id,
            "NODE_INPUT_CHANGED",
            {"node_id": node_id, "input_digest": new_input_digest},
            runner_fence=self.runner_fence,
        )
        affected = {node_id}
        changed = True
        while changed:
            changed = False
            for candidate in self.nodes.values():
                if candidate.node_id not in affected and affected.intersection(candidate.dependencies):
                    affected.add(candidate.node_id)
                    changed = True
        for affected_id in sorted(affected):
            self.ledger.append_event(
                self.run_id,
                "NODE_INVALIDATED",
                {"node_id": affected_id, "source_node": node_id},
                runner_fence=self.runner_fence,
            )
        self.ledger.save_checkpoint(self.run_id, self.state(), runner_fence=self.runner_fence)
