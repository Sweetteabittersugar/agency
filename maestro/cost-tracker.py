#!/usr/bin/env python3
"""cost-tracker.py — AI API 费用追踪与实时看板

用法:
    python cost-tracker.py             今日汇总
    python cost-tracker.py --days 7    最近 N 天
    python cost-tracker.py --live      实时看板（5 秒刷新，Ctrl+C 退出）

纯 Python stdlib，只读 cost.db。
"""

import argparse
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = os.environ.get(
    "CLAUDE_PROJECT_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

COST_DB = Path(PROJECT_ROOT) / "maestro" / "cost.db"

# 告警阈值
DAILY_WARN_USD = 5.0  # 单日超 $5 告警
ENTRY_RED_USD = 0.50  # 单次超 $0.50 标红

# ── ANSI 颜色 ──────────────────────────────────────────────────────────────

RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def red(s: str) -> str:
    return f"{RED}{s}{RESET}"


def yellow(s: str) -> str:
    return f"{YELLOW}{s}{RESET}"


def bold(s: str) -> str:
    return f"{BOLD}{s}{RESET}"


# ── 数据库查询 ────────────────────────────────────────────────────────────


def get_conn() -> sqlite3.Connection:
    """只读连接，数据库不存在时优雅报错。"""
    if not COST_DB.exists():
        print(f"数据库不存在: {COST_DB}")
        sys.exit(1)
    conn = sqlite3.connect(f"file:{COST_DB}?mode=ro", uri=True)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection) -> bool:
    """检查 costs 表是否存在。"""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='costs'"
    ).fetchone()
    return row is not None


def query_range(conn: sqlite3.Connection, days: int | None) -> list[sqlite3.Row]:
    """查询指定天数内的记录；days=None 表示仅今日。"""
    if not _table_exists(conn):
        return []
    if days is None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT * FROM costs WHERE time >= ? AND time < ? ORDER BY time",
            (today, f"{today}T99"),
        ).fetchall()
    else:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        rows = conn.execute(
            "SELECT * FROM costs WHERE time >= ? ORDER BY time",
            (since,),
        ).fetchall()
    return rows


