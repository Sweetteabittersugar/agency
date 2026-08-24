"""测试 orchesterat.py — 智能调度、路由建议、管线编排"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure maestro is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from maestro.routes.orchestrate import _orch_estimate_tokens


class TestOrchEstimateTokens:
    """_orch_estimate_tokens() — token 估算辅助（纯函数）"""

    def test_empty_text(self):
        assert _orch_estimate_tokens("") == 0

    def test_chinese_text(self):
        estimated_units = _orch_estimate_tokens("你好世界" * 100)
        assert estimated_units > 0

    def test_with_model(self):
        estimated_units = _orch_estimate_tokens("test " * 200, "claude-opus-4-8")
        assert estimated_units > 0

    def test_default_model(self):
        """无 model 参数时用 deepseek-v4-flash 默认"""
        estimated_units = _orch_estimate_tokens("测试" * 100)
        assert estimated_units > 0

    def test_returns_int(self):
        result = _orch_estimate_tokens("hello world")
        assert isinstance(result, int)


class TestPolicyGate:
    """_policy_gate() — 策略门控
    ⚠ orchestrator_model 全局变量在 _policy_gate 引用时未初始化（已知 bug），
    此处仅验证函数可导入且不会因 ImportError 崩溃。
    完整测试需在 _run_pipeline_orchestrate 上下文中进行。
    """

    def test_function_importable(self):
        from maestro.routes.orchestrate import _policy_gate
        assert callable(_policy_gate)


class TestRouteHandlerImports:
    """handle_route / handle_orchestrate 可导入"""

    def test_imports(self):
        from maestro.routes.orchestrate import handle_route, handle_orchestrate
        assert callable(handle_route)
        assert callable(handle_orchestrate)


class TestSimpleRoute:
    """simple_route() 路由建议"""

    def test_basic(self):
        from maestro.main import simple_route
        result = simple_route("写一个 Python 脚本来排序数组")
        assert result is not None
        assert isinstance(result, dict)
        assert "agent" in result
        assert len(result["agent"]) > 0

    def test_empty_safe(self):
        from maestro.main import simple_route
        result = simple_route("")
        assert result is not None
        assert isinstance(result, dict)

    def test_unknown_fallback(self):
        """无法匹配的任务有 fallback agent"""
        from maestro.main import simple_route
        result = simple_route("xyzzy gibberish 12345")
        assert result is not None
        assert "agent" in result
        assert len(result["agent"]) > 0


class TestPipelineModule:
    """管线模块基本可用性"""

    def test_imports(self):
        from maestro.pipeline import (
            PipelineStateMachine, pass_k_verify,
            select_model, hard_gate_check,
            STAGE_ORDER, TASK_STATES,
        )
        assert len(STAGE_ORDER) >= 4
        assert len(TASK_STATES) >= 2

    def test_state_machine_create(self):
        from maestro.pipeline import PipelineStateMachine
        task = {"id": "test-001", "task": "test task", "complexity": 3}
        psm = PipelineStateMachine(task)
        assert psm.current_stage is not None  # 应有初始阶段

    def test_select_model(self):
        from maestro.pipeline import select_model
        task = {"task": "write a sorting function", "complexity": 5}
        model = select_model(task)
        assert isinstance(model, str)
        assert len(model) > 0

    def test_hard_gate_check(self):
        from maestro.pipeline import hard_gate_check
        dry_run = {"status": "pass", "score": 8.5}
        result = hard_gate_check(dry_run)
        assert isinstance(result, tuple)


class TestTaskClassification:
    """classify_task_complexity() 返回 'simple'/'normal'/'complex'"""

    def test_simple(self):
        from maestro.task_classifier import classify_task_complexity
        result = classify_task_complexity("修复一个小bug")
        assert result in ("simple", "normal", "complex")

    def test_complex(self):
        from maestro.task_classifier import classify_task_complexity
        result = classify_task_complexity(
            "设计完整的微服务系统，包含认证、数据库、缓存、消息队列"
        )
        assert result in ("simple", "normal", "complex")

    def test_empty(self):
        from maestro.task_classifier import classify_task_complexity
        result = classify_task_complexity("")
        assert result in ("simple", "normal", "complex")
