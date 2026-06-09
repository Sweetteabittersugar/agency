"""自动测试 API"""
import uuid
import time

_runs = {}


def handle_test_run(handler, body):
    """POST /api/test/run"""
    url = body.get("url", "")
    if not url:
        handler.send_json({"error": "url required"}, 400)
        return True
    run_id = str(uuid.uuid4())[:8]
    _runs[run_id] = {"status": "running", "start_time": time.time(), "url": url}
    handler.send_json({"run_id": run_id, "status": "started"})
    return True


def handle_test_status(handler, parsed):
    """GET /api/test/status/:runId"""
    path = parsed.path
    run_id = path.rsplit("/", 1)[-1]
    run = _runs.get(run_id)
    if not run:
        handler.send_json({"error": "not found"}, 404)
        return True
    handler.send_json(run)
    return True
