"""自动测试 API -- 通过 claude -p 发送 Playwright 指令并解析结果"""

import json
import subprocess
import threading
import time
import uuid
from pathlib import Path


_runs: dict = {}
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
SCREENSHOTS_DIR = RESULTS_DIR / "screenshots"


def _ensure_dirs() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def _build_playwright_prompt(url: str, steps: list | None = None) -> str:
    """构建 Playwright 测试 prompt，指示 claude -p 执行并保存结果。"""
    run_id = uuid.uuid4().hex[:8]
    screenshot_path = (SCREENSHOTS_DIR / f"test_{run_id}.png").as_posix()
    result_path = (RESULTS_DIR / f"test_result_{run_id}.json").as_posix()

    prompt = (
        f"你是浏览器自动化测试执行者。执行以下测试并保存结果。\n\n## 任务\n1. 导航到 URL: {url}\n"
    )

    if steps:
        for i, step in enumerate(steps, 1):
            action = step.get("action", "click")
            selector = step.get("selector", "")
            prompt += f"{i + 1}. {action} 元素 '{selector}'\n"

    prompt += (
        f"\n## 输出要求\n"
        f"1. 使用 mcp__plugin_playwright_playwright__browser_navigate 打开页面\n"
        f"2. 使用 mcp__plugin_playwright_playwright__browser_take_screenshot 截图保存到 {screenshot_path}\n"
        f"3. 如果遇到错误，记录下来\n"
    )

    prompt += (
        f"\n最后将 JSON 结果写入文件 {result_path}:\n"
        f'{{"status":"completed"|"failed",'
        f'"screenshot":"{screenshot_path}",'
        f'"url":"{url}",'
        f'"tests":[{{"name":"页面加载","passed":true|false,"duration_ms":0,"error":""}}],'
        f'"summary":"简短测试结果描述"}}\n\n'
        f"使用 Write 工具写入结果文件。禁止输出任何其他内容。"
    )

    return prompt, run_id, result_path, screenshot_path


def _execute_test(project_root: str, prompt: str) -> dict | None:
    """启动 claude -p 执行 Playwright 测试，返回结果或 None。"""
    try:
        result = subprocess.run(
            [
                "claude",
                "-p",
                prompt,
                "--model",
                "haiku",
                "--permission-mode",
                "acceptEdits",
                "--max-turns",
                "20",
                "--max-budget-usd",
                "0.10",
                "--output-format",
                "text",
            ],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=120,
        )
        # 尝试从输出中提取 JSON 结果
        for line in result.stdout.split("\n"):
            line = line.strip()
            if line.startswith("{") and "status" in line:
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        return None
    except subprocess.TimeoutExpired:
        return {"status": "failed", "error": "测试超时（120s）"}
    except FileNotFoundError:
        return {"status": "failed", "error": "claude 命令不可用"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def handle_test_run(handler, body):
    """POST /api/test/run -- 启动 Playwright 测试"""
    url = body.get("url", "")
    if not url:
        handler.send_json({"error": "缺少必填字段 url。请提供要测试的页面地址"}, 400)
        return True

    _ensure_dirs()
    steps = body.get("steps", None)
    project_root = body.get("proj_dir", "") or str(Path(__file__).resolve().parent.parent.parent)

    prompt, run_id, result_path, screenshot_path = _build_playwright_prompt(url, steps)
    _runs[run_id] = {
        "status": "running",
        "start_time": time.time(),
        "url": url,
        "result_path": result_path,
        "screenshot": screenshot_path,
    }

    def _worker() -> None:
        result = _execute_test(project_root, prompt)
        if result:
            _runs[run_id]["status"] = result.get("status", "failed")
            _runs[run_id]["tests"] = result.get("tests", [])
            _runs[run_id]["summary"] = result.get("summary", "")
            _runs[run_id]["error"] = result.get("error", "")
            _runs[run_id]["end_time"] = time.time()
            # 验证截图是否存在
            shot = Path(screenshot_path)
            if shot.exists():
                _runs[run_id]["screenshot"] = screenshot_path
            else:
                _runs[run_id]["screenshot"] = None
            # 持久化结果
            try:
                Path(result_path).write_text(
                    json.dumps(_runs[run_id], ensure_ascii=False), encoding="utf-8"
                )
            except Exception:
                pass
        else:
            # 检查是否有 claude 写入的结果文件
            result_file = Path(result_path)
            if result_file.exists():
                try:
                    saved = json.loads(result_file.read_text(encoding="utf-8"))
                    _runs[run_id].update(saved)
                    _runs[run_id]["end_time"] = time.time()
                except (json.JSONDecodeError, Exception):
                    _runs[run_id]["status"] = "failed"
                    _runs[run_id]["error"] = "无法解析测试结果"
                    _runs[run_id]["end_time"] = time.time()
            else:
                _runs[run_id]["status"] = "failed"
                _runs[run_id]["error"] = "claude 进程未产出结果"
                _runs[run_id]["end_time"] = time.time()

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

    handler.send_json({"run_id": run_id, "status": "started", "screenshot": screenshot_path})
    return True


def handle_test_status(handler, parsed):
    """GET /api/test/status/:runId -- 获取测试状态/结果"""
    path = parsed.path
    run_id = path.rsplit("/", 1)[-1]
    run = _runs.get(run_id)
    if not run:
        handler.send_json({"error": "未找到该测试运行 ID。请检查 run_id 是否正确"}, 404)
        return True

    # 如果还在运行且结果文件已存在，自动加载
    if run.get("status") == "running":
        result_path = run.get("result_path")
        if result_path and Path(result_path).exists():
            try:
                saved = json.loads(Path(result_path).read_text(encoding="utf-8"))
                run.update(saved)
                run["end_time"] = time.time()
            except Exception:
                pass

    response = {
        "run_id": run_id,
        "status": run.get("status", "unknown"),
        "url": run.get("url", ""),
        "screenshot": run.get("screenshot"),
        "tests": run.get("tests", []),
        "summary": run.get("summary", ""),
        "error": run.get("error", ""),
    }
    handler.send_json(response)
    return True
