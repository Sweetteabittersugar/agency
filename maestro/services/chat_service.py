"""Chat 业务逻辑层 — chat.py (SSE) 和 ws_chat.py (WebSocket) 共享核心逻辑

抽取 5 项重复逻辑：
1. API Key 三级回退（request → env → api_key.json）
2. PermissionEngine 模块级单例 + 预算检查
3. Memory injection（首次新会话）
4. 费用记录统一入口
5. Session 事件安全写入
"""

import os
import json
import time
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# ── 模块级单例：PermissionEngine 只创建一次，避免每次请求 new ──
_engine = None


def _get_permission_engine(project_root: Path):
    """获取 PermissionEngine 单例——替代 chat.py/ws_chat.py 每次 new"""
    global _engine
    if _engine is None:
        from maestro.permission_engine import PermissionEngine

        _engine = PermissionEngine(project_root / "maestro" / "cost.db")
    return _engine


def resolve_api_key(project_root, api_key: str = "", api_provider: str = ""):
    """API Key 三级回退：request → env → api_key.json

    优先级不可变——后台配置(env)优先于前端传递，服务端文件兜底。
    返回 (api_key: str, api_provider: str)
    """
    # 第一级：从后台环境变量读取（优先级最高）
    if not api_key:
        from maestro.models import get_provider_config

        _, env_key, _ = get_provider_config()
        api_key = env_key
    # 第二级：从服务端 api_key.json 读取（设置面板保存的 Key）
    if not api_key:
        try:
            _key_file = project_root / "maestro" / "api_key.json"
            if _key_file.exists():
                _data = json.loads(_key_file.read_text(encoding="utf-8"))
                api_key = _data.get("key", "")
                if not api_provider:
                    api_provider = _data.get("provider", "deepseek")
        except Exception:
            pass
    # 兜底：环境变量 PROVIDER
    if not api_provider:
        api_provider = os.environ.get("PROVIDER", "deepseek")
    return api_key, api_provider


def check_budget(task_text: str, model: str, project_root) -> tuple:
    """预算检查——任务执行前验证日预算是否充足。

    返回 (ok: bool, message: str)。失败不抛异常，不阻塞聊天。
    """
    try:
        from maestro.models import estimate_tokens

        engine = _get_permission_engine(project_root)
        task_tokens = estimate_tokens(task_text, model or "deepseek-v4-flash")
        ok, msg = engine.check_cost_budget(
            task_estimate_tokens=task_tokens,
            model=model or "deepseek-v4-flash",
        )
        return ok, msg
    except Exception:
        # 预算检查失败不阻塞聊天——宁可放行也不错杀
        return True, ""


def inject_memory(task: str, project_root) -> str:
    """新会话注入记忆——扫描 memory/ 目录获取相关历史。

    返回增强后的 task 文本（或原 task，注入失败不阻塞）。
    """
    try:
        from maestro.memory_engine import build_injection_prefix

        return build_injection_prefix(task, str(project_root))
    except Exception:
        return task


def record_chat_cost(
    project_root,
    model: str,
    in_tokens: int,
    out_tokens: int,
    cost_usd: float,
    duration_s: float,
    agent: str = "",
    session_id: str = "",
    cache_read: int = 0,
    cache_write: int = 0,
    cache_ephemeral: int = 0,
    is_estimated: bool = False,
    tokens_from_api: bool = True,
):
    """统一费用记录入口——chat.py 和 ws_chat.py 共用同一写入逻辑。

    静默失败不阻塞聊天流。
    """
    try:
        from maestro.web_cost import record_cost as web_record_cost

        _now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        web_record_cost(
            project_root=project_root,
            time_str=_now_str,
            model=model,
            in_tokens=in_tokens,
            out_tokens=out_tokens,
            cost_usd=cost_usd,
            duration_s=duration_s,
            agent=agent,
            session_id=session_id,
            cache_read=cache_read,
            cache_write=cache_write,
            cache_ephemeral=cache_ephemeral,
            is_estimated=is_estimated,
            tokens_from_api=tokens_from_api,
        )
    except Exception:
        pass


def append_session_event(session_id: str, event_type: str, data: dict):
    """安全写入 session 事件——供时间线和会话列表使用。

    静默失败不阻塞聊天流。
    """
    try:
        from maestro.session_store import append_event

        append_event(session_id, event_type, data)
    except Exception:
        pass
