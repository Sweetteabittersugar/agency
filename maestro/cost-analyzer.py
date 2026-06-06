#!/usr/bin/env python3
"""
cost-analyzer.py — 每日 22:00 运行，分析 cost.db 当日数据并输出优化建议。

纯 Python stdlib 实现。
用法: python cost-analyzer.py

输出:
  - stdout: 完整分析报告
  - <工作日志>/<当日>.md: 追加 ## 成本分析 小节
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = os.environ.get("CLAUDE_PROJECT_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── 配置 ────────────────────────────────────────────────────────────────
COST_DB = Path(PROJECT_ROOT) / "maestro" / "cost.db"
WORK_LOG_DIR = Path(PROJECT_ROOT) / "工作日志"
AGENTS_JSON = Path(PROJECT_ROOT) / "maestro" / "agents.json"
TASK_BOARD = Path(PROJECT_ROOT) / "maestro" / "task-board.json"

# Agent → 预期模型（从 agents.json 提取的权威映射）
AGENT_MODEL_MAP: dict[str, str] = {}
# 模型层次：越靠前越便宜
MODEL_TIER = ["haiku", "sonnet", "opus", "deepseek-v4-pro", "deepseek-v4-flash"]

# ── 定价统一从 models.py 导入 ──
def _model_price(model: str) -> tuple[float, float]:
    """返回模型的 (input_price_per_1M, output_price_per_1M)。"""
    from maestro.models import PRICING
    if model in PRICING:
        return PRICING[model]
    # 模糊匹配
    for key, price in PRICING.items():
        if key in model.lower() or model.lower() in key:
            return price
    # 未知模型按 sonnet 算
    return (3.00, 15.00)


def _load_agent_model_map() -> dict[str, str]:
    """从 agents.json 加载 agent→model 映射。"""
    if not AGENTS_JSON.exists():
        return {}
    try:
        data = json.loads(AGENTS_JSON.read_text(encoding="utf-8"))
        return {
            name: cfg.get("model", "unknown")
            for name, cfg in data.items()
        }
    except (json.JSONDecodeError, OSError):
        return {}


# ── 数据查询 ────────────────────────────────────────────────────────────

def query_today(conn: sqlite3.Connection, today_str: str) -> list[dict]:
    """查询 costs 中今日的所有记录。"""
    rows: list[dict] = []

    # costs 表
    try:
        cur = conn.execute(
            """SELECT time, agent, model, in_tokens, out_tokens, cost_usd
               FROM costs
               WHERE time >= ? AND time < ?
               ORDER BY time""",
            (today_str, _next_day(today_str)),
        )
        for r in cur:
            rows.append({
                "source": "costs",
                "time": r[0],
                "channel": r[1] or "unknown",
                "model": r[2] or "unknown",
                "in_tokens": r[3],
                "out_tokens": r[4],
                "cost_usd": r[5],
                "msg_count": 1,  # 每条记录 = 1 次 API 调用
            })
    except sqlite3.OperationalError:
        pass

    return rows


def query_day(conn: sqlite3.Connection, day_str: str) -> list[dict]:
    """查询指定日期（YYYY-MM-DD）的所有记录。"""
    rows: list[dict] = []

    try:
        cur = conn.execute(
            """SELECT time, agent, model, in_tokens, out_tokens, cost_usd
               FROM costs
               WHERE time >= ? AND time < ?
               ORDER BY time""",
            (day_str, _next_day(day_str)),
        )
        for r in cur:
            row = {
                "source": "costs",
                "time": r[0],
                "channel": r[1] or "unknown",
                "model": r[2] or "unknown",
                "in_tokens": r[3],
                "out_tokens": r[4],
                "cost_usd": r[5],
                "msg_count": 1,  # 每条记录 = 1 次 API 调用
            }
            rows.append(row)
    except sqlite3.OperationalError:
        pass

    return rows


def _next_day(day_str: str) -> str:
    """返回 day_str 的下一天（YYYY-MM-DD）。"""
    dt = datetime.strptime(day_str, "%Y-%m-%d")
    return (dt + timedelta(days=1)).strftime("%Y-%m-%d")


# ── 分析函数 ────────────────────────────────────────────────────────────

def analyze_channel_distribution(rows: list[dict]) -> list[str]:
    """分析各通道 token 占比是否合理。"""
    lines: list[str] = []

    # 按 channel 聚合
    channel_stats: dict[str, dict] = {}
    for r in rows:
        ch = r["channel"] or "unknown"
        if ch not in channel_stats:
            channel_stats[ch] = {"in_tokens": 0, "out_tokens": 0, "cost_usd": 0.0, "count": 0}
        channel_stats[ch]["in_tokens"] += r["in_tokens"]
        channel_stats[ch]["out_tokens"] += r["out_tokens"]
        channel_stats[ch]["cost_usd"] += r["cost_usd"]
        channel_stats[ch]["count"] += r["msg_count"]

    total_cost = sum(s["cost_usd"] for s in channel_stats.values())
    total_in = sum(s["in_tokens"] for s in channel_stats.values())
    total_out = sum(s["out_tokens"] for s in channel_stats.values())

    if total_cost == 0:
        lines.append("- 今日无费用记录，通道占比分析跳过。")
        return lines

    lines.append("### 通道费用分布")
    lines.append("")
    lines.append("| 通道 | 调用次数 | 入向Token | 出向Token | 费用(USD) | 占比 |")
    lines.append("|------|----------|-----------|-----------|-----------|------|")

    for ch, stats in sorted(channel_stats.items(), key=lambda x: x[1]["cost_usd"], reverse=True):
        pct = stats["cost_usd"] / total_cost * 100
        lines.append(
            f"| {ch} | {stats['count']} | {stats['in_tokens']:,} | "
            f"{stats['out_tokens']:,} | ${stats['cost_usd']:.4f} | {pct:.1f}% |"
        )

    lines.append("")
    lines.append(f"**总计**: in={total_in:,}t  out={total_out:,}t  cost=${total_cost:.4f}")
    lines.append("")

    # 检查主 Claude token 是否偏高
    mc = channel_stats.get("main_claude", {})
    if mc:
        mc_pct = mc["cost_usd"] / total_cost * 100 if total_cost else 0
        if mc_pct > 60:
            lines.append(f"**警告**: 主 Claude 通道占{mc_pct:.0f}%费用，偏高。建议将更多长任务派给 reasonix/worker agent，减少主会话上下文膨胀。")
        lines.append("")

    return lines


def analyze_reasonix_anomaly(conn: sqlite3.Connection, today_str: str,
                             today_rows: list[dict]) -> list[str]:
    """检测 reasonix 单次平均 token 是否超过昨日的 2 倍。"""
    lines: list[str] = []

    # 今日 reasonix 相关
    today_reasonix = [r for r in today_rows if
                      r["channel"] == "reasonix" or "deepseek" in r.get("model", "").lower()]
    if not today_reasonix:
        return lines

    today_count = sum(r["msg_count"] for r in today_reasonix)
    today_total = sum(r["in_tokens"] + r["out_tokens"] for r in today_reasonix)
    today_avg = today_total / today_count if today_count else 0

    # 昨日 reasonix 相关
    yesterday_str = (datetime.strptime(today_str, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_rows = query_day(conn, yesterday_str)
    yesterday_reasonix = [r for r in yesterday_rows if
                          r["channel"] == "reasonix" or "deepseek" in r.get("model", "").lower()]

    yesterday_count = sum(r["msg_count"] for r in yesterday_reasonix)
    yesterday_total = sum(r["in_tokens"] + r["out_tokens"] for r in yesterday_reasonix)
    yesterday_avg = yesterday_total / yesterday_count if yesterday_count else 0

    lines.append("### Reasonix 异常检测")
    lines.append("")
    lines.append(f"- 今日: {today_count} 次调用, 平均 {today_avg:,.0f} tokens/次")
    lines.append(f"- 昨日: {yesterday_count} 次调用, 平均 {yesterday_avg:,.0f} tokens/次")

    if yesterday_avg > 0 and today_avg > yesterday_avg * 2:
        ratio = today_avg / yesterday_avg
        lines.append(f"")
        lines.append(f"**异常**: 今日 reasonix 单次平均 token ({today_avg:,.0f}) 是昨日 ({yesterday_avg:,.0f}) "
                     f"的 {ratio:.1f} 倍，超过 2 倍阈值。")
        lines.append(f"  - 建议: 检查是否有任务携带了过多上下文；考虑拆分大任务为多个小任务；启用 deepseek-v4-flash 处理简单查询。")
    else:
        lines.append(f"- 单次平均 token 在正常范围内。")

    lines.append("")
    return lines


def analyze_model_misuse(conn: sqlite3.Connection, today_str: str,
                         today_rows: list[dict]) -> list[str]:
    """检测是否简单任务用了 sonnet 而非 haiku。"""
    lines: list[str] = []

    # 按 channel 聚合 model 使用
    channel_model_usage: dict[str, dict[str, dict]] = {}
    for r in today_rows:
        ch = r["channel"] or "unknown"
        model = r["model"] or "unknown"
        if ch not in channel_model_usage:
            channel_model_usage[ch] = {}
        if model not in channel_model_usage[ch]:
            channel_model_usage[ch][model] = {"count": 0, "cost_usd": 0.0, "total_tokens": 0}
        channel_model_usage[ch][model]["count"] += r["msg_count"]
        channel_model_usage[ch][model]["cost_usd"] += r["cost_usd"]
        channel_model_usage[ch][model]["total_tokens"] += r["in_tokens"] + r["out_tokens"]

    lines.append("### 模型使用检测")
    lines.append("")

    # 检查 explorer / test 是否用了 sonnet
    for ch in ["explorer", "test"]:
        if ch in channel_model_usage:
            for model, stats in channel_model_usage[ch].items():
                if "sonnet" in model.lower() or "opus" in model.lower():
                    lines.append(f"**注意**: {ch} 通道使用了 {model} ({stats['count']} 次)，"
                                 f"应使用 haiku。累计费用 ${stats['cost_usd']:.4f}。")
                    lines.append(f"  - 建议: 检查 dispatch 时 model 参数是否被错误覆盖。")

    # 检查是否有小而简单的调用用了昂贵模型
    for ch, models in channel_model_usage.items():
        for model, stats in models.items():
            if "opus" in model.lower() and stats["total_tokens"] and stats["count"]:
                avg = stats["total_tokens"] / stats["count"]
                if avg < 2000:
                    lines.append(f"**注意**: {ch} 用 {model} 处理了 {stats['count']} 次小任务"
                                 f"(平均 {avg:,.0f} tokens/次)，费用 ${stats['cost_usd']:.4f}。")
                    lines.append(f"  - 建议: <2000 token 的任务应降级到 haiku 或 sonnet。")

    if not any("注意" in l or "异常" in l for l in lines[1:]):
        lines.append("- 模型使用正常，未发现 haiku→sonnet 误配。")

    lines.append("")
    return lines


def analyze_main_claude_tokens(today_rows: list[dict]) -> list[str]:
    """分析主 Claude 会话 token 是否偏高。"""
    lines: list[str] = []
    lines.append("### 主会话 Token 分析")
    lines.append("")

    mc_rows = [r for r in today_rows if r["channel"] == "main_claude"]
    if not mc_rows:
        lines.append("- 今日无 main_claude 记录。")
        lines.append("")
        return lines

    total_in = sum(r["in_tokens"] for r in mc_rows)
    total_out = sum(r["out_tokens"] for r in mc_rows)
    total_cost = sum(r["cost_usd"] for r in mc_rows)
    total_msgs = sum(r["msg_count"] for r in mc_rows)

    lines.append(f"- 入向 token: {total_in:,}")
    lines.append(f"- 出向 token: {total_out:,}")
    lines.append(f"- 消息数: {total_msgs}")
    lines.append(f"- 费用: ${total_cost:.4f}")
    lines.append("")

    if total_in > 100_000:
        lines.append("**警告**: 主会话入向 token 超过 100K，上下文可能膨胀。")
        lines.append("  - 建议: ")
        lines.append("    1. 将长时间会话拆分为多个专注任务，派给 agent 执行")
        lines.append("    2. 启用上下文压缩（当前阈值 300K，可降低到 200K）")
        lines.append("    3. 减少在主会话中阅读大文件，改用 explorer agent")
        lines.append("    4. 使用 /compact 命令手动压缩当前会话")
        lines.append("")
    elif total_in > 50_000:
        lines.append("**提醒**: 主会话入向 token 超过 50K，建议关注上下文增长趋势。")
        lines.append("")

    return lines


def analyze_task_board_efficiency(today_str: str) -> list[str]:
    """从 task-board 交叉分析调度效率。"""
    lines: list[str] = []
    lines.append("### 任务调度效率")
    lines.append("")

    if not TASK_BOARD.exists():
        lines.append("- task-board.json 不存在，跳过。")
        lines.append("")
        return lines

    try:
        data = json.loads(TASK_BOARD.read_text(encoding="utf-8"))
        tasks = data.get("tasks", [])
    except (json.JSONDecodeError, OSError):
        lines.append("- 无法读取 task-board.json，跳过。")
        lines.append("")
        return lines

    # 今日完成/失败的任务
    today_tasks = []
    for t in tasks:
        created = t.get("created_at", "")
        if created.startswith(today_str):
            today_tasks.append(t)

    if not today_tasks:
        lines.append("- 今日无新任务记录。")
        lines.append("")
        return lines

    # 按 agent 统计
    agent_stats: dict[str, dict] = {}
    for t in today_tasks:
        agent = t.get("agent", "unknown")
        if agent not in agent_stats:
            agent_stats[agent] = {"total": 0, "done": 0, "failed": 0, "dispatched": 0}
        agent_stats[agent]["total"] += 1
        status = t.get("status", "dispatched")
        if status == "done":
            agent_stats[agent]["done"] += 1
        elif status == "failed":
            agent_stats[agent]["failed"] += 1
        else:
            agent_stats[agent]["dispatched"] += 1

    # 检查 simple 任务是否用了昂贵 agent
    for agent, stats in agent_stats.items():
        expected_model = AGENT_MODEL_MAP.get(agent, "unknown")
        if expected_model in ("sonnet", "opus") and stats["total"] >= 3:
            # 检查是否有大量 dispatched 未完成 → 可能是僵尸任务
            if stats["dispatched"] > stats["done"] * 2:
                lines.append(f"**注意**: {agent} ({expected_model}) 有 {stats['dispatched']} 个未完成任务，"
                             f"仅 {stats['done']} 个完成。可能是僵尸任务浪费资源。")
                lines.append(f"  - 建议: 取消超时任务，清理 task-board 僵尸记录。")

    lines.append("")
    return lines


# ── 建议生成 ────────────────────────────────────────────────────────────

def generate_recommendations(
    today_rows: list[dict],
    today_str: str,
    conn: sqlite3.Connection,
) -> list[str]:
    """综合所有分析结果，生成优化建议。"""
    lines: list[str] = []

    # 汇总
    total_cost = sum(r["cost_usd"] for r in today_rows)
    total_tokens = sum(r["in_tokens"] + r["out_tokens"] for r in today_rows)

    lines.append(f"## 成本分析 (private)")
    lines.append("")
    lines.append(f"**日期**: {today_str}")
    lines.append(f"**当日总费用**: ${total_cost:.4f}")
    lines.append(f"**当日总 Token**: {total_tokens:,}")
    lines.append("")

    # 1. 通道分布
    lines.extend(analyze_channel_distribution(today_rows))

    # 2. Reasonix 异常
    lines.extend(analyze_reasonix_anomaly(conn, today_str, today_rows))

    # 3. 模型误用
    lines.extend(analyze_model_misuse(conn, today_str, today_rows))

    # 4. 主会话 token
    lines.extend(analyze_main_claude_tokens(today_rows))

    # 5. 任务效率
    lines.extend(analyze_task_board_efficiency(today_str))

    # ── 综合建议 ──
    lines.append("### 综合优化建议")
    lines.append("")

    recommendations: list[tuple[int, str]] = []

    # 基于通道分布的建议
    channel_costs: dict[str, float] = {}
    for r in today_rows:
        ch = r["channel"] or "unknown"
        channel_costs[ch] = channel_costs.get(ch, 0.0) + r["cost_usd"]

    mc_pct = channel_costs.get("main_claude", 0) / total_cost * 100 if total_cost else 0
    if mc_pct > 50:
        recommendations.append((1, "**切换模型**: 将主会话长任务委托给 reasonix agent，减少 main_claude 上下文膨胀"))

    # 基于模型使用的建议
    sonnet_overuse = False
    for r in today_rows:
        ch = r["channel"] or ""
        model = r.get("model", "") or ""
        if ch in ("explorer", "test") and "sonnet" in model.lower():
            sonnet_overuse = True
            break
    if sonnet_overuse:
        recommendations.append((2, "**降级任务**: explorer/test 应强制使用 haiku，确认 dispatch 未错误覆盖 model 参数"))

    # 上下文压缩建议
    mc_in = sum(r["in_tokens"] for r in today_rows if r["channel"] == "main_claude")
    if mc_in > 80_000:
        recommendations.append((3, "**压缩上下文**: 主会话入向 >80K，建议降低上下文压缩阈值至 200K 或手动 /compact"))

    # 任务拆分建议
    reasonix_rows = [r for r in today_rows if r["channel"] == "reasonix" or "deepseek" in r.get("model", "").lower()]
    if reasonix_rows:
        avg_tokens = sum(r["in_tokens"] + r["out_tokens"] for r in reasonix_rows) / sum(r["msg_count"] for r in reasonix_rows)
        if avg_tokens > 50_000:
            recommendations.append((4, "**拆分大任务**: reasonix 单次超 50K tokens，建议拆分复杂任务为多步骤小任务"))

    if not recommendations:
        recommendations.append((0, "今日成本结构正常，无需调整。继续保持当前策略。"))

    recommendations.sort(key=lambda x: x[0])
    for _, rec in recommendations:
        lines.append(f"- {rec}")

    lines.append("")
    return lines


# ── 文件输出 ────────────────────────────────────────────────────────────

def append_to_worklog(today_str: str, report_lines: list[str]) -> None:
    """追加分析结果到当日工作日志。"""
    log_file = WORK_LOG_DIR / f"{today_str}.md"

    # 确保目录存在
    WORK_LOG_DIR.mkdir(parents=True, exist_ok=True)

    existing = ""
    if log_file.exists():
        existing = log_file.read_text(encoding="utf-8")

    # 检查是否已有成本分析段落，避免重复追加
    if "## 成本分析" in existing:
        # 替换已有段落
        idx = existing.find("## 成本分析")
        # 找到下一个 ## 或文件末尾
        next_section = existing.find("\n## ", idx + 1)
        if next_section == -1:
            next_section = len(existing)
        existing = existing[:idx] + existing[next_section:]
        # 去除尾部多余空行
        existing = existing.rstrip() + "\n\n"

    new_content = existing.rstrip()
    if new_content:
        new_content += "\n\n"
    new_content += "\n".join(report_lines)
    new_content += "\n"

    log_file.write_text(new_content, encoding="utf-8")

    print(f"[cost-analyzer] 已追加至 {log_file}", file=sys.stderr)


# ── 入口 ────────────────────────────────────────────────────────────────

def main() -> int:
    global AGENT_MODEL_MAP
    AGENT_MODEL_MAP = _load_agent_model_map()

    # 确定"今日"——允许命令行参数覆盖
    if len(sys.argv) > 1:
        today_str = sys.argv[1]
    else:
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 连接数据库
    if not COST_DB.exists():
        print(f"[cost-analyzer] cost.db 不存在: {COST_DB}", file=sys.stderr)
        # 即使数据库不存在，也生成一份空报告
        report = [
            f"## 成本分析 (private)",
            "",
            f"**日期**: {today_str}",
            "**状态**: cost.db 不存在，无数据可分析。",
            "",
        ]
        print("\n".join(report))
        append_to_worklog(today_str, report)
        return 0

    conn = sqlite3.connect(str(COST_DB))
    try:
        today_rows = query_today(conn, today_str)

        if not today_rows:
            report = [
                f"## 成本分析 (private)",
                "",
                f"**日期**: {today_str}",
                "**状态**: 今日无记录。",
                "",
            ]
            print("\n".join(report))
            append_to_worklog(today_str, report)
            return 0

        report_lines = generate_recommendations(today_rows, today_str, conn)
    finally:
        conn.close()

    # 输出到 stdout
    report_text = "\n".join(report_lines)
    print(report_text)

    # 追加到工作日志
    append_to_worklog(today_str, report_lines)

    return 0


if __name__ == "__main__":
    sys.exit(main())
