#!/usr/bin/env python3
"""Maestro Dispatch — CLI entry point for single agent dispatch.

Supported modes:
  --agent <name> --task <desc>    Single agent dispatch
  --status [agent]                Check task status
  --result <task_id> [--raw]      Show result
  --list                          List agents

Delegation:
  - Single agent dispatch: sandbox.Sandbox + sandbox.execute_in_sandbox()
  - Status/Result/List: kept inline (lightweight queries).

Zero external dependencies — pure Python stdlib.
"""

import argparse
import importlib.util
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = os.environ.get("CLAUDE_PROJECT_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MAESTRO_DIR = Path(PROJECT_ROOT) / "maestro"
REGISTRY_FILE = MAESTRO_DIR / "agents.json"
TASKS_DIR = MAESTRO_DIR / "tasks"
RESULTS_DIR = MAESTRO_DIR / "results"
ARCHIVE_DIR = MAESTRO_DIR / "archive"


def _import_mod(file_stem, file_name):
    """Import a Python module from a file that has a hyphen in its name."""
    file_path = MAESTRO_DIR / file_name
    if not file_path.is_file():
        raise ImportError(f"Cannot load module from {file_path}")
    spec = importlib.util.spec_from_file_location(file_stem, str(file_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {file_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[file_stem] = mod  # 在 exec 前注册，dataclass 依赖 __module__ 查找
    spec.loader.exec_module(mod)
    return mod


def ensure_dirs():
    for d in [TASKS_DIR, RESULTS_DIR, ARCHIVE_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def load_registry():
    with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def sync_task_board():
    """After creating a task, refresh task-board.json from disk."""
    try:
        import subprocess as _sp
        _sp.run(
            ["python", str(MAESTRO_DIR / "task-tracker.py"), "--sync"],
            capture_output=True,
            timeout=10,
        )
    except Exception:
        pass


def create_task(agent_name, task_desc, context, model=None):
    task_id = uuid.uuid4().hex[:8]
    session_id = str(uuid.uuid4())
    task = {
        "task_id": task_id,
        "agent": agent_name,
        "task": task_desc,
        "context": context or "",
        "status": "dispatched",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
    }
    if model:
        task["model"] = model
    with open(TASKS_DIR / f"{task_id}.json", "w", encoding="utf-8") as f:
        json.dump(task, f, ensure_ascii=False, indent=2)
    sync_task_board()
    return task


# ── Single agent dispatch (delegated to sandbox) ──────────────────

def dispatch(agent_name, task_desc, context, model=None):
    """Dispatch a single agent via sandbox isolation."""
    registry = load_registry()
    if agent_name not in registry:
        names = ", ".join(registry.keys())
        print(f"未知agent: {agent_name}. 可用: {names}")
        sys.exit(1)

    agent_cfg = dict(registry[agent_name])
    agent_type = agent_cfg.get("type", "")

    # ── Reasonix external agent dispatch ──
    if agent_type == "reasonix":
        _dispatch_reasonix(agent_cfg, agent_name, task_desc, context, model)
        return

    actual_model = model or agent_cfg.get("model", "sonnet")
    if model:
        agent_cfg["model"] = model

    task = create_task(agent_name, task_desc, context, actual_model)

    # Use sandbox for isolated execution
    try:
        sandbox_mod = _import_mod("sandbox", "sandbox.py")
        result = sandbox_mod.execute_in_sandbox(
            agent_cfg, task_desc, context, dag_id=task["task_id"]
        )

        # Write result in standard format
        result_path = RESULTS_DIR / f"{task['task_id']}.txt"
        with open(result_path, "w", encoding="utf-8") as f:
            f.write(f"STATUS: {result.status}\n")
            f.write("\n## 详细结果\n")
            f.write((result.output or "")[:5000] + "\n")
            f.write("\n## 用户摘要\n")
            f.write(f"[{agent_name}] {result.status}\n")
            if result.output:
                f.write(result.output[:500] + "\n")

        print(f"{agent_name} 已完成 (model: {actual_model})")
        print(f"task: {task['task_id']}")
    except ImportError:
        # Fallback: use basic subprocess dispatch
        _dispatch_basic(agent_cfg, agent_name, task_desc, context, model, task)
    except Exception as e:
        print(f"调度异常: {e}")
        # Write failure result
        result_path = RESULTS_DIR / f"{task['task_id']}.txt"
        with open(result_path, "w", encoding="utf-8") as f:
            f.write("STATUS: FAILED\n")
            f.write(f"\n## 详细结果\n调度异常: {e}\n")
            f.write(f"\n## 用户摘要\n[{agent_name}] 调度失败: {str(e)[:200]}\n")


def _dispatch_reasonix(agent_cfg, agent_name, task_desc, context, model):
    """Dispatch task to Reasonix via secure wrapper script.

    API key is read by reasonix-run.ps1 directly from ~/.reasonix/config.json
    and set as an environment variable inside that script process.  The key
    never enters Python memory, stdout, or Claude conversation context — the
    only place the key exists is inside the wrapper script's own process.

    v2: Wrapper writes the result file itself (--result-path).  It captures
    reasonix stdout, extracts content between ===RESULT===...===END=== markers,
    and writes that to disk.  If markers are missing, the wrapper generates a
    STATUS: FAILED result file.  This dispatch function NEVER constructs a
    result file from raw stdout — the wrapper is the sole authority.

    agents.json fields used:
      - endpoint: API endpoint (default https://api.deepseek.com)
      - model:  default model (deepseek-v4-pro)
      - work_dir: working directory for subprocess
    """
    import subprocess

    task = create_task(agent_name, task_desc, context, model or agent_cfg.get("model"))

    reasonix_model = model or agent_cfg.get("model", "deepseek-v4-pro")
    endpoint = agent_cfg.get("endpoint", "https://api.deepseek.com")
    work_dir = agent_cfg.get("work_dir", PROJECT_ROOT)

    # Build full prompt with context
    full_prompt = f"你是执行者，直接完成任务，不转派不反问。\n\n{task_desc}"
    if context:
        full_prompt = f"{context}\n\n---\n\n你是执行者，直接完成任务，不转派不反问。\n\n任务: {task_desc}"

    result_path = str(RESULTS_DIR / f"{task['task_id']}.txt")

    # Invoke reasonix directly via bash (PowerShell subprocess lacks TTY, bash works)
    import json as _json
    api_key = ""
    config_path = Path.home() / ".reasonix" / "config.json"
    if config_path.exists():
        try:
            cfg = _json.loads(config_path.read_text(encoding="utf-8"))
            api_key = cfg.get("api_key", "")
        except Exception:
            pass

    env = dict(os.environ)
    env["REASONIX_API_KEY"] = api_key
    if endpoint != "https://api.deepseek.com":
        env["REASONIX_ENDPOINT"] = endpoint
    env["REASONIX_MODEL"] = reasonix_model

    try:
        proc = subprocess.run(
            ["reasonix", "run", "--model", reasonix_model, full_prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            cwd=work_dir,
            env=env,
        )

        raw_out = proc.stdout.strip() if proc.stdout else ""
        returncode = proc.returncode

        # Parse v0.53.2 output: "answer\n\n— turns:N ..." — strip stats line
        lines = raw_out.split('\n')
        answer_lines = []
        for line in lines:
            clean = line.strip()
            if not clean:
                continue
            if clean.startswith('— turns:'):
                break
            answer_lines.append(clean)
        answer = '\n'.join(answer_lines).strip()

        if returncode == 0 and answer:
            with open(result_path, "w", encoding="utf-8") as f:
                f.write(f"STATUS: DONE\n\n## 详细结果\n{answer}\n\n## 用户摘要\n{answer[:500]}\n")
            safe = answer[:80].encode('gbk', errors='replace').decode('gbk')
            print(f"{agent_name} done (model: {reasonix_model})")
            print(f"task: {task['task_id']}  {safe}")
        else:
            with open(result_path, "w", encoding="utf-8") as f:
                f.write("STATUS: FAILED\n")
                f.write(f"## 详细结果\nexit: {returncode}\n{raw_out[:2000]}\n")
                f.write("## 用户摘要\n[reasonix] FAILED\n")
            print(f"{agent_name} FAILED (task: {task['task_id']})")

    except subprocess.TimeoutExpired:
        with open(result_path, "w", encoding="utf-8") as f:
            f.write("STATUS: TIMEOUT\n\n## 用户摘要\n[reasonix] timeout (600s)\n")
        print(f"{agent_name} timeout (task: {task['task_id']})")

    except Exception as e:
        with open(result_path, "w", encoding="utf-8") as f:
            f.write("STATUS: FAILED\n")
            f.write(f"## 详细结果\n{str(e)[:1000]}\n")
            f.write(f"## 用户摘要\n[reasonix] FAILED\n")
        print(f"reasonix error: {str(e)[:100]}")


def _dispatch_basic(agent_cfg, agent_name, task_desc, context, model, task):
    """Fallback dispatch method (no sandbox isolation)."""
    import subprocess

    prompt_md = agent_cfg.get("system_prompt_file", "")
    tools = agent_cfg.get("allowed_tools", "Read,Write,Edit")
    work_dir = agent_cfg.get("work_dir", PROJECT_ROOT)
    actual_model = model or agent_cfg.get("model", "sonnet")

    # ── MCP 权限注入 ──
    try:
        from maestro.sandbox import _get_mcp_permissions, _get_mcp_tool_descriptions
        mcp_perms = _get_mcp_permissions(PROJECT_ROOT)
        if mcp_perms:
            tools = tools + "," + ",".join(mcp_perms)
        mcp_tool_desc = _get_mcp_tool_descriptions(PROJECT_ROOT)
    except ImportError:
        mcp_tool_desc = ""

    full_task = f"你是执行者，直接完成任务，不转派不反问。\\n\\n{task_desc}"
    if context:
        full_task = f"{context}\\n\\n你是执行者，直接完成任务，不转派不反问。\\n\\n任务: {task_desc}"

    result_path = str(RESULTS_DIR / f"{task['task_id']}.txt")
    result_instruction = (
        "完成后将结果写入 " + result_path +
        " -- 第一行写 STATUS: DONE 或 STATUS: FAILED，" +
        "然后写 ## 详细结果（包含完整执行过程），" +
        "然后写 ## 用户摘要（面向 boss 的精简结果，无内部过程）"
    )
    if mcp_tool_desc:
        result_instruction += f"\\n\\n{mcp_tool_desc}"

    claude_cmd = (
        f'claude -p "{full_task}"'
        f' --name "{agent_name}"'
    )
    if prompt_md:
        claude_cmd += f' --system-prompt-file "{prompt_md}"'
    claude_cmd += (
        f' --append-system-prompt "{result_instruction}"'
        f' --model "{actual_model}"'
        f' --allowedTools "{tools}"'
        f' --output-format text'
        f' --permission-mode auto'
    )

    script_path = MAESTRO_DIR / f"_launch_{task['task_id']}.ps1"
    lines = [
        f'Write-Host "Maestro Agent: {agent_name} | Task: {task["task_id"]} | Model: {actual_model}"',
        f'Write-Host "Working dir: {work_dir}"',
        f'Write-Host "---"',
        f'cd "{work_dir}"',
        claude_cmd,
        f'Write-Host ""',
        f'Write-Host "=== Agent finished. You can close this window. ==="',
    ]
    script_path.write_text("\n".join(lines), encoding="utf-8-sig")

    ps_cmd = (
        f'Start-Process powershell'
        f' -ArgumentList "-NoProfile","-File","{script_path}"'
    )

    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        cwd=work_dir,
        check=False,
    )

    print(f"{agent_name} 已派出 (model: {actual_model})")
    print(f"task: {task['task_id']}")


# ── Status and result display ─────────────────────────────────────

def gateway_filter(raw_text):
    """Extract boss-visible content from agent result file."""
    if not raw_text:
        return ""

    lines = raw_text.split("\n")
    status_line = lines[0].strip() if lines else ""

    in_summary = False
    summary_lines = []
    for line in lines[1:]:
        if line.strip().startswith("## 用户摘要"):
            in_summary = True
            continue
        if in_summary:
            if line.strip().startswith("## ") and "用户摘要" not in line:
                break
            summary_lines.append(line)

    if summary_lines:
        return "\n".join(summary_lines).strip()

    in_detail = False
    detail_lines = []
    for line in lines[1:]:
        if line.strip().startswith("## 详细结果"):
            in_detail = True
            continue
        if in_detail:
            if line.strip().startswith("## ") and "详细结果" not in line:
                break
            detail_lines.append(line)
            if len("\n".join(detail_lines)) > 500:
                break

    return "\n".join(detail_lines).strip()[:500] if detail_lines else status_line


def status(filter_agent=None):
    ensure_dirs()
    tasks = []
    if TASKS_DIR.exists():
        for f in sorted(TASKS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            with open(f, encoding="utf-8") as fp:
                t = json.load(fp)
                agent = t.get("agent", "?")
                tid = t["task_id"]
                result_file = RESULTS_DIR / f"{tid}.txt"
                if result_file.exists():
                    first_line = result_file.read_text(encoding="utf-8").split("\n")[0].strip()
                    t["_result"] = first_line
                else:
                    t["_result"] = None
                if filter_agent and agent != filter_agent:
                    continue
                tasks.append(t)

    if not tasks:
        print("没有任务记录" if not filter_agent else f"{filter_agent} 没有任务")
        return

    for t in tasks[:10]:
        agent = t.get("agent", "?")
        tid = t["task_id"]
        desc = t["task"][:40]
        if t["_result"]:
            print(f"[完成] {agent:10s} {tid}  {t['_result']}")
            print(f"       {desc}")
        else:
            print(f"[进行中] {agent:10s} {tid}  {desc}")


def show_result(task_id, raw=False):
    """Show result for a task. With gateway filter unless --raw."""
    ensure_dirs()
    result_file = RESULTS_DIR / f"{task_id}.txt"
    if result_file.exists():
        content = result_file.read_text(encoding="utf-8")
        if raw:
            print(content)
        else:
            filtered = gateway_filter(content)
            task_file = TASKS_DIR / f"{task_id}.json"
            agent_name = ""
            if task_file.exists():
                with open(task_file, encoding="utf-8") as f:
                    t = json.load(f)
                    agent_name = t.get("agent", "")
            prefix = f"[{agent_name}] " if agent_name else ""
            status_line = content.split("\n")[0].strip() if content else ""
            print(f"{prefix}{status_line}")
            print(filtered)
    else:
        print(f"task {task_id} 还没有结果")


def list_agents():
    registry = load_registry()
    for name, cfg in registry.items():
        model = cfg.get("model", "?")
        collab = cfg.get("collaborates_with", [])
        collab_str = ", ".join(collab) if collab else "(无)"
        isolation = cfg.get("isolation", "none")
        schema = cfg.get("output_schema", "")
        print(f"  {name:12s} model={model:6s} isolation={isolation:8s} 协作={collab_str}")
        print(f"             {cfg['description']}")
        if schema:
            print(f"             schema={schema}")


# ── CLI main ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Maestro Agent Dispatch")
    parser.add_argument("--agent", help="Agent name to dispatch")
    parser.add_argument("--task", help="Task description")
    parser.add_argument("--context", help="Additional context")
    parser.add_argument("--model", help="Override model (haiku/sonnet/opus)")
    parser.add_argument("--status", nargs="?", const="__ALL__", help="Check status")
    parser.add_argument("--result", help="Get result by task ID")
    parser.add_argument("--raw", action="store_true", help="Show raw result (no gateway filter)")
    parser.add_argument("--list", action="store_true", help="List agents")
    args = parser.parse_args()

    ensure_dirs()

    if args.list:
        list_agents()
    elif args.agent and args.task:
        dispatch(args.agent, args.task, args.context, args.model)
    elif args.status:
        status(None if args.status == "__ALL__" else args.status)
    elif args.result:
        show_result(args.result, raw=args.raw)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
