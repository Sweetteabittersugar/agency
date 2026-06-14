"""Cron 定时任务 API — CRUD 端点（Phase 1）"""

import uuid
import logging

log = logging.getLogger(__name__)


def handle_list(handler, parsed):
    """GET /api/cron — 列出所有定时任务"""
    from maestro.cron_scheduler import list_jobs

    handler.send_json({"ok": True, "jobs": list_jobs()})
    return True


def handle_create(handler, body):
    """POST /api/cron — 创建定时任务"""
    from maestro.cron_scheduler import add_job

    prompt = body.get("prompt", "").strip()
    cron_expr = body.get("cron_expr", "").strip()
    if not prompt or not cron_expr:
        handler.send_json({"ok": False, "error": "缺少必填字段 prompt 或 cron_expr"}, 400)
        return True
    job_id = body.get("id", str(uuid.uuid4())[:8])
    job = add_job(job_id, prompt, cron_expr, body.get("api_provider", "deepseek"), True)
    handler.send_json({"ok": True, "job": job})
    return True


def handle_delete(handler, parsed):
    """DELETE /api/cron/:id — 删除定时任务
    注意：DELETE 请求时 adapt_handler 传的是 body_dict 而非 _Parsed，
    所以 job_id 需从 handler.path 获取而非 parsed['path']。"""
    from maestro.cron_scheduler import remove_job

    # 从 handler 的 path 属性获取 URL 中的 job_id
    job_id = handler.path.rsplit("/", 1)[-1]
    if not job_id:
        handler.send_json({"ok": False, "error": "缺少 job_id"}, 400)
        return True
    remove_job(job_id)
    handler.send_json({"ok": True})
    return True
