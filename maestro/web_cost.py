"""Agency 费用记录与分析"""

import sqlite3
import threading
import logging
import time

log = logging.getLogger(__name__)
_cost_db_lock = threading.Lock()

DAILY_WARN = 5.0
ENTRY_RED = 0.50

# ── 数据库迁移管理 ──
# 版本号 → (迁移SQL列表, 说明)。新增列只需在最新版本追加条目并提升 CURRENT_SCHEMA。
# 启动时 _run_migrations() 自动补全缺失列，已存在的列被 sqlite3.OperationalError 跳过。

CURRENT_SCHEMA = 2

_MIGRATIONS = {
    1: [
        "ALTER TABLE costs ADD COLUMN date TEXT DEFAULT ''",
        "ALTER TABLE costs ADD COLUMN project TEXT DEFAULT ''",
        "ALTER TABLE costs ADD COLUMN task_preview TEXT DEFAULT ''",
        "ALTER TABLE costs ADD COLUMN agent TEXT DEFAULT ''",
        "ALTER TABLE costs ADD COLUMN cache_read_tokens INTEGER DEFAULT 0",
        "ALTER TABLE costs ADD COLUMN cache_write_tokens INTEGER DEFAULT 0",
        "ALTER TABLE costs ADD COLUMN cache_saved_usd REAL DEFAULT 0.0",
        "ALTER TABLE costs ADD COLUMN is_estimated INTEGER DEFAULT 0",
        "ALTER TABLE costs ADD COLUMN session_id TEXT DEFAULT ''",
        "ALTER TABLE costs ADD COLUMN tokens_from_api INTEGER DEFAULT 1",
    ],
}

_migrations_done = set()  # 已迁移的 db 路径（进程内缓存，避免每次 record_cost 都检查）


def _run_migrations(db_path: str):
    """按版本号顺序执行未应用的迁移。每个 db 只执行一次（进程生命周期内）。"""
    if db_path in _migrations_done:
        return
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        # 创建 schema_version 表（迁移记录）
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_version ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  version INTEGER NOT NULL,"
            "  applied_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),"
            "  description TEXT DEFAULT ''"
            ")"
        )
        # 查询当前版本（无记录 → 0）
        cur = conn.execute("SELECT MAX(version) FROM schema_version")
        row = cur.fetchone()
        current = row[0] if row and row[0] is not None else 0

        if current >= CURRENT_SCHEMA:
            _migrations_done.add(db_path)
            conn.close()
            return

        # 按序应用未执行的迁移
        import time as _time
        for ver in sorted(_MIGRATIONS.keys()):
            if ver <= current:
                continue
            for sql in _MIGRATIONS[ver]:
                try:
                    conn.execute(sql)
                except sqlite3.OperationalError:
                    pass  # 列已存在（旧 ALTER TABLE 方式的遗留列）
            conn.execute(
                "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                (ver, f"Auto-migrated at {_time.strftime('%Y-%m-%d %H:%M:%S')}"),
            )
            log.info(f"DB migration v{ver} applied → {db_path}")
        conn.commit()
        # 补全历史数据：旧记录的 date 可能为空
        conn.execute(
            "UPDATE costs SET date = substr(time, 1, 10) WHERE date = '' OR date IS NULL"
        )
        conn.commit()
    finally:
        conn.close()
    _migrations_done.add(db_path)


