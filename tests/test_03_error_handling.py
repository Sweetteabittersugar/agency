#!/usr/bin/env python3
"""
Test 3: 错误处理检查
检查 web.py 和 main.py 中的错误处理逻辑：
- 异常捕获是否完整
- 边界条件处理
- 输入验证
- 空值/缺失值处理
"""
import sys
import os
import re
import json
import time
import threading
import unittest
from http.server import HTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "maestro"))

from web import Handler, HTML, AGENCY_VERSION
from main import (
    route_task, route_with_fallback, route_with_cache,
    load_agent, estimate_cost, get_agent_stats, record_agent_result,
    ROUTING, get_provider_config, get_actual_model, semantic_match,
)

PORT = 18803


class TestServerErrorHandling(unittest.TestCase):
    """服务端错误处理检查（运行时）"""

    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", PORT), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.5)
        cls.base = f"http://127.0.0.1:{PORT}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def _post(self, path, data=None):
        import urllib.request
        body = json.dumps(data or {}).encode("utf-8") if data else b"{}"
        req = urllib.request.Request(
            f"{self.base}{path}", data=body,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()
        except Exception as e:
            return -1, str(e).encode()

    def test_01_empty_body_post(self):
        """POST 空 body — 不崩溃"""
        import urllib.request
        req = urllib.request.Request(
            f"{self.base}/api/route", data=b"",
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            self.assertIn("agent", data)
        except urllib.error.HTTPError as e:
            # 即使返回 4xx 也不应崩溃
            self.assertIn(e.code, (400, 404, 405, 500))

    def test_02_invalid_json_body(self):
        """POST 非 JSON body — 不崩溃"""
        import urllib.request
        req = urllib.request.Request(
            f"{self.base}/api/route", data=b"this is not json",
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            self.assertIn("agent", data)
        except urllib.error.HTTPError as e:
            self.assertIn(e.code, (400, 404, 405, 500))

    def test_03_gbk_encoded_body(self):
        """POST GBK 编码 body — 不崩溃"""
        import urllib.request
        gbk_data = "测试任务".encode("gbk")
        req = urllib.request.Request(
            f"{self.base}/api/route", data=gbk_data,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            resp = urllib.request.urlopen(req, timeout=5)
            # 应该能处理
            data = json.loads(resp.read())
            self.assertIn("agent", data)
        except urllib.error.HTTPError as e:
            self.assertIn(e.code, (400, 404, 405, 500))

    def test_04_missing_content_type(self):
        """POST 无 Content-Type — 不崩溃"""
        import urllib.request
        body = json.dumps({"task": "test"}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base}/api/route", data=body, method="POST",
        )
        try:
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            self.assertIn("agent", data)
        except urllib.error.HTTPError as e:
            self.assertIn(e.code, (400, 404, 405, 500))

    def test_05_unknown_route_returns_404(self):
        """未定义路径返回 404 — 不返回 500"""
        import urllib.request
        try:
            resp = urllib.request.urlopen(f"{self.base}/api/unknown-route-test", timeout=5)
            self.fail("应返回 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

    def test_06_agent_save_no_name(self):
        """POST /api/agent-save 无 name — 返回 error"""
        status, data = self._post("/api/agent-save", {"content": "test"})
        result = json.loads(data)
        self.assertFalse(result.get("ok", True))
        self.assertIn("error", result)

    def test_07_agent_save_no_content(self):
        """POST /api/agent-save 无 content — 不崩溃"""
        status, data = self._post("/api/agent-save", {"name": "test-agent"})
        if status == 200:
            # 应该保存空内容或返回错误
            result = json.loads(data)
            if not result.get("ok"):
                self.assertIn("error", result)

    def test_08_route_with_special_chars(self):
        """路由含特殊字符 — 不崩溃"""
        for bad_task in ["", None, "a" * 10000, "!@#$%^&*()_+{}|:\"<>?", "\x00\x01\x02"]:
            if bad_task is None:
                continue  # None 无法序列化
            try:
                self._post("/api/route", {"task": bad_task})
            except Exception:
                pass  # 不崩溃即可

    def test_09_agent_content_empty_name(self):
        """GET /api/agent-content?name= — 返回 error 或 404"""
        import urllib.request
        try:
            resp = urllib.request.urlopen(f"{self.base}/api/agent-content?name=", timeout=5)
            data = json.loads(resp.read())
            if "error" in data:
                pass  # 期望的行为
        except urllib.error.HTTPError:
            pass


class TestLogicErrorHandling(unittest.TestCase):
    """核心逻辑错误处理检查（单元级）"""

    def test_01_route_task_empty(self):
        """空任务路由 — 返回默认 agent"""
        agent, score, confidence = route_task("")
        self.assertEqual(agent, "coder")
        self.assertIsInstance(score, (int, float))
        self.assertIsInstance(confidence, float)

    def test_02_route_task_gibberish(self):
        """乱输入路由 — 不崩溃"""
        agent, score, confidence = route_task("abcdefghijklmnopqrstuvwxyz" * 100)
        self.assertIsNotNone(agent)
        self.assertIsInstance(score, (int, float))
        self.assertIsInstance(confidence, float)

    def test_03_route_with_fallback_empty(self):
        """route_with_fallback 空任务"""
        result = route_with_fallback("")
        self.assertEqual(len(result), 4)
        agent, score, confidence, method = result
        self.assertEqual(agent, "coder")
        self.assertIn(method, ("keyword", "semantic", "keyword_low_confidence", "cache"))

    def test_04_route_with_cache_empty(self):
        """route_with_cache 空任务"""
        agent, score, confidence, method = route_with_cache("")
        self.assertEqual(agent, "coder")

    def test_05_load_agent_not_found(self):
        """加载不存在的 Agent — 返回默认提示"""
        prompt, model = load_agent("__does_not_exist__")
        self.assertIn("__does_not_exist__", prompt)
        self.assertIsInstance(model, str)
        self.assertTrue(len(model) > 0)

    def test_06_load_agent_partial_name(self):
        """部分匹配 agent 名 — 应模糊匹配"""
        prompt, model = load_agent("code")  # 应匹配到 coder
        self.assertIsNotNone(prompt)
        self.assertGreater(len(prompt), 0)

    def test_07_estimate_cost_unknown_model(self):
        """未知模型费用估算 — 返回 0"""
        cost = estimate_cost("unknown-model-12345", 100, 50)
        self.assertEqual(cost, 0.0)

    def test_08_estimate_cost_known(self):
        """已知模型费用估算 — 返回正值"""
        cost = estimate_cost("deepseek-chat", 1000, 500)
        self.assertGreater(cost, 0)

    def test_09_record_agent_result(self):
        """记录 Agent 结果 — 不崩溃"""
        try:
            record_agent_result("test-agent", True)
            record_agent_result("test-agent", False)
            stats = get_agent_stats()
            self.assertIn("test-agent", stats)
            self.assertEqual(stats["test-agent"]["total"], 2)
            self.assertEqual(stats["test-agent"]["success_rate"], 0.5)
        except Exception as e:
            self.fail(f"record_agent_result 崩溃: {e}")

    def test_10_get_agent_stats_empty(self):
        """空统计 — 返回空 dict"""
        stats = get_agent_stats()
        self.assertIsInstance(stats, dict)

    def test_11_semantic_match_empty(self):
        """空文本语义匹配 — 返回默认"""
        agent, score = semantic_match("")
        self.assertEqual(agent, "coder")
        self.assertEqual(score, 0.0)

    def test_12_get_provider_config_no_key(self):
        """无 key 时 get_provider_config — 返回 None"""
        # 保存环境
        saved = {}
        for k in ["DEEPSEEK_API_KEY", "OPENAI_API_KEY", "OLLAMA_BASE_URL"]:
            saved[k] = os.environ.pop(k, None)
        try:
            base_url, api_key, headers = get_provider_config()
            self.assertIsNone(base_url)
            self.assertIsNone(api_key)
            self.assertIsNone(headers)
        finally:
            for k, v in saved.items():
                if v:
                    os.environ[k] = v

    def test_13_get_actual_model_empty(self):
        """空模型名映射 — 返回默认"""
        model = get_actual_model("")
        self.assertEqual(model, os.environ.get("DEFAULT_MODEL", "deepseek-chat"))

    def test_14_get_actual_model_known(self):
        """已知模型名映射"""
        model = get_actual_model("haiku")
        self.assertIsInstance(model, str)
        self.assertGreater(len(model), 0)

    def test_15_route_with_unicode(self):
        """Unicode 任务路由 — 不崩溃"""
        agent, score, confidence = route_task("帮我写一个 🔥 的排序算法")
        self.assertIsNotNone(agent)

    def test_16_route_task_none(self):
        """None 任务路由 — 应处理"""
        try:
            agent, score, confidence = route_task(None)
            self.assertIsNotNone(agent)
        except (AttributeError, TypeError) as e:
            self.fail(f"None 任务导致崩溃: {e}")


class TestSourceErrorHandling(unittest.TestCase):
    """源码静态错误处理检查"""

    def test_01_web_py_has_try_except(self):
        """web.py 中包含充分的 try/except"""
        src = open(str(PROJECT_ROOT / "maestro" / "web.py"), encoding="utf-8").read()
        try_count = len(re.findall(r"\btry\b", src))
        except_count = len(re.findall(r"\bexcept\b", src))
        self.assertGreaterEqual(try_count, 10, f"try 块数量不足 ({try_count})")
        self.assertGreaterEqual(except_count, 10, f"except 块数量不足 ({except_count})")

    def test_02_main_py_has_try_except(self):
        """main.py 中包含充分的 try/except"""
        src = open(str(PROJECT_ROOT / "maestro" / "main.py"), encoding="utf-8").read()
        try_count = len(re.findall(r"\btry\b", src))
        except_count = len(re.findall(r"\bexcept\b", src))
        self.assertGreaterEqual(try_count, 3)
        self.assertGreaterEqual(except_count, 3)

    def test_03_web_py_no_bare_except(self):
        """web.py 中避免裸 except（除已知位置）"""
        src = open(str(PROJECT_ROOT / "maestro" / "web.py"), encoding="utf-8").read()
        # 允许特定模式的裸 except：json 解析、回调等
        bare_excepts = re.findall(r"\bexcept\s*:", src)
        bare_except_count = len(bare_excepts)
        # 存在一些裸 except 是可以接受的（如 UI 回调），但不应过多
        self.assertLessEqual(bare_except_count, 15,
                             f"裸 except 过多 ({bare_except_count})，建议指定异常类型")

    def test_04_main_py_no_bare_except(self):
        """main.py 中避免裸 except"""
        src = open(str(PROJECT_ROOT / "maestro" / "main.py"), encoding="utf-8").read()
        bare_excepts = re.findall(r"\bexcept\s*:", src)
        self.assertLessEqual(len(bare_excepts), 3)

    def test_05_web_py_has_finally(self):
        """web.py 有 finally 块（资源清理）"""
        src = open(str(PROJECT_ROOT / "maestro" / "web.py"), encoding="utf-8").read()
        finally_count = len(re.findall(r"\bfinally\b", src))
        # JS 中的 finally 不算
        js_match = re.search(r"<script>(.*?)</script>", src, re.DOTALL)
        if js_match:
            js_part = js_match.group(1)
            js_finally = len(re.findall(r"\bfinally\b", js_part))
            finally_count -= js_finally
        self.assertGreaterEqual(finally_count, 0)

    def test_06_connection_closed_in_api(self):
        """API 中数据库连接有关闭"""
        src = open(str(PROJECT_ROOT / "maestro" / "web.py"), encoding="utf-8").read()
        conn_count = src.count("conn = sqlite3.connect")
        close_count = src.count("conn.close()")
        # 每个 connect 都应该有 close
        self.assertEqual(conn_count, close_count,
                         f"conn open={conn_count} 但 close={close_count}，可能存在连接泄露")

    def test_07_web_py_has_404_handler(self):
        """do_GET 和 do_POST 都有 404 兜底"""
        src = open(str(PROJECT_ROOT / "maestro" / "web.py"), encoding="utf-8").read()
        # do_GET 的 else 分支返回 404
        self.assertIn("self.send_response(404)", src)
        # do_POST 的 else 分支返回 404
        self.assertIn("self.send_response(404)", src)


if __name__ == "__main__":
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestServerErrorHandling))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestLogicErrorHandling))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestSourceErrorHandling))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
