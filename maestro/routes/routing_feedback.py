"""路由反馈 — 用户纠正路由错误，系统学习改进"""

import json
import time
from pathlib import Path

FEEDBACK_FILE = Path(__file__).resolve().parent.parent / "routing_feedback.jsonl"


def handle_feedback(handler, body):
    """POST /api/routing/feedback — 记录用户路由纠正"""
    task = body.get("task", "").strip()
    original_agent = body.get("original_agent", "").strip()
    corrected_agent = body.get("corrected_agent", "").strip()
    reason = body.get("reason", "").strip()

    if not task or not original_agent or not corrected_agent:
        handler.send_json(
            {"ok": False, "error": "缺少必填字段: task, original_agent, corrected_agent"}, 400
        )
        return True

    entry = {
        "ts": time.time(),
        "task": task,
        "original_agent": original_agent,
        "corrected_agent": corrected_agent,
        "reason": reason,
    }

    try:
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        handler.send_json({"ok": False, "error": f"写入失败: {e}"}, 500)
        return True

    handler.send_json({"ok": True, "recorded": True})
    return True


def get_feedback_stats():
    """返回反馈统计 — 哪些路由最常被纠正"""
    if not FEEDBACK_FILE.exists():
        return {"total": 0, "top_mistakes": []}

    entries = []
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except Exception:
        return {"total": 0, "top_mistakes": [], "error": "读取失败"}

    from collections import Counter

    pairs = Counter()
    for e in entries:
        key = f"{e['original_agent']} → {e['corrected_agent']}"
        pairs[key] += 1

    top = [{"pair": k, "count": v} for k, v in pairs.most_common(20)]

    return {"total": len(entries), "top_mistakes": top}


def handle_stats(handler, parsed):
    """GET /api/routing/feedback/stats — 反馈统计"""
    stats = get_feedback_stats()
    handler.send_json({"ok": True, **stats})
    return True