def record_cost(
    project_root,
    time_str,
    model,
    in_tokens,
    out_tokens,
    cost_usd,
    duration_s,
    agent="",
    project="",
    cache_read=0,
    cache_write=0,
    cache_saved=None,  # None → 自动根据 ModelPrice 计算
    is_estimated=False,
    session_id="",
    tokens_from_api=True,  # True=API返回值, False=客户端估算
):
    # 自动计算缓存节省金额（如果调用方没传或传了0）
    # cache_saved = cache_read * (input_price - cache_read_price)，表示因缓存而少付的输入费
    # cache_saved is None → 新调用方没传；cache_saved == 0 → 旧调用方传了占位值
    if (cache_saved is None or cache_saved == 0) and cache_read > 0:
        try:
            from maestro.models import get_model_price
            price = get_model_price(model)
            if price and price.input > price.cache_read:
                cache_saved = (cache_read / 1_000_000) * (price.input - price.cache_read)
            else:
                cache_saved = 0.0
        except Exception:
            cache_saved = 0.0
    elif cache_saved is None or cache_saved == 0:
        cache_saved = 0.0

    db = project_root / "maestro" / "cost.db"
    date_str = time_str[:10]
    with _cost_db_lock:
        conn = sqlite3.connect(str(db))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT, date TEXT, project TEXT, agent TEXT, model TEXT,
                in_tokens INTEGER, out_tokens INTEGER, cost_usd REAL,
                duration_s REAL, task_preview TEXT,
                cache_read_tokens INTEGER DEFAULT 0,
                cache_write_tokens INTEGER DEFAULT 0,
                cache_saved_usd REAL DEFAULT 0.0,
                is_estimated INTEGER DEFAULT 0,
                session_id TEXT DEFAULT '',
                tokens_from_api INTEGER DEFAULT 1
            )""")
            # 版本化迁移——只在新版本或首次运行时执行，不再每次 ALTER TABLE
            _run_migrations(str(db))
            conn.execute(
                "INSERT INTO costs (time, date, project, agent, model, in_tokens, out_tokens, cost_usd, duration_s, cache_read_tokens, cache_write_tokens, cache_saved_usd, is_estimated, session_id, tokens_from_api) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    time_str,
                    date_str,
                    project or "",
                    agent or "",
                    model,
                    in_tokens,
                    out_tokens,
                    round(cost_usd, 8),
                    duration_s,
                    cache_read,
                    cache_write,
                    round(cache_saved, 8),
                    1 if is_estimated else 0,
                    session_id or "",
                    1 if tokens_from_api else 0,
                ),
            )
            conn.commit()
        except Exception as e:
            log.warning(f"record_cost 写入失败: {e}")
        finally:
            conn.close()


def get_cost_analytics(project_root, days=30):
    """多维度费用分析"""
    db = project_root / "maestro" / "cost.db"
    if not db.exists():
        return None
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        conn.row_factory = sqlite3.Row
        has_date = any(c[1] == "date" for c in conn.execute("PRAGMA table_info(costs)").fetchall())
        date_col = "date" if has_date else "substr(time, 1, 10)"
        total = conn.execute(
            f"SELECT COUNT(*) as calls, COALESCE(SUM(cost_usd),0) as cost, COALESCE(SUM(in_tokens),0) as in_tok, COALESCE(SUM(out_tokens),0) as out_tok FROM costs WHERE {date_col} >= date('now','-'||?||' days')",
            (days,),
        ).fetchone()
        # 2026-06 修复：by_date 补上 token 聚合字段，供 handle_summary 和前端使用
        # 之前只返回 {date, calls, cost}，导致 handle_summary 的 input_tokens/output_tokens 始终为 0
        by_date = [
            dict(r)
            for r in conn.execute(
                f"SELECT {date_col} as date, COUNT(*) as calls, ROUND(COALESCE(SUM(cost_usd),0),6) as cost, COALESCE(SUM(in_tokens),0) as input_tokens, COALESCE(SUM(out_tokens),0) as output_tokens FROM costs WHERE {date_col} >= date('now','-'||?||' days') GROUP BY {date_col} ORDER BY date",
                (days,),
            )
        ]
        by_model = [
            dict(r)
            for r in conn.execute(
                f"SELECT model, COUNT(*) as calls, ROUND(COALESCE(SUM(cost_usd),0),6) as cost, SUM(in_tokens) as in_tok, SUM(out_tokens) as out_tok FROM costs WHERE {date_col} >= date('now','-'||?||' days') GROUP BY model ORDER BY cost DESC",
                (days,),
            )
        ]
        by_agent = [
            dict(r)
            for r in conn.execute(
                f"SELECT agent, COUNT(*) as calls, ROUND(COALESCE(SUM(cost_usd),0),6) as cost FROM costs WHERE {date_col} >= date('now','-'||?||' days') AND agent != '' GROUP BY agent ORDER BY cost DESC",
                (days,),
            )
        ]
        by_project = [
            dict(r)
            for r in conn.execute(
                f"SELECT project, COUNT(*) as calls, ROUND(COALESCE(SUM(cost_usd),0),6) as cost FROM costs WHERE {date_col} >= date('now','-'||?||' days') AND project != '' GROUP BY project ORDER BY cost DESC",
                (days,),
            )
        ]
        today = conn.execute(
            f"SELECT COUNT(*) as calls, COALESCE(SUM(cost_usd),0) as cost FROM costs WHERE {date_col} = date('now')"
        ).fetchone()
        try:
            cache = conn.execute(
                f"SELECT COALESCE(SUM(cache_read_tokens),0) as read_tok, COALESCE(SUM(cache_write_tokens),0) as write_tok, COALESCE(SUM(cache_saved_usd),0) as saved FROM costs WHERE {date_col} >= date('now','-'||?||' days')",
                (days,),
            ).fetchone()
        except sqlite3.OperationalError:
            cache = {"read_tok": 0, "write_tok": 0, "saved": 0}
        alerts = _build_alerts(conn) if has_date else []
        conn.close()
        return {
            "total": dict(total),
            "today": dict(today),
            "by_date": by_date,
            "by_model": by_model,
            "by_agent": by_agent,
            "by_project": by_project,
            "cache": dict(cache) if cache else {"read_tok": 0, "write_tok": 0, "saved": 0},
            "alerts": alerts,
        }
    except Exception as e:
        log.warning(f"get_cost_analytics 查询失败: {e}")
        conn.close()
        return None


def _build_alerts(conn):
    """生成费用告警列表"""
    alerts = []
    try:
        daily = conn.execute(
            "SELECT date, ROUND(COALESCE(SUM(cost_usd),0),6) as cost FROM costs GROUP BY date ORDER BY date DESC LIMIT 14"
        ).fetchall()
        for r in daily:
            if r["cost"] > DAILY_WARN:
                level = "warn" if r["cost"] < DAILY_WARN * 3 else "danger"
                alerts.append(
                    {
                        "level": level,
                        "type": "daily_budget",
                        "date": r["date"],
                        "cost": r["cost"],
                        "msg": f"{r['date']} 单日费用 ${r['cost']:.4f} 超过 ${DAILY_WARN:.2f} 告警线",
                    }
                )
        big = conn.execute(
            "SELECT id, time, model, cost_usd FROM costs WHERE cost_usd > ? AND date >= date('now','-7 days') ORDER BY cost_usd DESC LIMIT 10",
            (ENTRY_RED,),
        ).fetchall()
        for r in big:
            alerts.append(
                {
                    "level": "danger",
                    "type": "single_high",
                    "id": r["id"],
                    "time": r["time"],
                    "model": r["model"],
                    "cost": r["cost_usd"],
                    "msg": f"单次调用 ${r['cost_usd']:.4f} ({r['model']} @ {r['time']})",
                }
            )
    except Exception:
        pass
    return alerts


# ── 权限审计表（migration + 查询）──


def ensure_permission_audit_table(project_root):
    """确保 permission_audit 表存在（migration）"""
    db = project_root / "maestro" / "cost.db"
    with _cost_db_lock:
        conn = sqlite3.connect(str(db))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS permission_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    time TEXT NOT NULL,
                    tool TEXT NOT NULL,
                    args TEXT DEFAULT '',
                    decision TEXT NOT NULL,
                    risk TEXT DEFAULT '',
                    reason TEXT DEFAULT '',
                    user_choice TEXT DEFAULT ''
                )
            """)
            conn.commit()
        except Exception as e:
            log.warning(f"permission_audit 建表失败: {e}")
        finally:
            conn.close()