def query_all(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """查询全部记录。"""
    if not _table_exists(conn):
        return []
    return conn.execute("SELECT * FROM costs ORDER BY time").fetchall()


# ── 聚合计算 ──────────────────────────────────────────────────────────────


def aggregate(rows: list[sqlite3.Row]) -> dict:
    """按 agent 聚合费用、token 等。"""
    channels: dict[str, dict] = {}
    for r in rows:
        ch = r["agent"] or "unknown"
        if ch not in channels:
            channels[ch] = {
                "channel": ch,
                "cost": 0.0,
                "in_tokens": 0,
                "out_tokens": 0,
                "msg_count": 0,
                "records": 0,
            }
        channels[ch]["cost"] += r["cost_usd"]
        channels[ch]["in_tokens"] += r["in_tokens"]
        channels[ch]["out_tokens"] += r["out_tokens"]
        channels[ch]["msg_count"] += 1  # 每条记录 = 1 次 API 调用
        channels[ch]["records"] += 1

    total_cost = sum(v["cost"] for v in channels.values())
    total_in = sum(v["in_tokens"] for v in channels.values())
    total_out = sum(v["out_tokens"] for v in channels.values())
    total_msgs = sum(v["msg_count"] for v in channels.values())
    total_records = sum(v["records"] for v in channels.values())

    return {
        "channels": dict(sorted(channels.items())),
        "total_cost": total_cost,
        "total_in": total_in,
        "total_out": total_out,
        "total_msgs": total_msgs,
        "total_records": total_records,
    }


def daily_aggregate(rows: list[sqlite3.Row]) -> dict:
    """按日期聚合每日费用，返回 {date_str: total_cost_usd}。"""
    daily: dict[str, float] = {}
    for r in rows:
        day = r["time"][:10]  # YYYY-MM-DD
        daily[day] = daily.get(day, 0.0) + r["cost_usd"]
    return daily


def anomaly_check(rows: list[sqlite3.Row]) -> list[dict]:
    """检测异常：单日超 $5、单次超 $0.50。"""
    anomalies: list[dict] = []
    # 单次费用过高
    for r in rows:
        if r["cost_usd"] > ENTRY_RED_USD:
            anomalies.append(
                {
                    "type": "single",
                    "level": "red",
                    "id": r["id"],
                    "time": r["time"],
                    "channel": r["agent"] or "unknown",
                    "model": r["model"],
                    "cost": r["cost_usd"],
                    "msg": f"单次 ${r['cost_usd']:.4f} 超过 ${ENTRY_RED_USD:.2f}",
                }
            )
    # 单日超过阈值（在所有行中计算）
    daily = daily_aggregate(rows)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for day, cost in sorted(daily.items()):
        if cost > DAILY_WARN_USD:
            anomalies.append(
                {
                    "type": "daily",
                    "level": "warn" if day != today else "warn_active",
                    "date": day,
                    "cost": cost,
                    "msg": f"{day} 单日 ${cost:.4f} 超过 ${DAILY_WARN_USD:.2f}",
                }
            )
    return anomalies


# ── 渲染 ───────────────────────────────────────────────────────────────────


def format_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def format_cost(n: float) -> str:
    if n < 0.01:
        return f"${n:.6f}"
    return f"${n:.4f}"


CLEAR = "\033[2J\033[H"  # 清屏


def render_summary(rows: list[sqlite3.Row], days: int | None, live: bool = False):
    """渲染终端表格。"""
    if live:
        print(CLEAR, end="")

    agg = aggregate(rows)
    anomalies = anomaly_check(rows)

    # 表头
    period_label = "今日" if days is None else f"最近 {days} 天"
    effective_days = 1 if days is None else days
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{'=' * 62}")
    print(f"  AI API 费用追踪 · {period_label} · {now_str}".ljust(63))
    print(f"{'=' * 62}")

    # 通道明细
    print(f"  {'通道':<16} {'费用':>10} {'占比':>8} {'输入':>10} {'输出':>10} {'消息':>5}")
    print(f"{'-' * 62}")

    if agg["channels"]:
        for ch_name, ch_data in agg["channels"].items():
            pct = (ch_data["cost"] / agg["total_cost"] * 100) if agg["total_cost"] > 0 else 0
            line = (
                f"  {ch_name:<16} "
                f"{format_cost(ch_data['cost']):>10} "
                f"{pct:>7.1f}% "
                f"{format_tokens(ch_data['in_tokens']):>10} "
                f"{format_tokens(ch_data['out_tokens']):>10} "
                f"{ch_data['msg_count']:>5}"
            )
            print(line)
    else:
        print(f"  {'(无数据)':^60}")

    print(f"{'-' * 62}")
    # 汇总行
    daily_avg = agg["total_cost"] / effective_days
    est_monthly = daily_avg * 30

    print(
        f"  {'合计':<16} "
        f"{bold(format_cost(agg['total_cost'])):>10} "
        f"{'100.0%':>8} "
        f"{format_tokens(agg['total_in']):>10} "
        f"{format_tokens(agg['total_out']):>10} "
        f"{agg['total_msgs']:>5}"
    )
    print(f"{'-' * 62}")
    print(f"    日均: {format_cost(daily_avg):>10}   预估月费: {format_cost(est_monthly):>10}")
    print(f"{'=' * 62}")

    # 异常告警
    if anomalies:
        print(f"  {red('[!!] 异常告警')}".ljust(63))
        for a in anomalies:
            marker = red("X") if a["level"] in ("red", "warn_active") else yellow("!")
            print(f"   {marker} {a['msg']}".ljust(63))
    else:
        print(f"  {GREEN}[OK] 无异常{RESET}".ljust(63))

    print(f"{'=' * 62}")

    # 异常明细列表
    if anomalies:
        print()
        print(bold("异常明细:"))
        for a in anomalies:
            if a["level"] in ("red", "warn_active"):
                print(f"  {red('X')} {a['msg']}")
            else:
                print(f"  {yellow('!')} {a['msg']}")


# ── 主入口 ────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="AI API 费用追踪与实时看板",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="查询最近 N 天（不含则仅今日）",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="实时看板模式，每 5 秒刷新",
    )
    args = parser.parse_args()

    # --live 与 --days 互斥
    if args.live:
        try:
            _run_live()
        except KeyboardInterrupt:
            print(f"\n{GREEN}已退出。{RESET}")
        return

    conn = get_conn()
    try:
        rows = query_range(conn, args.days)
    finally:
        conn.close()

    render_summary(rows, args.days)


def _run_live():
    """实时看板主循环。"""
    print(CLEAR, end="")
    print("进入实时看板模式 (Ctrl+C 退出)...")
    time.sleep(1)

    while True:
        try:
            if not COST_DB.exists():
                print(red(f"等待数据库创建: {COST_DB}"))
                time.sleep(5)
                continue
            conn = get_conn()
            rows = query_all(conn)
            conn.close()
            render_summary(rows, days=None, live=True)
        except Exception as e:
            print(red(f"读取数据库出错: {e}"))
        time.sleep(5)


if __name__ == "__main__":
    main()
