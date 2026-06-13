"""
Hook HTTP 回调接收器
Claude Code hooks 配置为 POST http://127.0.0.1:8800/api/hooks/:event
本模块处理这些回调并推送到 HarnessBus
"""

import json
import time
from .watcher import bus


# 风险关键词评分 — 工具调用参数中包含这些词 → 风险升高
RISK_KEYWORDS = {
    "rm ": 8,
    "rm -rf": 10,
    "delete": 6,
    "DROP": 10,
    "DROP TABLE": 10,
    "format": 9,
    "mkfs": 10,
    "chmod 777": 7,
    "sudo": 8,
    "eval": 8,
    "exec(": 8,
    "subprocess": 5,
    "shell=True": 7,
    "--force": 6,
    "git push --force": 10,
    "git reset --hard": 7,
    "truncate": 6,
    "shutdown": 9,
    "reboot": 9,
    "> /dev/sda": 10,
    "dd if=": 10,
    "wget": 4,
    "curl": 4,
    "pip install": 4,
    "npm install -g": 5,
}


def calc_risk(tool_name: str, tool_input: dict) -> dict:
    """计算工具调用的风险评分 (0-10)"""
    score = 0
    reasons = []

    # 基础风险：工具类型
    tool_risk = {
        "Bash": 4,
        "Write": 3,
        "Edit": 3,
        "TaskCreate": 2,
        "NotebookEdit": 2,
        "Agent": 3,
        "SendMessage": 2,
        "Read": 0,
        "Grep": 0,
        "Glob": 0,
        "WebSearch": 1,
        "WebFetch": 1,
    }
    score += tool_risk.get(tool_name, 2)

    # 参数关键词匹配
    if tool_input:
        input_str = (
            json.dumps(tool_input).lower()
            if isinstance(tool_input, dict)
            else str(tool_input).lower()
        )
        for kw, risk in RISK_KEYWORDS.items():
            if kw.lower() in input_str:
                score = max(score, risk)
                reasons.append(kw)

    level = "low" if score <= 3 else ("medium" if score <= 6 else "high")
    return {"score": min(score, 10), "level": level, "reasons": reasons}


def handle_hook_callback(event: str, body: dict) -> dict:
    """
    处理 Claude Code hook 回调
    返回供 Claude Code 使用的决策 JSON
    """
    tool_name = body.get("tool_name", body.get("tool", "unknown"))
    tool_input = body.get("tool_input", body.get("input", {}))
    hook_event = event.lstrip("/")  # /api/hooks/PermissionRequest → PermissionRequest

    # 权限请求 → 需要客户端决策
    if "Permission" in hook_event or "permission" in hook_event:
        risk = calc_risk(tool_name, tool_input)

        event_data = {
            "tool_name": tool_name,
            "tool_input": str(tool_input)[:500],
            "risk": risk,
            "timestamp": time.strftime("%H:%M:%S"),
            "hook_event": hook_event,
        }
        bus.broadcast("permission_request", event_data)

        # 低风险自动放行，中高风险等待前端决策（超时默认 deny）
        if risk["level"] == "low":
            bus.broadcast(
                "permission_decision",
                {"tool_name": tool_name, "decision": "allow", "reason": "低风险自动放行"},
            )
            return {"decision": "allow"}

        # 中高风险 → 前端弹窗，这里默认返回 "ask"
        return {"decision": "ask", "risk": risk}

    # 工具使用通知
    if "ToolUse" in hook_event:
        risk = calc_risk(tool_name, tool_input)
        bus.broadcast(
            "tool_use",
            {
                "tool_name": tool_name,
                "tool_input": str(tool_input)[:300],
                "timestamp": time.strftime("%H:%M:%S"),
                "risk": risk,
            },
        )

    # PreCompaction / PostCompaction
    if "Compact" in hook_event:
        bus.broadcast(
            "compaction",
            {
                "event": hook_event,
                "timestamp": time.strftime("%H:%M:%S"),
            },
        )

    # 生命周期事件
    if hook_event in ("SessionStart", "Stop", "SubagentStart", "SubagentStop"):
        bus.broadcast(
            "lifecycle",
            {
                "event": hook_event,
                "timestamp": time.strftime("%H:%M:%S"),
                "agent_name": body.get("name", body.get("agent_name", "")),
            },
        )

    return {"decision": "allow"}
