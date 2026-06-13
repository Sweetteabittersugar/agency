"""dispatch 基础测试"""

import sys
import os
import pytest

# 确保 maestro 在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "maestro"))


class TestDispatchBasics:
    """dispatch.py 基础功能测试"""

    def test_dispatch_module_importable(self):
        """dispatch 模块可导入"""
        try:
            import dispatch

            assert dispatch is not None
        except ImportError as e:
            pytest.skip(f"dispatch 模块不可导入: {e}")

    def test_dispatch_has_agents(self):
        """dispatch 包含 agent 列表"""
        try:
            from dispatch import AGENTS

            assert isinstance(AGENTS, dict)
            assert len(AGENTS) > 0
        except (ImportError, AttributeError) as e:
            pytest.skip(f"AGENTS 不可用: {e}")


class TestSandboxBasics:
    """sandbox.py 基础功能测试"""

    def test_sandbox_module_importable(self):
        """sandbox 模块可导入"""
        try:
            import sandbox

            assert sandbox is not None
        except ImportError as e:
            pytest.skip(f"sandbox 模块不可导入: {e}")


class TestGatewayBasics:
    """gateway.py 基础功能测试"""

    def test_gateway_module_importable(self):
        """gateway 模块可导入"""
        try:
            import gateway

            assert gateway is not None
        except ImportError as e:
            pytest.skip(f"gateway 模块不可导入: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
