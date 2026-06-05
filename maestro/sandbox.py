"""Sandbox isolation for agent execution.

Creates isolated execution environments for agents and runs Claude Code
with appropriate permissions, system prompts, and output capture.

Lightweight: uses subprocess + Start-Process for terminal window isolation.
Worktree isolation is handled by the caller (dispatch.py) when requested.
"""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import os

PROJECT_ROOT = os.environ.get("CLAUDE_PROJECT_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MAESTRO_DIR = Path(__file__).resolve().parent
TASKS_DIR = MAESTRO_DIR / "tasks"
RESULTS_DIR = MAESTRO_DIR / "results"


@dataclass
class SandboxResult:
    """Result from sandbox execution."""
    status: str       # "DONE" | "FAILED" | "TIMEOUT" | "CANCELLED"
    output: str       # agent's output text (first 5000 chars)
    task_id: str
    elapsed_ms: float


def execute_in_sandbox(
    agent_cfg: dict,
    task_desc: str,
    context: str | None = None,
    dag_id: str | None = None,
    timeout: int = 600,
) -> SandboxResult:
    """Execute an agent task in a sandbox environment.

    Args:
        agent_cfg: Agent configuration from agents.json
        task_desc: The task description to pass to the agent
        context: Optional additional context for the task
        dag_id: Optional task ID (generated if not provided)
        timeout: Timeout in seconds (default 600 = 10min)

    Returns:
        SandboxResult with status and output
    """
    task_id = dag_id or uuid.uuid4().hex[:8]
    agent_name = agent_cfg.get("name", "agent")
    model = agent_cfg.get("model", "sonnet")
    work_dir = agent_cfg.get("work_dir", PROJECT_ROOT)
    tools = agent_cfg.get("allowed_tools", "Read,Glob,Grep")
    prompt_file = agent_cfg.get("system_prompt_file", "")
    isolation = agent_cfg.get("isolation", "none")

    # Build full task prompt
    full_task = f"你是执行者，直接完成任务，不转派不反问。\n\n{task_desc}"
    if context:
        full_task = f"{context}\n\n---\n\n你是执行者，直接完成任务，不转派不反问。\n\n任务: {task_desc}"

    # Result output instruction
    result_path = str(RESULTS_DIR / f"{task_id}.txt").replace("\\", "/")
    result_instruction = (
        "完成后将结果写入 " + result_path +
        " -- 第一行写 STATUS: DONE 或 STATUS: FAILED，" +
        "然后写 ## 详细结果（包含完整执行过程），" +
        "然后写 ## 用户摘要（面向 boss 的精简结果，无内部过程，无原始数据）"
    )

    # Build Claude Code command
    claude_cmd = f'claude -p "{full_task}"'
    claude_cmd += f' --name "{agent_name}"'
    if prompt_file:
        claude_cmd += f' --system-prompt-file "{prompt_file}"'
    claude_cmd += (
        f' --append-system-prompt "{result_instruction}"'
        f' --model "{model}"'
        f' --allowedTools "{tools}"'
        f' --output-format text'
        f' --permission-mode auto'
    )

    # Write launch script
    launch_id = task_id[:8]
    script_path = MAESTRO_DIR / f"_launch_{launch_id}.ps1"
    lines = [
        f'Write-Host "Maestro Agent: {agent_name} | Task: {launch_id} | Model: {model}"',
        f'Write-Host "Working dir: {work_dir}"',
        f'Write-Host "---"',
        f'cd "{work_dir}"',
        claude_cmd,
        f'Write-Host ""',
        f'Write-Host "=== Agent finished. You can close this window. ==="',
    ]
    script_path.write_text("\n".join(lines), encoding="utf-8-sig")

    # Launch in new terminal window
    start_time = datetime.now(timezone.utc)
    try:
        ps_cmd = (
            f'Start-Process powershell'
            f' -ArgumentList "-NoProfile","-File","{script_path}"'
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            cwd=work_dir,
            check=False,
            timeout=30,  # 30s to launch, actual work is async
        )

        # The agent runs asynchronously in its own terminal.
        # Return immediately — result will be written to result_path by agent.
        return SandboxResult(
            status="DISPATCHED",
            output=f"Agent {agent_name} launched in new terminal (task: {launch_id})",
            task_id=launch_id,
            elapsed_ms=(datetime.now(timezone.utc) - start_time).total_seconds() * 1000,
        )

    except subprocess.TimeoutExpired:
        return SandboxResult(
            status="FAILED",
            output=f"Launch timeout for agent {agent_name}",
            task_id=launch_id,
            elapsed_ms=(datetime.now(timezone.utc) - start_time).total_seconds() * 1000,
        )
    except Exception as e:
        return SandboxResult(
            status="FAILED",
            output=f"Sandbox error: {e}",
            task_id=launch_id,
            elapsed_ms=(datetime.now(timezone.utc) - start_time).total_seconds() * 1000,
        )
