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
