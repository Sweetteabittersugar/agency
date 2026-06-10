"""pytest 共享 fixtures"""
import pytest
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_dir():
    """临时目录，测试后自动清理"""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_agent_md():
    """示例 Agent Markdown 内容"""
    return """---
name: test-agent
description: "测试 Agent。用于测试场景。典型输入: \"测试\"。不适合生产环境。"
model: haiku
tools: [Read, Grep, Glob]
skills: []
memory: project
permissionMode: default
maxTurns: 5
---

# 测试 Agent

## 职责
仅用于单元测试。
"""


@pytest.fixture
def mock_handler():
    """模拟 HTTP 请求处理器"""
    class MockHandler:
        def __init__(self):
            self.status = 200
            self.response = None
            self.headers = {}
            self.body = "{}"
            self.client_address = ("127.0.0.1", 12345)
            self.path = "/api/test"

        def send_json(self, data, status=200):
            self.response = data
            self.status = status

        def send_response(self, code):
            self.status = code

        def send_header(self, key, value):
            self.headers[key] = value

        def end_headers(self):
            pass

    return MockHandler()
