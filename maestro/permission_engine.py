#!/usr/bin/env python3
"""
PermissionEngine — 三级权限审批引擎

三级分类:
  - allow:  安全操作，直接放行
  - ask:    需确认操作，24h 内同类操作只问一次
  - deny:   危险操作，始终拒绝

信任模式（由前端传入 trust_mode）:
  - cautious:  默认，所有需确认操作都询问
  - normal:    同类操作只问一次（24h 内记住）
  - trusted:   仅拦截高危操作（ALWAYS_DENY）
"""

import fnmatch
import json
import re
import time
import threading
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# ── 工具白名单：只读类，直接放行 ──
AUTO_ALLOW = [
    "Read",
    "Grep",
    "Glob",
    "Bash",          # Bash 本身不是危险操作，危险的是 Bash 的参数
    "TaskList",
    "TaskGet",
    "CronList",
    "EnterWorktree",
    "ExitWorktree",
]

# ── 需确认操作：24h 内同类操作只问一次 ──
ASK_ONCE = [
    "Write",
    "Edit",
    "NotebookEdit",
    "WebFetch",
    "WebSearch",
    "TaskCreate",
    "TaskUpdate",
    "TaskStop",
    "CronCreate",
    "CronDelete",
    "Skill",
    "SendMessage",
    "TeamCreate",
    "TeamDelete",
]

# ── 危险操作：始终拒绝 ──
ALWAYS_DENY_PATTERNS = [
    # Bash 危险命令
    (r"Bash.*rm\s+-rf\s+/", "禁止递归强制删除根目录"),
    (r"Bash.*rm\s+-rf\s+~", "禁止递归强制删除用户目录"),
    (r"Bash.*sudo\s", "禁止使用 sudo 提权"),
    (r"Bash.*chmod\s+777", "禁止设置全局可写权限"),
    (r"Bash.*chmod\s+-R\s+777", "禁止递归设置全局可写权限"),
    (r"Bash.*>\/dev\/[sh]d[a-z]", "禁止直接写入磁盘设备"),
    (r"Bash.*mkfs\.", "禁止格式化磁盘"),
    (r"Bash.*dd\s+if=", "禁止磁盘低级操作"),
    (r"Bash.*:\(\)\s*\{", "禁止 fork bomb"),
    (r"Bash.*wget.*\|.*sh", "禁止管道下载执行"),
    (r"Bash.*curl.*\|.*sh", "禁止管道下载执行"),
    (r"Bash.*\/etc\/passwd", "禁止访问系统密码文件"),
    (r"Bash.*\/etc\/shadow", "禁止访问系统影子密码文件"),
    (r"Bash.*nc\s+-[lL]", "禁止 netcat 监听"),
    # 危险工具
    (r"Bash.*dangerouslyDisableSandbox.*true", "禁止禁用沙箱"),
    # 系统级破坏
    (r"Bash.*scp.*\/etc\/", "禁止传输系统配置"),
    (r"Bash.*iptables", "禁止修改防火墙规则"),
    (r"Bash.*systemctl\s+disable", "禁止禁用系统服务"),
]

# ── 信任模式 ──
TRUST_MODE_CAUTIOUS = "cautious"    # 所有需确认操作都询问
TRUST_MODE_NORMAL = "normal"        # 同类操作只问一次
TRUST_MODE_TRUSTED = "trusted"      # 仅拦截高危操作

# ── 策略门常量 ──
from maestro.app_config import DEFAULT_TOKEN_LIMIT, DEFAULT_DAILY_BUDGET
BATCH_DELETE_THRESHOLD = 5
SENSITIVE_FILES = [".env", ".env.local", ".gitignore", "settings.json",
    "*.key", "*.pem", "*.p12", "credentials*", "secret*"]
