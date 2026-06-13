#!/usr/bin/env python3
"""
Test 1: API endpoints for Agency
"""

import sys
import json
import time
import threading
import unittest
from http.server import HTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "maestro"))
from web import Handler, AGENCY_VERSION

PORT = 18801


class TestAPIEndpoints(unittest.TestCase):
    """All API endpoint availability tests"""

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

    def test_01_root_html(self):
        status, data = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn(b"<!DOCTYPE html>", data)
        self.assertIn(b"Agency", data)

    def test_02_api_agents(self):
        status, data = self._get("/api/agents")
        self.assertEqual(status, 200)
        agents = json.loads(data)
        self.assertIsInstance(agents, list)
        self.assertGreater(len(agents), 0)
        for a in agents:
            self.assertIn("name", a)
            self.assertIn("description", a)
            self.assertIn("model", a)

    def test_03_api_cost(self):
        status, data = self._get("/api/cost")
        self.assertEqual(status, 200)
        cost_data = json.loads(data)
        self.assertIn("total", cost_data)
        self.assertIn("today", cost_data)
        self.assertIn("by_date", cost_data)
        self.assertIn("by_model", cost_data)

    def test_04_api_cost_summary(self):
        status, data = self._get("/api/cost/summary")
        self.assertEqual(status, 200)
        summary = json.loads(data)
        self.assertIn("today", summary)
        self.assertIn("this_month", summary)
        self.assertIn("alerts", summary)

    def test_05_api_settings(self):
        status, data = self._get("/api/settings")
        self.assertEqual(status, 200)
        settings = json.loads(data)
        self.assertIn("claude_bin", settings)
        self.assertIn("config_dir", settings)
        self.assertIn("has_api_key", settings)
        self.assertIn("version", settings)

    def test_06_api_version(self):
        status, data = self._get("/api/version")
        self.assertEqual(status, 200)
        ver_data = json.loads(data)
        self.assertIn("version", ver_data)
        self.assertEqual(ver_data["version"], AGENCY_VERSION)

    def test_07_api_agent_detail(self):
        status, data = self._get("/api/agents/coder")
        self.assertEqual(status, 200)
        content = json.loads(data)
        self.assertIn("name", content)
        self.assertIn("content", content)
        self.assertEqual(content["name"], "coder")

    def test_08_api_agent_detail_not_found(self):
        status, data = self._get("/api/agents/nonexistent")
        self.assertEqual(status, 404)
        content = json.loads(data)
        self.assertIn("error", content)

    def test_09_api_skills(self):
        status, data = self._get("/api/skills")
        self.assertEqual(status, 200)
        skills = json.loads(data)
        self.assertIsInstance(skills, list)

    def test_10_api_mcp_status(self):
        status, data = self._get("/api/mcp/status")
        self.assertEqual(status, 200)
        mcp = json.loads(data)
        self.assertIn("servers", mcp)

    def test_11_api_profiles(self):
        status, data = self._get("/api/profiles")
        self.assertEqual(status, 200)
        profiles = json.loads(data)
        self.assertIn("profiles", profiles)

    def test_12_api_health(self):
        status, data = self._get("/api/health")
        self.assertEqual(status, 200)
        health = json.loads(data)
        self.assertIn("status", health)
        self.assertEqual(health["status"], "ok")
        self.assertIn("uptime", health)

    def test_13_404(self):
        status, _ = self._get("/api/nonexistent")
        self.assertEqual(status, 404)

    def test_14_post_route(self):
        status, data = self._post("/api/route", {"task": "test"})
        self.assertEqual(status, 200)
        route_data = json.loads(data)
        self.assertIn("agent", route_data)
        self.assertIn("keyword_score", route_data)
        self.assertIn("semantic_score", route_data)
        self.assertIn("confidence", route_data)
        self.assertIn("source", route_data)
        self.assertIn("method", route_data)
        self.assertIn("category", route_data)

    def test_15_post_route_force_agent(self):
        status, data = self._post("/api/route", {"task": "test", "force_agent": "explorer"})
        self.assertEqual(status, 200)
        route_data = json.loads(data)
        self.assertEqual(route_data["agent"], "explorer")
        self.assertEqual(route_data["source"], "force")

    def test_16_post_route_force_invalid(self):
        status, data = self._post("/api/route", {"task": "test", "force_agent": "doesnotexist"})
        self.assertEqual(status, 200)
        route_data = json.loads(data)
        self.assertEqual(route_data["agent"], "doesnotexist")
        self.assertEqual(route_data["source"], "force")

    def test_17_post_route_empty_task(self):
        status, data = self._post("/api/route", {"task": ""})
        self.assertEqual(status, 200)
        route_data = json.loads(data)
        self.assertIn("agent", route_data)

    def test_18_post_chat_empty_task(self):
        status, data = self._post("/api/chat", {"messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(status, 400)
        resp = json.loads(data)
        self.assertIn("error", resp)

    def test_19_post_agent_update_save(self):
        coder_file = PROJECT_ROOT / "agents" / "coder.md"
        original = coder_file.read_text(encoding="utf-8")
        status, data = self._post("/api/agent-update", {"name": "coder", "content": original})
        self.assertEqual(status, 200)
        result = json.loads(data)
        self.assertTrue(result.get("ok", False))
        saved = coder_file.read_text(encoding="utf-8")
        self.assertEqual(saved, original)

    def test_20_post_agent_update_no_name(self):
        status, data = self._post("/api/agent-update", {"content": "test"})
        self.assertEqual(status, 400)
        result = json.loads(data)
        self.assertIn("error", result)

    def test_21_post_agent_update_no_content(self):
        status, data = self._post("/api/agent-update", {"name": "test-agent"})
        self.assertEqual(status, 400)
        result = json.loads(data)
        self.assertIn("error", result)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAPIEndpoints)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
