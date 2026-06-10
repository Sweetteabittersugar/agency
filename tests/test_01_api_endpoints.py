#!/usr/bin/env python3
"""
Test 1: API端点可用性测试
启动 web.py 服务，检查所有 API 端点是否正常响应。
"""
import sys
import os
import json
import time
import threading
import unittest
from http.server import HTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "maestro"))

# 导入 web handler
from web import Handler, HTML, AGENCY_VERSION

PORT = 18801


class TestAPIEndpoints(unittest.TestCase):
    """所有 API 端点可用性测试"""

    @classmethod
    def setUpClass(cls):
        """启动服务器"""
        import urllib.request
        # 绕过系统代理（SOCKS4 不被 urllib 原生支持）
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

    def _get(self, path):
        import urllib.request
        try:
            resp = urllib.request.urlopen(f"{self.base}{path}", timeout=5)
            return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()
        except Exception as e:
            return -1, str(e).encode()

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

    # ── GET 端点 ─────────────────────────────────

    def test_01_root_html(self):
        """GET / — 返回 HTML 首页"""
        status, data = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn(b"<!DOCTYPE html>", data)
        self.assertIn(b"Agency", data)

    def test_02_api_agents(self):
        """GET /api/agents — 返回 Agent 列表"""
        status, data = self._get("/api/agents")
        self.assertEqual(status, 200)
        agents = json.loads(data)
        self.assertIsInstance(agents, list)
        self.assertGreater(len(agents), 0)
        # 检查必要的字段
        for a in agents:
            self.assertIn("name", a)
            self.assertIn("description", a)
            self.assertIn("model", a)

    def test_03_api_cost(self):
        """GET /api/cost — 返回费用统计"""
        status, data = self._get("/api/cost")
        self.assertEqual(status, 200)
        cost_data = json.loads(data)
        self.assertIn("total_calls", cost_data)
        self.assertIn("total_cost", cost_data)
        self.assertIn("by_model", cost_data)

    def test_04_api_cost_recent(self):
        """GET /api/cost-recent — 返回最近调用"""
        status, data = self._get("/api/cost-recent")
        self.assertEqual(status, 200)
        rows = json.loads(data)
        self.assertIsInstance(rows, list)

    def test_05_api_settings(self):
        """GET /api/settings — 返回设置信息"""
        status, data = self._get("/api/settings")
        self.assertEqual(status, 200)
        settings = json.loads(data)
        self.assertIn("provider_type", settings)
        self.assertIn("has_key", settings)
        self.assertIn("model_mapping", settings)

    def test_06_api_version(self):
        """GET /api/version — 返回版本号"""
        status, data = self._get("/api/version")
        self.assertEqual(status, 200)
        ver_data = json.loads(data)
        self.assertIn("version", ver_data)
        self.assertEqual(ver_data["version"], AGENCY_VERSION)

    def test_07_api_agent_content(self):
        """GET /api/agent-content?name=coder — 返回 Agent 内容"""
        status, data = self._get("/api/agent-content?name=coder")
        self.assertEqual(status, 200)
        content = json.loads(data)
        self.assertIn("name", content)
        self.assertIn("content", content)
        self.assertEqual(content["name"], "coder")

    def test_08_api_agent_content_not_found(self):
        """GET /api/agent-content?name=nonexistent — 返回 error"""
        status, data = self._get("/api/agent-content?name=nonexistent")
        self.assertEqual(status, 200)
        content = json.loads(data)
        self.assertIn("error", content)

    def test_09_api_agent_stats(self):
        """GET /api/agent-stats — 返回 Agent 统计"""
        status, data = self._get("/api/agent-stats")
        self.assertEqual(status, 200)
        stats = json.loads(data)
        self.assertIsInstance(stats, dict)

    def test_10_404(self):
        """GET /api/nonexistent — 返回 404"""
        status, _ = self._get("/api/nonexistent")
        self.assertEqual(status, 404)

    # ── POST 端点 ────────────────────────────────

    def test_11_post_route(self):
        """POST /api/route — 路由测试"""
        status, data = self._post("/api/route", {"task": "帮我写一个排序函数"})
        self.assertEqual(status, 200)
        route_data = json.loads(data)
        self.assertIn("agent", route_data)
        self.assertIn("score", route_data)
        self.assertIn("confidence", route_data)
        self.assertIn("model", route_data)

    def test_12_post_route_force_agent(self):
        """POST /api/route with force_agent — 强制指定 Agent"""
        status, data = self._post("/api/route", {"task": "测试", "force_agent": "explorer"})
        self.assertEqual(status, 200)
        route_data = json.loads(data)
        self.assertEqual(route_data["agent"], "explorer")
        self.assertTrue(route_data["direct"])

    def test_13_post_route_force_invalid(self):
        """POST /api/route with invalid force_agent — 返回 error"""
        status, data = self._post("/api/route", {"task": "测试", "force_agent": "doesnotexist"})
        self.assertEqual(status, 200)
        route_data = json.loads(data)
        self.assertIn("error", route_data)

    def test_14_post_route_test(self):
        """POST /api/route-test — 路由测试（全量排名）"""
        status, data = self._post("/api/route-test", {"task": "帮我审查这段代码的安全性"})
        self.assertEqual(status, 200)
        results = json.loads(data)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertIn("agent", results[0])
        self.assertIn("score", results[0])

    def test_15_post_stat(self):
        """POST /api/stat — 统计查询"""
        status, data = self._post("/api/stat", {"task": "test", "agent": "coder"})
        self.assertEqual(status, 200)
        stat_data = json.loads(data)
        self.assertIn("elapsed", stat_data)
        self.assertIn("cost", stat_data)

    def test_16_post_agent_save(self):
        """POST /api/agent-save — Agent 保存（原地读回验证）"""
        # 先读取原内容
        coder_file = PROJECT_ROOT / "agents" / "coder.md"
        original = coder_file.read_text(encoding="utf-8")
        # 保存相同内容
        status, data = self._post("/api/agent-save", {"name": "coder", "content": original})
        self.assertEqual(status, 200)
        result = json.loads(data)
        self.assertTrue(result["ok"])
        # 验证内容未变
        saved = coder_file.read_text(encoding="utf-8")
        self.assertEqual(saved, original)

    def test_17_post_config_reload(self):
        """POST /api/config-reload — 配置重载"""
        status, data = self._post("/api/config-reload")
        self.assertEqual(status, 200)
        result = json.loads(data)
        self.assertIn("ok", result)

    def test_18_post_route_empty_task(self):
        """POST /api/route with empty task — 应返回默认路由"""
        status, data = self._post("/api/route", {"task": ""})
        self.assertEqual(status, 200)
        route_data = json.loads(data)
        self.assertIn("agent", route_data)

    def test_19_post_stat_empty(self):
        """POST /api/stat with empty fields — 不应崩溃"""
        status, data = self._post("/api/stat", {})
        self.assertEqual(status, 200)
        stat_data = json.loads(data)
        self.assertIn("elapsed", stat_data)

    def test_20_chat_missing_key(self):
        """POST /api/chat without API key — 返回错误"""
        status, data = self._post("/api/chat", {"messages": [{"role": "user", "content": "hi"}]})
        # 没有 key 时 /api/chat 返回 SSE 或 error
        resp_text = data.decode("utf-8", errors="replace")
        # 只要不崩溃就算通过
        self.assertIn(status, (200,), msg=f"Status: {status}")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAPIEndpoints)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
