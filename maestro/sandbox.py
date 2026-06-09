"""Sandbox isolation for agent execution.

Creates isolated execution environments for agents and runs Claude Code
with appropriate permissions, system prompts, and output capture.
Uses subprocess + Start-Process for terminal window isolation.
Worktree isolation is handled by the caller (dispatch.py) when requested.

DAG support: tasks can declare depends_on for dependency ordering.
File batches: related files can be grouped as a batch for unified submission.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = os.environ.get("CLAUDE_PROJECT_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MAESTRO_DIR = Path(__file__).resolve().parent
TASKS_DIR = MAESTRO_DIR / "tasks"
RESULTS_DIR = MAESTRO_DIR / "results"
PROMPTS_DIR = MAESTRO_DIR / "_prompts"  # temp prompt files (avoids shell injection)

# MCP 状态文件路径
MCP_STATE_FILE = MAESTRO_DIR / "mcp_state.json"

# ── DAG 依赖追踪 ──
_dag_registry: dict[str, dict] = {}       # task_id -> {status, depends_on, blocked_by, batch_id, ...}
_dag_lock = threading.Lock()


def _load_mcp_state() -> dict:
    """加载 MCP 启用/禁用状态，默认全部启用。"""
    try:
        if MCP_STATE_FILE.exists():
            return json.loads(MCP_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_mcp_state(state: dict) -> None:
    """保存 MCP 启用/禁用状态。"""
    MCP_STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _get_mcp_permissions(project_root: str | None = None) -> list[str]:
    """从 .mcp.json 读取已启用的 MCP 服务器，生成权限前缀列表。

    返回格式: ['mcp__plugin_playwright_playwright__*', ...]
    """
    root = Path(project_root) if project_root else Path(PROJECT_ROOT)
    state = _load_mcp_state()
    permissions = []

    mcp_sources = [
        root / ".mcp.json",
        Path.home() / ".claude" / ".mcp.json",
    ]
    seen = set()

    for src in mcp_sources:
        if not src.exists():
            continue
        try:
            mcp = json.loads(src.read_text(encoding="utf-8"))
            for name in mcp.get("mcpServers", {}):
                if name in seen:
                    continue
                seen.add(name)
                # 默认启用，除非 mcp_state.json 显式设为 false
                if state.get(name, True):
                    permissions.append(f"mcp__plugin_{name}_{name}__*")
        except Exception:
            pass

    return permissions


def _get_mcp_tool_descriptions(project_root: str | None = None) -> str:
    """生成 MCP 工具清单描述，注入到 Agent system prompt。"""
    root = Path(project_root) if project_root else Path(PROJECT_ROOT)
    state = _load_mcp_state()

    # MCP 服务器描述映射
    DESCRIPTIONS = {
        "playwright": "浏览器自动化（Playwright）— 网页导航、截图、操作、测试",
        "context7": "文档查询（Context7）— 实时库/框架文档和代码示例",
        "github": "GitHub API — 仓库操作、PR、Issue 管理",
        "brave-search": "网络搜索（Brave Search）",
        "sequential-thinking": "深度推理（Sequential Thinking）— 分步骤思考",
    }

    servers = []
    mcp_sources = [
        root / ".mcp.json",
        Path.home() / ".claude" / ".mcp.json",
    ]
    seen = set()

    for src in mcp_sources:
        if not src.exists():
            continue
        try:
            mcp = json.loads(src.read_text(encoding="utf-8"))
            for name in mcp.get("mcpServers", {}):
                if name in seen:
                    continue
                seen.add(name)
                if state.get(name, True):
                    desc = DESCRIPTIONS.get(name, name)
                    servers.append(f"- {name}: {desc}")
        except Exception:
            pass

    if servers:
        return "可用外部工具：\n" + "\n".join(servers)
    return ""


# ── DAG 依赖解析 ──

@dataclass
class DAGNode:
    """DAG 任务节点。"""
    task_id: str
    status: str = "pending"       # pending | running | done | failed
    depends_on: list[str] = field(default_factory=list)
    blocked_by: list[str] = field(default_factory=list)
    batch_id: str | None = None
    agent_cfg: dict | None = None
    task_desc: str = ""
    submitted_at: float = 0.0


def register_dag_task(
    task_id: str,
    depends_on: list[str] | None = None,
    batch_id: str | None = None,
) -> DAGNode:
    """注册一个 DAG 任务节点，解析依赖关系。"""
    with _dag_lock:
        deps = depends_on or []
        node = DAGNode(
            task_id=task_id,
            depends_on=list(deps),
            blocked_by=[d for d in deps if d in _dag_registry and _dag_registry[d].get("status") != "done"],
            batch_id=batch_id,
            submitted_at=time.time(),
        )
        _dag_registry[task_id] = {
            "status": "pending",
            "depends_on": deps,
            "blocked_by": node.blocked_by,
            "batch_id": batch_id,
            "submitted_at": node.submitted_at,
        }
        return node


def is_task_ready(task_id: str) -> bool:
    """检查任务是否可以执行（所有依赖已完成）。"""
    with _dag_lock:
        entry = _dag_registry.get(task_id)
        if not entry:
            return True
        for dep in entry.get("depends_on", []):
            dep_entry = _dag_registry.get(dep)
            if not dep_entry or dep_entry.get("status") != "done":
                return False
        return True


def mark_dag_done(task_id: str, status: str = "done") -> None:
    """标记 DAG 任务完成，解除后续任务的阻塞。"""
    with _dag_lock:
        if task_id in _dag_registry:
            _dag_registry[task_id]["status"] = status
        # 解除被此任务阻塞的后续任务
        for tid, entry in _dag_registry.items():
            if task_id in entry.get("depends_on", []):
                # 重新计算 blocked_by
                entry["blocked_by"] = [
                    d for d in entry.get("depends_on", [])
                    if d in _dag_registry and _dag_registry[d].get("status") != "done"
                ]


def get_dag_tree(task_id: str) -> dict | None:
    """获取 DAG 依赖树（缩进树形结构）。"""
    with _dag_lock:
        entry = _dag_registry.get(task_id)
        if not entry:
            return None
        tree = {
            "task_id": task_id,
            "status": entry.get("status", "unknown"),
            "batch_id": entry.get("batch_id"),
            "children": [],
        }
        for dep in entry.get("depends_on", []):
            subtree = get_dag_tree(dep)
            if subtree:
                tree["children"].append(subtree)
        return tree


def get_batch_tasks(batch_id: str) -> list[dict]:
    """获取同一批次的所有任务。"""
    with _dag_lock:
        return [
            {"task_id": tid, "status": entry.get("status", "unknown")}
            for tid, entry in _dag_registry.items()
            if entry.get("batch_id") == batch_id
        ]


def submit_file_batch(files: list[str], task_desc: str) -> str:
    """将关联文件打包为一个批次并统一提交。

    Returns:
        batch_id (str): 批次 ID
    """
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    with _dag_lock:
        for fpath in files:
            tid = f"file_{uuid.uuid4().hex[:6]}"
            _dag_registry[tid] = {
                "status": "pending",
                "depends_on": [],
                "blocked_by": [],
                "batch_id": batch_id,
                "file_path": fpath,
            }
    return batch_id


# ── Sandbox 执行 ──

@dataclass
class SandboxResult:
    """Result from sandbox execution."""
    status: str       # "DISPATCHED" | "FAILED" | "TIMEOUT" | "CANCELLED"
    output: str       # agent's output text (first 5000 chars)
    task_id: str
    elapsed_ms: float
    dag_info: dict | None = None  # DAG 依赖信息


def _write_prompt_file(content: str, prefix: str = "task") -> Path:
    """将 prompt 内容写入临时文件，避免 shell 注入。"""
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4().hex[:8]
    filepath = PROMPTS_DIR / f"{prefix}_{file_id}.txt"
    filepath.write_text(content, encoding="utf-8")
    return filepath


def execute_in_sandbox(
    agent_cfg: dict,
    task_desc: str,
    context: str | None = None,
    dag_id: str | None = None,
    timeout: int = 600,
    depends_on: list[str] | None = None,
    batch_id: str | None = None,
) -> SandboxResult:
    """Execute an agent task in a sandbox environment.

    Args:
        agent_cfg: Agent configuration from agents.json
        task_desc: The task description to pass to the agent
        context: Optional additional context for the task
        dag_id: Optional task ID (generated if not provided)
        timeout: Timeout in seconds (default 600 = 10min)
        depends_on: Optional list of task IDs this task depends on
        batch_id: Optional batch ID for grouping related tasks

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

    # ── DAG 依赖注册 ──
    dag_node = None
    if depends_on or batch_id:
        dag_node = register_dag_task(task_id, depends_on=depends_on, batch_id=batch_id)

    # ── MCP 权限注入 ──
    mcp_perms = _get_mcp_permissions(PROJECT_ROOT)
    if mcp_perms:
        tools = tools + "," + ",".join(mcp_perms)

    # ── MCP 工具发现注入 ──
    mcp_tool_desc = _get_mcp_tool_descriptions(PROJECT_ROOT)

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

    # 注入 MCP 工具发现
    if mcp_tool_desc:
        result_instruction += "\\n\\n" + mcp_tool_desc

    # ── 安全：将用户输入写入临时文件以避免 shell 注入 ──
    task_prompt_file = _write_prompt_file(full_task, "task")
    result_prompt_file = _write_prompt_file(result_instruction, "result")

    # Build launch script (safe: only controlled values embedded; user input via files)
    launch_id = task_id[:8]
    script_path = MAESTRO_DIR / f"_launch_{launch_id}.ps1"

    # PowerShell 脚本内容：从文件读取 prompt，安全传参给 claude
    task_file_escaped = str(task_prompt_file).replace("\\", "/")
    result_file_escaped = str(result_prompt_file).replace("\\", "/")
    prompt_file_arg = f' --system-prompt-file "{prompt_file}"' if prompt_file else ""
    allowed_tools = tools.replace('"', '`"')  # escape double quotes for PS

    lines = [
        f'Write-Host "Maestro Agent: {agent_name} | Task: {launch_id} | Model: {model}"',
        f'Write-Host "Working dir: {work_dir}"',
        f'Write-Host "---"',
        f'cd "{work_dir}"',
        # 从临时文件读取 prompt（避免 shell 注入）
        f'$taskPrompt = Get-Content -Path "{task_file_escaped}" -Raw -Encoding UTF8',
        f'$resultPrompt = Get-Content -Path "{result_file_escaped}" -Raw -Encoding UTF8',
        # 使用列表形式传参给 claude
        f'$claudeArgs = @(',
        f'  "-p", $taskPrompt,',
        f'  "--name", "{agent_name}",',
    ]
    if prompt_file:
        lines.append(f'  "--system-prompt-file", "{prompt_file}",')
    lines.extend([
        f'  "--append-system-prompt", $resultPrompt,',
        f'  "--model", "{model}",',
        f'  "--allowedTools", "{allowed_tools}",',
        f'  "--output-format", "stream-json",',
        f'  "--max-turns", "50",',
        f'  "--max-budget-usd", "0.50",',
        f'  "--permission-mode", "acceptEdits"',
        f')',
        f'& claude @claudeArgs',
        f'Write-Host ""',
        f'Write-Host "=== Agent finished. You can close this window. ==="',
        # 清理临时 prompt 文件
        f'Remove-Item -Path "{task_file_escaped}" -ErrorAction SilentlyContinue',
        f'Remove-Item -Path "{result_file_escaped}" -ErrorAction SilentlyContinue',
    ])
    script_path.write_text("\n".join(lines), encoding="utf-8-sig")

    # Launch in new terminal window (safe: Start-Process args are all controlled)
    start_time = datetime.now(timezone.utc)
    dag_info = None
    if dag_node:
        dag_info = {
            "task_id": task_id,
            "depends_on": dag_node.depends_on,
            "blocked_by": dag_node.blocked_by,
            "batch_id": batch_id,
        }

    try:
        # subprocess.Popen with list args — no shell parsing of user input
        subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                f'Start-Process powershell -ArgumentList "-NoProfile","-File","{script_path}"',
            ],
            cwd=work_dir,
            check=False,
            timeout=30,
        )

        # Update DAG state
        if dag_node:
            mark_dag_done(task_id, "running")

        return SandboxResult(
            status="DISPATCHED",
            output=f"Agent {agent_name} launched in new terminal (task: {launch_id})",
            task_id=launch_id,
            elapsed_ms=(datetime.now(timezone.utc) - start_time).total_seconds() * 1000,
            dag_info=dag_info,
        )

    except subprocess.TimeoutExpired:
        if dag_node:
            mark_dag_done(task_id, "failed")
        return SandboxResult(
            status="FAILED",
            output=f"Launch timeout for agent {agent_name}",
            task_id=launch_id,
            elapsed_ms=(datetime.now(timezone.utc) - start_time).total_seconds() * 1000,
            dag_info=dag_info,
        )
    except Exception as e:
        if dag_node:
            mark_dag_done(task_id, "failed")
        return SandboxResult(
            status="FAILED",
            output=f"Sandbox error: {e}",
            task_id=launch_id,
            elapsed_ms=(datetime.now(timezone.utc) - start_time).total_seconds() * 1000,
            dag_info=dag_info,
        )
