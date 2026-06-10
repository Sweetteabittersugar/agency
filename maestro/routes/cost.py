"""费用查询路由"""
import logging
from urllib.parse import parse_qs
from pathlib import Path

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def handle_cost(handler, parsed):
    """GET /api/cost — 费用分析"""
    from maestro.web_cost import get_cost_analytics
    days = int(parse_qs(parsed.query).get("days", ["30"])[0])
    data = get_cost_analytics(PROJECT_ROOT, days)
    if data:
        handler.send_json(data)
    else:
        handler.send_json({
            "total": {"calls": 0, "cost": 0}, "today": {"calls": 0, "cost": 0},
            "by_date": [], "by_model": [], "by_agent": [], "by_project": [], "alerts": [],
        })
    return True


def handle_history(handler, parsed):
    """GET /api/cost/history — 费用历史趋势"""
    from maestro.web_cost import get_cost_analytics
    days = int(parse_qs(parsed.query).get("days", ["30"])[0])
    data = get_cost_analytics(PROJECT_ROOT, days)
    if data:
        handler.send_json({
            "by_date": data.get("by_date", []),
            "by_model": data.get("by_model", []),
            "cache": data.get("cache", {"read_tok": 0, "write_tok": 0, "saved": 0}),
        })
    else:
        handler.send_json({
            "by_date": [], "by_model": [],
            "cache": {"read_tok": 0, "write_tok": 0, "saved": 0},
        })
    return True


def handle_alerts(handler, parsed):
    """GET /api/cost/alerts — 费用告警"""
    from maestro.web_cost import get_cost_analytics
    data = get_cost_analytics(PROJECT_ROOT, 7)
    alerts = data.get("alerts", []) if data else []
    handler.send_json({"alerts": alerts})
    return True


def handle_summary(handler, parsed):
    """GET /api/cost/summary — 费用摘要（今日 + 本月汇总）"""
    from maestro.web_cost import get_cost_analytics
    import datetime
    data = get_cost_analytics(PROJECT_ROOT, 30)
    if not data:
        handler.send_json({
            "today": {"calls": 0, "cost": 0, "tokens": {"input": 0, "output": 0}},
            "this_month": {"calls": 0, "cost": 0, "tokens": {"input": 0, "output": 0}},
            "alerts": [],
            "model": "N/A",
            "updated": datetime.datetime.now().isoformat(),
        })
        return True

    # 筛选本月数据
    today_str = datetime.date.today().isoformat()
    this_month_start = datetime.date.today().replace(day=1).isoformat()
    by_date = data.get("by_date", [])
    today_entries = [d for d in by_date if d.get("date", "") == today_str]
    month_entries = [d for d in by_date if d.get("date", "") >= this_month_start]

    today_calls = sum(d.get("calls", 0) for d in today_entries)
    today_cost = sum(d.get("cost", 0) for d in today_entries)
    month_calls = sum(d.get("calls", 0) for d in month_entries)
    month_cost = sum(d.get("cost", 0) for d in month_entries)

    # 聚合本月 token 统计
    month_input_tok = sum(d.get("input_tokens", 0) for d in month_entries)
    month_output_tok = sum(d.get("output_tokens", 0) for d in month_entries)

    handler.send_json({
        "today": {
            "calls": today_calls,
            "cost": round(today_cost, 6),
            "tokens": {
                "input": sum(d.get("input_tokens", 0) for d in today_entries),
                "output": sum(d.get("output_tokens", 0) for d in today_entries),
            },
        },
        "this_month": {
            "calls": month_calls,
            "cost": round(month_cost, 6),
            "tokens": {"input": month_input_tok, "output": month_output_tok},
        },
        "alerts": data.get("alerts", []),
        "model": data.get("model", "N/A"),
        "updated": datetime.datetime.now().isoformat(),
    })
    return True
