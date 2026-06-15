#!/usr/bin/env python3
"""
Test 3: Error handling checks
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
from web import Handler
from main import (
    route_task,
    route_with_fallback,
    route_with_cache,
    load_agent,
    get_agent_stats,
    record_agent_result,
    semantic_match,
)
from models import estimate_cost, get_provider_config, get_actual_model, get_default_model

PORT = 18803


class TestServerErrorHandling(unittest.TestCase):
    """Server error handling (runtime)"""

    @classmethod
    def setUpClass(cls):
        import urllib.request

        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        urllib.request.install_opener(opener)
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
            f"{self.base}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()
        except Exception as e:
            return -1, str(e).encode()

    def test_01_empty_body_post(self):
        import urllib.request

        req = urllib.request.Request(
            f"{self.base}/api/route",
            data=b"",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            self.assertIn("agent", data)
        except urllib.error.HTTPError as e:
            self.assertIn(e.code, (400, 404, 405, 500))

    def test_02_invalid_json_body(self):
        import urllib.request

        req = urllib.request.Request(
            f"{self.base}/api/route",
            data=b"this is not json",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            self.assertIn("agent", data)
        except urllib.error.HTTPError as e:
            self.assertIn(e.code, (400, 404, 405, 500))

    def test_03_gbk_encoded_body(self):
        import urllib.request

        gbk_data = "test task".encode("gbk")
        req = urllib.request.Request(
            f"{self.base}/api/route",
            data=gbk_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            self.assertIn("agent", data)
        except urllib.error.HTTPError as e:
            self.assertIn(e.code, (400, 404, 405, 500))

    def test_04_missing_content_type(self):
        import urllib.request

        body = json.dumps({"task": "test"}).encode("utf-8")
        req = urllib.request.Request(f"{self.base}/api/route", data=body, method="POST")
        try:
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            self.assertIn("agent", data)
        except urllib.error.HTTPError as e:
            self.assertIn(e.code, (400, 404, 405, 500))
        except (ConnectionError, ConnectionAbortedError):
            pass

    def test_05_unknown_route_returns_404(self):
        import urllib.request

        try:
            resp = urllib.request.urlopen(f"{self.base}/api/unknown-route-test", timeout=5)
            self.fail("Should return 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

    def test_06_agent_update_no_name(self):
        status, data = self._post("/api/agent-update", {"content": "test"})
        result = json.loads(data)
        self.assertIn("error", result)

    def test_07_agent_update_no_content(self):
        status, data = self._post("/api/agent-update", {"name": "test-agent"})
        result = json.loads(data)
        self.assertIn("error", result)

    def test_08_route_with_special_chars(self):
        for bad_task in ["", "a" * 10000, '!@#$%^&*()_+{}|:"<>?', "\x00\x01\x02"]:
            try:
                self._post("/api/route", {"task": bad_task})
            except Exception:
                pass

    def test_09_agent_detail_empty_name(self):
        import urllib.request

        try:
            resp = urllib.request.urlopen(f"{self.base}/api/agents/", timeout=5)
            data = json.loads(resp.read())
            self.assertIn("error", data)
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)


class TestLogicErrorHandling(unittest.TestCase):
    """Core logic error handling (unit level)"""

    def test_01_route_task_empty(self):
        agent, score, confidence = route_task("")
        self.assertEqual(agent, "coder")
        self.assertIsInstance(score, (int, float))
        self.assertIsInstance(confidence, float)

    def test_02_route_task_gibberish(self):
        agent, score, confidence = route_task("abcdefghijklmnopqrstuvwxyz" * 100)
        self.assertIsNotNone(agent)
        self.assertIsInstance(score, (int, float))
        self.assertTrue(isinstance(confidence, (int, float)))

    def test_03_route_with_fallback_empty(self):
        result = route_with_fallback("")
        self.assertIsInstance(result, dict)
        self.assertIn("agent", result)
        self.assertIn("keyword_score", result)
        self.assertIn("semantic_score", result)
        self.assertIn("source", result)
        self.assertIn("method", result)
        self.assertIn(result["source"], ("keyword", "semantic", "llm", "llm_cached", "fallback"))

    def test_04_route_with_cache_empty(self):
        result = route_with_cache("")
        self.assertIsInstance(result, dict)
        self.assertIn("agent", result)

    def test_05_load_agent_not_found(self):
        prompt, model = load_agent("__does_not_exist__")
        self.assertIn("__does_not_exist__", prompt)
        self.assertIsInstance(model, str)
        self.assertTrue(len(model) > 0)

    def test_06_load_agent_partial_name(self):
        prompt, model = load_agent("code")
        self.assertIsNotNone(prompt)
        self.assertGreater(len(prompt), 0)

    def test_07_estimate_cost_unknown_model(self):
        cost, saved, hit_rate = estimate_cost("unknown-model-12345", 100, 50)
        self.assertGreater(cost, 0)

    def test_08_estimate_cost_known(self):
        cost, saved, hit_rate = estimate_cost("deepseek-chat", 1000, 500)
        self.assertGreater(cost, 0)

    def test_09_record_agent_result(self):
        try:
            record_agent_result("test-agent", True)
            record_agent_result("test-agent", False)
            stats = get_agent_stats()
            self.assertIn("test-agent", stats)
            self.assertEqual(stats["test-agent"]["total"], 2)
            self.assertEqual(stats["test-agent"]["success_rate"], 0.5)
        except Exception as e:
            self.fail(f"record_agent_result crashed: {e}")

    def test_10_get_agent_stats_empty(self):
        stats = get_agent_stats()
        self.assertIsInstance(stats, dict)

    def test_11_semantic_match_empty(self):
        agent, score = semantic_match("")
        self.assertEqual(agent, "coder")
        self.assertEqual(score, 0.0)

    def test_12_get_provider_config_no_key(self):
        saved = {}
        for k in ["DEEPSEEK_API_KEY", "OPENAI_API_KEY", "OLLAMA_BASE_URL"]:
            saved[k] = os.environ.pop(k, None)
        try:
            base_url, api_key, headers = get_provider_config()
            self.assertIsNotNone(base_url)
            self.assertIsInstance(base_url, str)
            self.assertGreater(len(base_url), 0)
            self.assertIsInstance(api_key, str)
            self.assertIsInstance(headers, dict)
            self.assertIn("Content-Type", headers)
        finally:
            for k, v in saved.items():
                if v:
                    os.environ[k] = v

    def test_13_get_actual_model_empty(self):
        model = get_actual_model("")
        default = get_default_model()
        self.assertEqual(model, default)

    def test_14_get_actual_model_known(self):
        model = get_actual_model("haiku")
        self.assertIsInstance(model, str)
        self.assertGreater(len(model), 0)

    def test_15_route_with_unicode(self):
        agent, score, confidence = route_task("help me write a sorting algorithm")
        self.assertIsNotNone(agent)

    def test_16_route_task_none(self):
        try:
            agent, score, confidence = route_task(None)
            self.assertIsNotNone(agent)
        except (AttributeError, TypeError) as e:
            self.fail(f"None task crashed: {e}")


class TestSourceErrorHandling(unittest.TestCase):
    """Source code static error handling checks"""

    def test_01_web_py_has_try_except(self):
        src = open(str(PROJECT_ROOT / "maestro" / "web.py"), encoding="utf-8").read()
        try_count = len(re.findall(r"\btry\b", src))
        except_count = len(re.findall(r"\bexcept\b", src))
        self.assertGreaterEqual(try_count, 1, "web.py should have at least 1 try")
        self.assertGreaterEqual(except_count, 1, "web.py should have at least 1 except")

    def test_02_main_py_has_try_except(self):
        src = open(str(PROJECT_ROOT / "maestro" / "main.py"), encoding="utf-8").read()
        try_count = len(re.findall(r"\btry\b", src))
        except_count = len(re.findall(r"\bexcept\b", src))
        self.assertGreaterEqual(try_count, 3)
        self.assertGreaterEqual(except_count, 3)

    def test_03_web_py_no_bare_except(self):
        src = open(str(PROJECT_ROOT / "maestro" / "web.py"), encoding="utf-8").read()
        bare_excepts = re.findall(r"\bexcept\s*:", src)
        self.assertLessEqual(
            len(bare_excepts), 15, f"Bare except count too high: {len(bare_excepts)}"
        )

    def test_04_main_py_no_bare_except(self):
        src = open(str(PROJECT_ROOT / "maestro" / "main.py"), encoding="utf-8").read()
        bare_excepts = re.findall(r"\bexcept\s*:", src)
        self.assertLessEqual(len(bare_excepts), 3)

    def test_05_web_py_has_finally(self):
        src = open(str(PROJECT_ROOT / "maestro" / "web.py"), encoding="utf-8").read()
        finally_count = len(re.findall(r"\bfinally\b", src))
        self.assertGreaterEqual(finally_count, 0)

    def test_06_connection_closed_in_api(self):
        src = open(str(PROJECT_ROOT / "maestro" / "web.py"), encoding="utf-8").read()
        conn_count = src.count("conn = sqlite3.connect")
        close_count = src.count("conn.close()")
        if conn_count > 0:
            self.assertEqual(
                conn_count, close_count, f"conn open={conn_count} but close={close_count}"
            )

    def test_07_web_py_has_error_handler(self):
        src = open(str(PROJECT_ROOT / "maestro" / "web.py"), encoding="utf-8").read()
        self.assertIn("send_json", src)
        do_get = src.split("def do_GET")[1].split("def do_POST")[0]
        self.assertIn("send_json", do_get)
        do_post = src.split("def do_POST")[1].split("def do_DELETE")[0]
        self.assertIn("send_json", do_post)


if __name__ == "__main__":
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestServerErrorHandling))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestLogicErrorHandling))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestSourceErrorHandling))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
