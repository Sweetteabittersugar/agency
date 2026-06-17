"""任务复杂度分类 + Plan 提取 + SubAgent 扫描

为路由引擎和编排器提供纯函数工具：
- classify_task_complexity: 评估任务复杂度 (trivial/simple/normal/complex)
- _extract_plan: 从 orchestrator 输出中提取 JSON 计划
- _scan_subagents: 扫描 session 下的子 Agent
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)


def classify_task_complexity(task: str) -> str:
    """评估任务复杂度，决定走哪条管线路径。

    Returns: 'trivial' | 'simple' | 'normal' | 'complex'
    """
    task_lower = task.lower()

    # 估算涉及文件数（显式数字 + 文件名模式匹配）
    file_patterns = re.findall(r"(\d+)\s*(?:个|处|份)?\s*(?:文件|file)", task)
    file_count = sum(int(n) for n in file_patterns)
    named_files = len(
        re.findall(r"\b[\w/-]+\.(?:py|js|ts|jsx|tsx|css|html|md|yaml|json|toml)\b", task)
    )
    total_files = max(file_count, named_files)

    readonly_kw = [
        "查找",
        "搜索",
        "grep",
        "查看",
        "读取",
        "检查",
        "查询",
        "列出",
        "显示",
        "list",
        "find",
        "search",
        "cat ",
        "ls ",
        "dir ",
        "帮我看",
        "看看",
        "怎么",
        "什么是",
        "在哪",
        "是什么",
    ]
    complex_kw = [
        "重构",
        "架构",
        "系统设计",
        "多模块",
        "数据库迁移",
        "安全审计",
        "性能优化",
        "全量",
        "整体",
        "refactor",
        "architecture",
        "migration",
        "完整的",
        "重新设计",
        "重写整个",
    ]
    write_kw = [
        "修改",
        "修复",
        "fix",
        "调整",
        "加个",
        "删掉",
        "改个",
        "tweak",
        "写一个",
        "添加",
        "增加",
        "新建",
        "创建",
        "实现",
        "开发",
        "add ",
        "create",
        "build",
        "implement",
    ]

    task_len = len(task)

    # complex: 5+文件 / 架构词 / 超长
    if total_files >= 5 or any(kw in task_lower for kw in complex_kw) or task_len > 400:
        return "complex"

    # trivial: 只读 + 0-1文件 + 不太长
    is_readonly = any(kw in task_lower for kw in readonly_kw)
    is_write = any(kw in task_lower for kw in write_kw)
    if is_readonly and not is_write and total_files <= 1 and task_len < 200:
        return "trivial"
    # 单文件小修 → 也归 trivial
    if total_files == 1 and task_len < 40 and not any(kw in task_lower for kw in complex_kw):
        return "trivial"

    # simple: 1-3文件 + 有写入意图
    if 1 <= total_files <= 3 and is_write:
        return "simple"
    # 短写入任务无明确文件 → simple
    if is_write and task_len < 120 and total_files == 0:
        return "simple"

    return "normal"


def _extract_plan(text: str) -> dict | None:
    """从 orchestrator 输出中提取 JSON 计划"""
    m = re.search(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
    if not m:
        m = re.search(r'\{[^{}]*"phases"\s*:\s*\[.*?\]\s*[^{}]*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1) if "```" in text else m.group(0))
        except Exception:
            pass
    return None


def _scan_subagents(proj_root: str, session_id: str) -> list:
    """扫描 session 下的子 Agent"""
    home = Path.home()
    slug = (
        proj_root.replace("\\", "/").rstrip("/").replace(":/", "--").replace("/", "-").lstrip("-")
    )
    subs_dir = home / ".claude" / "projects" / slug / session_id / "subagents"
    if not subs_dir.exists():
        return []
    agents = []
    for meta_file in sorted(subs_dir.glob("*.meta.json")):
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            agent_id = meta_file.stem.replace(".meta", "")
            jsonl_file = subs_dir / f"{agent_id}.jsonl"
            has_output = jsonl_file.exists() and jsonl_file.stat().st_size > 100
            agents.append(
                {
                    "id": agent_id,
                    "name": meta.get("name", agent_id[:12]),
                    "type": meta.get("agentType", ""),
                    "description": (meta.get("description", "") or "")[:120],
                    "hasOutput": has_output,
                    "project": Path(proj_root).name,
                }
            )
        except Exception:
            log.debug(f"Subagent scan failed for {proj_root}", exc_info=True)
    return agents
