#!/usr/bin/env python3
"""
transcript-parser.py — 从 Claude Code JSONL 提取真实 API token usage，写入 cost.db

真实数据源：~/.claude/projects/D--ai/<session-id>.jsonl
每条 assistant 消息包含 message.usage，含 input_tokens / output_tokens / cache_read_input_tokens。
优先使用 API 返回的精确值；无 usage 数据时用本地 DeepSeek tokenizer 估算（fallback）。

用法: python transcript-parser.py
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = os.environ.get("CLAUDE_PROJECT_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 确保 maestro 包可导入
_maestro_root = Path(__file__).resolve().parent.parent
if str(_maestro_root) not in sys.path:
    sys.path.insert(0, str(_maestro_root))

from maestro.token_counter import count, count_messages

# ── 配置 ────────────────────────────────────────────────────────────────
JSONL_DIR = Path(os.path.expandvars(r"%USERPROFILE%\.claude\projects\D--ai"))
COST_DB = Path(PROJECT_ROOT) / "maestro" / "cost.db"
STATE_FILE = Path(PROJECT_ROOT) / "maestro" / ".transcript-parser-state.json"
CHANNEL = "main_claude"

# 每百万 token 价格（USD）
# DeepSeek V4 官方定价（2026年5月31日起永久降价75%）
# 来源: https://www.infoworld.com/article/4176709/
# V4-Pro:  input $0.435/M (cache miss), $0.003625/M (cache hit), output $0.87/M
# V4-Flash: input $0.14/M  (cache miss), $0.0028/M  (cache hit), output $0.28/M
PRICING = {
    # (cache_miss_input, cache_hit_input, output)  per 1M tokens
    "deepseek-v4-pro":   (0.435, 0.003625, 0.87),
    "deepseek-v4-flash": (0.14,  0.0028,   0.28),
    "deepseek-v3":       (0.27,  0.27,     1.10),
    "deepseek-r1":       (0.55,  0.55,     2.19),
    "deepseek-chat":     (0.14,  0.14,     0.28),
}
# 旧格式兼容: 仅当 model key 不在 PRICING 中时使用（用于 cost-writer 等仍传二元组的场景）
PRICING_LEGACY: dict[str, tuple[float, float]] = {
    "deepseek-v4-pro": (0.435, 0.87),
    "deepseek-v3":     (0.27,  1.10),
    "deepseek-r1":     (0.55,  2.19),
    "deepseek-chat":   (0.14,  0.28),
}
DEFAULT_PRICE_IN  = 0.435
DEFAULT_PRICE_OUT = 0.87


# ── 数据库 ──────────────────────────────────────────────────────────────

def init_db() -> sqlite3.Connection:
    """初始化 cost.db。统一使用 cost_logs 表（与 cost_mw.py 兼容）。"""
    conn = sqlite3.connect(str(COST_DB))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cost_logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            time       TEXT    NOT NULL,
            channel    TEXT    NOT NULL DEFAULT '',
            model      TEXT    NOT NULL DEFAULT '',
            in_tokens  INTEGER NOT NULL DEFAULT 0,
            out_tokens INTEGER NOT NULL DEFAULT 0,
            cost_usd   REAL    NOT NULL DEFAULT 0.0,
            note       TEXT    DEFAULT ''
        )
    """)
    # 迁移: 添加 cache_read_input_tokens 列（如果不存在）
    try:
        conn.execute("ALTER TABLE cost_logs ADD COLUMN cache_read_input_tokens INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # 列已存在
    # 迁移: 添加 cache_creation_input_tokens 列（如果不存在）
    try:
        conn.execute("ALTER TABLE cost_logs ADD COLUMN cache_creation_input_tokens INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # 列已存在
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_cost_logs_time ON cost_logs(time)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_cost_logs_channel ON cost_logs(channel)
    """)
    # 迁移旧表数据（如果有的话且 cost_logs 为空时）
    try:
        existing = conn.execute("SELECT COUNT(*) FROM cost_logs").fetchone()[0]
        if existing == 0:
            old = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='usage_log'"
            ).fetchone()
            if old:
                conn.execute("DROP TABLE IF EXISTS usage_log")
                conn.commit()
    except Exception:
        pass
    conn.commit()
    return conn


def write_entry(
    conn: sqlite3.Connection,
    ts: str,
    model: str,
    in_tokens: int,
    out_tokens: int,
    note: str = "",
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> int:
    """写入一条使用记录。按 model 区分定价，cache hit 享受折扣。

    in_tokens: 缓存未命中 token（DeepSeek 语义：input_tokens 不含 cache hit）
    cache_read_tokens: 从缓存读取的 token（cache hit，享受 ~99% 折扣）
    cache_creation_tokens: 新写入缓存的 token（按全价计，属于 cache miss 子集）
    out_tokens: 输出 token

    计费公式: in_tokens * 全价 + cache_read * 折扣价 + out_tokens * 输出价
    注：DeepSeek response 中 input_tokens 不含 cache hit，两字段互斥，不能相减。
    """
    if model in PRICING:
        miss_price, hit_price, out_price = PRICING[model]
    else:
        # 回退：旧二元组格式或未知 model
        legacy = PRICING_LEGACY.get(model, (DEFAULT_PRICE_IN, DEFAULT_PRICE_OUT))
        miss_price, hit_price, out_price = legacy[0], legacy[0], legacy[1]

    cost = (
        (in_tokens / 1_000_000) * miss_price
        + (cache_read_tokens / 1_000_000) * hit_price
        + (out_tokens / 1_000_000) * out_price
    )

    cur = conn.execute(
        """INSERT INTO cost_logs (time, channel, model, in_tokens, out_tokens, cost_usd, note, cache_read_input_tokens, cache_creation_input_tokens)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (ts, CHANNEL, model, in_tokens, out_tokens, round(cost, 8), note, cache_read_tokens, cache_creation_tokens),
    )
    conn.commit()
    return cur.lastrowid


# ── 状态管理 ────────────────────────────────────────────────────────────

def load_state() -> dict:
    """返回 {file_mtime: last_processed_uuid}，记录每个文件的处理进度。"""
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state: dict) -> None:
    """保存处理进度。"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ── JSONL 解析 ──────────────────────────────────────────────────────────

def find_jsonl_files() -> list[Path]:
    """找到所有 JSONL session 文件，按修改时间排序。"""
    if not JSONL_DIR.is_dir():
        print(f"[ERROR] JSONL 目录不存在: {JSONL_DIR}", file=sys.stderr)
        return []
    candidates = sorted(
        JSONL_DIR.glob("*.jsonl"),
        key=lambda p: p.stat().st_mtime,
    )
    if not candidates:
        print(f"[ERROR] 未找到 .jsonl 文件于 {JSONL_DIR}", file=sys.stderr)
        return []
    return candidates


def _clean_assistant_content(content) -> str:
    """去除 assistant 内容中的 thinking 块，只保留可见文本。

    典型格式:
      [{'type': 'thinking', 'thinking': '...'}, {'type': 'text', 'text': '...'}]
    """
    if not content:
        return ""
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
                elif block.get("type") == "tool_use":
                    tool_name = block.get("name", "")
                    tool_input = str(block.get("input", ""))[:80]
                    parts.append(f"[Tool: {tool_name}] {tool_input}")
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content)


def _estimate_tokens_from_context(
    context_msgs: list[dict],
    model: str,
) -> tuple[int, int, int, int]:
    """用本地 tokenizer 估算 token 用量（无 API usage 时的 fallback）。

    Args:
        context_msgs: 到当前 assistant 为止的完整消息历史
        model: 模型名（保留参数，供未来扩展）

    Returns:
        (in_tokens, out_tokens, cache_read_tokens, cache_creation_tokens)
    """
    if not context_msgs:
        return 0, 0, 0, 0

    last_msg = context_msgs[-1]
    raw_content = last_msg.get("content", "")
    out_text = _clean_assistant_content(raw_content)
    out_tokens = count(out_text)

    input_msgs = context_msgs[:-1]
    input_clean: list[dict] = []
    for m in input_msgs:
        content = m.get("content", "")
        content = _clean_assistant_content(content)
        if content:
            input_clean.append({"role": m.get("role", "user"), "content": content})

    in_tokens = count_messages(input_clean) if input_clean else 0

    return in_tokens, out_tokens, 0, 0


def process_jsonl(filepath: Path, last_uuid: str | None) -> list[dict]:
    """解析一个 JSONL 文件，提取所有新 assistant 消息的 token 用量。

    - 有 usage 数据时用 API 返回的精确值
    - 缺 usage 数据时用本地 DeepSeek tokenizer 估算（fallback）
    - 估算条目在 note 中标记 "[estimated]"

    Args:
        filepath: JSONL 文件路径
        last_uuid: 上次处理到的 UUID，跳过此 UUID 及之前的消息

    Returns:
        list of {ts, model, in_tokens, out_tokens, cache_read_tokens,
                 cache_creation_tokens, uuid, note}
    """
    # 先读取全部行
    all_lines: list[dict] = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                all_lines.append(obj)
    except OSError as exc:
        print(f"[ERROR] 无法读取 JSONL 文件: {filepath} — {exc}", file=sys.stderr)
        return []

    context_buffer: list[dict] = []
    results: list[dict] = []
    found_last = last_uuid is None
    estimated_count = 0

    for obj in all_lines:
        obj_type = obj.get("type", "")
        msg = obj.get("message", {}) or {}

        # 维护上下文：记录所有有内容的消息（用于 fallback 估算）
        if obj_type in ("user", "assistant", "system", "tool") and msg.get("content"):
            context_buffer.append({
                "role": obj_type,
                "content": msg.get("content", ""),
            })

        if obj_type != "assistant":
            continue

        uuid = obj.get("uuid", "")
        if not uuid:
            continue

        # 去重
        if not found_last:
            if uuid == last_uuid:
                found_last = True
            continue

        usage = msg.get("usage")
        ts = obj.get("timestamp", "")
        model = msg.get("model", "")
        note = ""

        if usage:
            # ── 精确值：API 返回的 usage ──
            in_tokens = usage.get("input_tokens", 0)
            out_tokens = usage.get("output_tokens", 0)
            cache_read_tokens = usage.get("cache_read_input_tokens", 0)
            cache_creation_tokens = usage.get("cache_creation_input_tokens", 0)

            if in_tokens == 0 and out_tokens == 0 and cache_read_tokens == 0:
                continue
        else:
            # ── Fallback：本地 tokenizer 估算 ──
            in_tokens, out_tokens, cache_read_tokens, cache_creation_tokens = (
                _estimate_tokens_from_context(context_buffer, model)
            )
            if in_tokens == 0 and out_tokens == 0:
                continue
            note = "[estimated]"
            estimated_count += 1

        results.append({
            "ts": ts,
            "model": model,
            "in_tokens": in_tokens,
            "out_tokens": out_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cache_creation_tokens": cache_creation_tokens,
            "uuid": uuid,
            "note": note,
        })

    if estimated_count > 0:
        print(
            f"[INFO] {filepath.name}: {estimated_count} 条无 usage 数据，已用本地 tokenizer 估算",
            file=sys.stderr,
        )

    return results


# ── 主流程 ──────────────────────────────────────────────────────────────

def main() -> int:
    """入口：扫描 JSONL → 提取 real token → 写入 cost.db。"""
    files = find_jsonl_files()
    if not files:
        return 1

    state = load_state()
    conn = init_db()
    total_written = 0
    estimated_total = 0

    try:
        for filepath in files:
            file_key = str(filepath)
            last_uuid = state.get(file_key)

            results = process_jsonl(filepath, last_uuid)
            if not results:
                continue

            for r in results:
                write_entry(
                    conn,
                    ts=r["ts"],
                    model=r["model"],
                    in_tokens=r["in_tokens"],
                    out_tokens=r["out_tokens"],
                    cache_read_tokens=r.get("cache_read_tokens", 0),
                    cache_creation_tokens=r.get("cache_creation_tokens", 0),
                    note=r.get("note", ""),
                )
                total_written += 1
                if "[estimated]" in r.get("note", ""):
                    estimated_total += 1

            # 更新进度到本文件最后一条
            state[file_key] = results[-1]["uuid"]
    finally:
        conn.close()

    save_state(state)

    if total_written > 0:
        msg = f"[OK] 写入 {total_written} 条记录"
        if estimated_total > 0:
            msg += f"（其中 {estimated_total} 条为本地 tokenizer 估算）"
        print(msg, file=sys.stderr)
    else:
        print("[INFO] 无新数据", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