SECRET_PATTERNS = [
    (r'sk-[A-Za-z0-9-_]{20,}', "疑似 API Key"),
    (r'api_key\s*=\s*["\'][^"\']{10,}', "疑似硬编码 Key"),
    (r'password\s*=\s*["\']', "疑似硬编码密码"),
    (r'token\s*=\s*["\'][A-Za-z0-9-_]{15,}', "疑似硬编码 Token"),
]
_AGENT_BASE_TOOLS = {
    "coder": "Read,Grep,Glob,Write,Edit,Bash,NotebookEdit",
    "reviewer": "Read,Grep,Glob", "test": "Read,Grep,Glob,Write,Edit,Bash",
    "writer": "Read,Grep,Glob,Write,Edit", "explorer": "Read,Grep,Glob,WebSearch,WebFetch",
    "reasonix": "Read,Grep,Glob,Write,Edit,Bash,NotebookEdit",
    "general-worker": "Read,Grep,Glob,Write,Edit,Bash",
    "docker_worker": "Read,Grep,Glob,Write,Edit,Bash",
}
DRY_RUN_DENY = {"Write", "Edit", "NotebookEdit", "Bash"}


class PermissionEngine:
    """三级权限审批引擎"""

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path
        self._memories: Dict[str, float] = {}  # key -> expiry_timestamp
        self._memories_lock = threading.Lock()
        self._stats = {
            "allowed": 0,
            "asked": 0,
            "denied": 0,
        }
        self._stats_lock = threading.Lock()

    # ── 数据库初始化 ──
    def _ensure_db(self):
        """延迟初始化数据库连接和表结构"""
        import sqlite3
        if self._db_path is None:
            return None
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._db_path))
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
        return conn

    # ── 核心分类逻辑 ──
    def classify(self, tool_name: str, args=None) -> Tuple[str, str, str]:
        """
        分类工具调用风险。
        返回 (decision, risk_level, reason)
        decision: 'allow' | 'ask' | 'deny'
        risk_level: 'low' | 'medium' | 'high'
        """
        args_str = str(args) if args else ""

        # 1. 检查危险模式（最高优先级）
        for pattern, reason in ALWAYS_DENY_PATTERNS:
            check_str = f"{tool_name} {args_str}"
            if re.search(pattern, check_str, re.IGNORECASE):
                return "deny", "high", reason

        # 2. Bash 工具需特殊检查参数安全性
        if tool_name == "Bash":
            risk, reason = self._check_bash_args(args_str)
            if risk == "high":
                return "deny", "high", reason
            if risk == "medium":
                return "ask", "medium", reason
            return "allow", "low", ""

        # 3. 检查 AUTO_ALLOW
        if tool_name in AUTO_ALLOW:
            return "allow", "low", ""

        # 4. 检查 ASK_ONCE
        if tool_name in ASK_ONCE:
            return "ask", "medium", ""

        # 5. 未分类工具默认询问
        return "ask", "medium", f"未识别工具 {tool_name}，需确认后执行"

    def _check_bash_args(self, args_str: str) -> Tuple[str, str]:
        """检查 Bash 命令参数的安全级别"""
        if not args_str:
            return "low", ""

        # 中危：文件写入/删除（非系统级）
        medium_patterns = [
            (r"\brm\b", "包含文件删除命令 rm"),
            (r">\s*/", "包含文件写入重定向"),
            (r"\bmv\b", "包含文件移动命令 mv"),
            (r"\bcp\b", "包含文件复制命令 cp"),
            (r"\bchmod\b", "包含权限修改命令 chmod"),
            (r"\bchown\b", "包含所有者修改命令 chown"),
            (r"\bpip\s+install\b", "包含 pip 安装命令"),
            (r"\bnpm\s+install\b", "包含 npm 安装命令"),
            (r"\bgit\s+push\b", "包含 git push 命令"),
            (r"\bdocker\b", "包含 docker 命令"),
            (r"\bshutdown\b", "包含关机命令"),
            (r"\breboot\b", "包含重启命令"),
        ]
        for pattern, reason in medium_patterns:
            if re.search(pattern, args_str, re.IGNORECASE):
                return "medium", reason

        return "low", ""

    # ── 记忆系统（24h 有效期）──
    def remember(self, tool_name: str, path_prefix: str = "") -> str:
        """记住用户选择，返回记忆 key"""
        key = self._memory_key(tool_name, path_prefix)
        with self._memories_lock:
            self._memories[key] = time.time() + 86400  # 24h
        return key

    def check_memory(self, tool_name: str, path_prefix: str = "") -> bool:
        """检查 24h 内是否有有效的记忆"""
        key = self._memory_key(tool_name, path_prefix)
        with self._memories_lock:
            expiry = self._memories.get(key, 0)
            if expiry > time.time():
                return True
            # 清理过期记忆
            if expiry > 0:
                del self._memories[key]
        return False

    def forget(self, tool_name: str, path_prefix: str = ""):
        """主动清除记忆"""
        key = self._memory_key(tool_name, path_prefix)
        with self._memories_lock:
            self._memories.pop(key, None)

    def _memory_key(self, tool_name: str, path_prefix: str) -> str:
        """生成记忆 key"""
        if path_prefix:
            return f"{tool_name}:{path_prefix}"
        return tool_name

    # ── 信任模式处理 ──
    def apply_trust_mode(self, decision: str, trust_mode: str, tool_name: str,
                         path_prefix: str = "") -> Tuple[str, str]:
        """
        根据信任模式调整决策。
        返回 (adjusted_decision, note)
        """
        if trust_mode == TRUST_MODE_TRUSTED:
            # 信任模式：仅拦截高危
            if decision == "deny":
                return "deny", "高危操作，始终拦截"
            if decision == "ask" and self.check_memory(tool_name, path_prefix):
                return "allow", "信任模式-已有记忆，直接放行"
            return "allow", "信任模式-自动放行"

        elif trust_mode == TRUST_MODE_NORMAL:
            # 正常模式：同类操作只问一次
            if decision == "ask" and self.check_memory(tool_name, path_prefix):
                return "allow", "正常模式-24h内有记忆，直接放行"
            return decision, ""

        else:  # TRUST_MODE_CAUTIOUS（默认）
            return decision, ""

    # ── 审计日志 ──
    def log_audit(self, tool: str, decision: str, reason: str = "",
                  risk: str = "", user_choice: str = "", args: str = ""):
        """写入审计日志到 cost.db"""
        with self._stats_lock:
            if decision == "allow":
                self._stats["allowed"] += 1
            elif decision == "ask":
                self._stats["asked"] += 1
            elif decision == "deny":
                self._stats["denied"] += 1

        if self._db_path is None:
            return

        import sqlite3
        try:
            conn = self._ensure_db()
            if conn is None:
                return
            try:
                conn.execute(
                    "INSERT INTO permission_audit (time, tool, args, decision, risk, reason, user_choice) VALUES (?,?,?,?,?,?,?)",
                    (time.strftime("%Y-%m-%d %H:%M:%S"), tool, args[:500] if args else "",
                     decision, risk, reason[:200] if reason else "",
                     user_choice[:100] if user_choice else "")
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            log.warning(f"审计日志写入失败: {e}")

    # ── 统计查询 ──
    def get_stats(self) -> dict:
        """获取权限统计数据"""
        with self._stats_lock:
            return dict(self._stats)

    def query_audit_log(self, limit: int = 100, decision_filter: str = "") -> list:
        """查询审计日志"""
        if self._db_path is None or not self._db_path.exists():
            return []

        import sqlite3
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            try:
                if decision_filter:
                    rows = conn.execute(
                        "SELECT * FROM permission_audit WHERE decision = ? ORDER BY id DESC LIMIT ?",
                        (decision_filter, limit)
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM permission_audit ORDER BY id DESC LIMIT ?",
                        (limit,)
                    ).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()
        except Exception as e:
            log.warning(f"审计日志查询失败: {e}")
            return []

    # ── a) 成本预算检查 ──
    def check_cost_budget(self, task_estimate_tokens: int) -> tuple[bool, str]:
        if task_estimate_tokens > DEFAULT_TOKEN_LIMIT:
            return False, f"token {task_estimate_tokens} 超上限 {DEFAULT_TOKEN_LIMIT}"
        today_key = time.strftime("%Y%m%d")
        with self._stats_lock:
            daily_tokens = self._stats.get(f"daily_{today_key}", 0)
        if daily_tokens * 0.000002 > DEFAULT_DAILY_BUDGET:
            return False, f"日预算 ${DEFAULT_DAILY_BUDGET} 已超"
        with self._stats_lock:
            self._stats[f"daily_{today_key}"] = daily_tokens + task_estimate_tokens
        return True, ""

    # ── b) 权限范围限制 ──
    def get_effective_permissions(self, agent_name: str, task_category: str = "",
                                   dry_run: bool = False) -> list[str]:
        base = _AGENT_BASE_TOOLS.get(agent_name, "Read,Grep,Glob").split(",")
        if task_category in ("代码审查", "测试质量"):
            for t in ("WebSearch", "WebFetch"):
                if t not in base:
                    base.append(t)
        if dry_run:
            base = [t for t in base if t not in DRY_RUN_DENY]
        return base

    # ── c) 安全扫描检查点 ──
    def pre_write_check(self, agent_name: str, files_to_modify: list) -> tuple[bool, str]:
        if not files_to_modify:
            return True, ""
        del_cnt = sum(1 for f in files_to_modify if "删除" in str(f) or "delete" in str(f).lower())
        if len(files_to_modify) > BATCH_DELETE_THRESHOLD:
            return False, f"批量修改 {len(files_to_modify)} 文件 > {BATCH_DELETE_THRESHOLD}"
        if del_cnt > BATCH_DELETE_THRESHOLD:
            return False, f"批量删除 {del_cnt} 文件 > {BATCH_DELETE_THRESHOLD}"
        for fp in files_to_modify:
            fname = Path(str(fp)).name
            for pat in SENSITIVE_FILES:
                if fnmatch.fnmatch(fname, pat):
                    return False, f"敏感文件: {fname}"
        return True, ""

    # ── d) 合规验证 ──
    def validate_output(self, output_text: str, expected_format: str = "") -> tuple[bool, str]:
        if not output_text or len(output_text.strip()) < 10:
            return False, "输出过短"
        for pattern, desc in SECRET_PATTERNS:
            if re.search(pattern, output_text):
                return False, f"禁止内容: {desc}"
        if expected_format == "json":
            try:
                json.loads(output_text)
            except json.JSONDecodeError:
                return False, "非 JSON 格式"
        return True, ""

    # ── 便捷方法 ──
    def check_and_log(self, tool_name: str, args=None, trust_mode: str = "",
                      path_prefix: str = "", user_choice: str = "") -> Tuple[str, str, str]:
        """
        一站式检查：分类 → 应用信任模式 → 记录审计。
        返回 (decision, risk, reason)
        """
        decision, risk, reason = self.classify(tool_name, args)
        original_decision = decision

        # 应用信任模式
        if trust_mode and decision == "ask":
            decision, note = self.apply_trust_mode(decision, trust_mode, tool_name, path_prefix)
            if note:
                reason = note

        # 如果用户已选择 allow，且之前是 ask
        if user_choice == "allow" and original_decision == "ask":
            decision = "allow"
            self.remember(tool_name, path_prefix)
            reason = "用户已确认"

        # 记录审计
        self.log_audit(
            tool=tool_name,
            decision=decision,
            reason=reason,
            risk=risk,
            user_choice=user_choice,
            args=str(args) if args else "",
        )

        return decision, risk, reason


# ── 模块级便捷函数（使用默认引擎实例）──

_default_engine: Optional[PermissionEngine] = None
_engine_lock = threading.Lock()


def get_engine(db_path: Optional[Path] = None) -> PermissionEngine:
    """获取默认权限引擎实例（单例）"""
    global _default_engine
    if _default_engine is None:
        with _engine_lock:
            if _default_engine is None:
                _default_engine = PermissionEngine(db_path=db_path)
    return _default_engine


def init_engine(project_root: Path):
    """初始化权限引擎，关联到项目的 cost.db"""
    db_path = project_root / "maestro" / "cost.db"
    return get_engine(db_path)