def log_permission_audit(project_root, tool, decision, args="", risk="", reason="", user_choice=""):
    """写入权限审计日志到 cost.db"""
    db = project_root / "maestro" / "cost.db"
    with _cost_db_lock:
        conn = sqlite3.connect(str(db))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            # 确保表存在
            conn.execute("""
                CREATE TABLE IF NOT EXISTS permission_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    time TEXT NOT NULL,
                    tool TEXT NOT NULL,
                    args TEXT DEFAULT '',
                    decision TEXT NOT NULL,
                    risk TEXT DEFAULT '',
                    reason TEXT DEFAULT '',
                    user_choice TEXT DEFAULT ''
                )
            """)
            conn.execute(
                "INSERT INTO permission_audit (time, tool, args, decision, risk, reason, user_choice) VALUES (?,?,?,?,?,?,?)",
                (
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                    tool,
                    args[:500] if args else "",
                    decision,
                    risk,
                    reason[:200] if reason else "",
                    user_choice[:100] if user_choice else "",
                ),
            )
            conn.commit()
        except Exception as e:
            log.warning(f"权限审计日志写入失败: {e}")
        finally:
            conn.close()


def get_permission_audit_log(project_root, limit=100, decision_filter=""):
    """查询权限审计日志"""
    db = project_root / "maestro" / "cost.db"
    if not db.exists():
        return []
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    try:
        has_table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='permission_audit'"
        ).fetchone()
        if not has_table:
            return []
        if decision_filter:
            rows = conn.execute(
                "SELECT * FROM permission_audit WHERE decision = ? ORDER BY id DESC LIMIT ?",
                (decision_filter, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM permission_audit ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        log.warning(f"权限审计日志查询失败: {e}")
        return []
    finally:
        conn.close()


def get_permission_stats(project_root):
    """获取权限统计数据"""
    db = project_root / "maestro" / "cost.db"
    if not db.exists():
        return {"total": 0, "allowed": 0, "denied": 0, "asked": 0}
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        has_table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='permission_audit'"
        ).fetchone()
        if not has_table:
            return {"total": 0, "allowed": 0, "denied": 0, "asked": 0}
        total = conn.execute("SELECT COUNT(*) as n FROM permission_audit").fetchone()[0]
        allowed = conn.execute(
            "SELECT COUNT(*) FROM permission_audit WHERE decision='allow'"
        ).fetchone()[0]
        denied = conn.execute(
            "SELECT COUNT(*) FROM permission_audit WHERE decision='deny'"
        ).fetchone()[0]
        asked = conn.execute(
            "SELECT COUNT(*) FROM permission_audit WHERE decision='ask'"
        ).fetchone()[0]
        return {"total": total, "allowed": allowed, "denied": denied, "asked": asked}
    except Exception:
        return {"total": 0, "allowed": 0, "denied": 0, "asked": 0}
    finally:
        conn.close()
