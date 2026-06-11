"""测试 permission_engine.py — 权限引擎"""
import pytest
from maestro.permission_engine import PermissionEngine, get_engine


class TestPermissionEngine:
    def test_init_default_db_path(self):
        """默认构造器不要求 db_path"""
        engine = PermissionEngine()
        assert engine._db_path is None

    def test_classify_auto_allow_read(self):
        """Read 属于 AUTO_ALLOW，应返回 allow"""
        engine = PermissionEngine()
        decision, risk, reason = engine.classify("Read", {"path": "/tmp/test.txt"})
        assert decision == "allow"
        assert risk == "low"

    def test_classify_auto_allow_grep(self):
        """Grep 属于 AUTO_ALLOW"""
        engine = PermissionEngine()
        decision, risk, reason = engine.classify("Grep", {"pattern": "test"})
        assert decision == "allow"

    def test_classify_ask_once_write(self):
        """Write 属于 ASK_ONCE，应返回 ask"""
        engine = PermissionEngine()
        decision, risk, reason = engine.classify("Write", {"path": "/tmp/test.txt"})
        assert decision == "ask"
        assert risk == "medium"

    def test_classify_always_deny_rm_rf(self):
        """rm -rf / 在任何模式下都应 deny"""
        engine = PermissionEngine()
        decision, risk, reason = engine.classify("Bash", {"command": "rm -rf /"})
        assert decision == "deny"
        assert risk == "high"

    def test_classify_always_deny_sudo(self):
        """sudo 命令应 deny"""
        engine = PermissionEngine()
        decision, risk, reason = engine.classify("Bash", {"command": "sudo apt install"})
        assert decision == "deny"

    def test_classify_unknown_tool_returns_ask(self):
        """未分类工具默认 ask"""
        engine = PermissionEngine()
        decision, risk, reason = engine.classify("SomeUnknownTool", {})
        assert decision == "ask"

    def test_apply_trust_mode_trusted_auto_allow(self):
        """trusted 模式下 ask 应转为 allow"""
        engine = PermissionEngine()
        decision, note = engine.apply_trust_mode("ask", "trusted", "Write", "/tmp/")
        assert decision == "allow"

    def test_apply_trust_mode_cautious_keeps_ask(self):
        """cautious 模式下 ask 保持 ask"""
        engine = PermissionEngine()
        decision, note = engine.apply_trust_mode("ask", "cautious", "Write", "/tmp/")
        assert decision == "ask"

    def test_apply_trust_mode_normal_keeps_ask_without_memory(self):
        """normal 模式下无记忆时 ask 保持 ask"""
        engine = PermissionEngine()
        decision, note = engine.apply_trust_mode("ask", "normal", "Write", "/tmp/")
        assert decision == "ask"

    def test_remember_and_check_memory(self):
        """记住后 check_memory 应返回 True"""
        engine = PermissionEngine()
        engine.remember("Write", "/tmp/test.txt")
        assert engine.check_memory("Write", "/tmp/test.txt") is True

    def test_forget_memory(self):
        """forget 后 check_memory 应返回 False"""
        engine = PermissionEngine()
        engine.remember("Write", "/tmp/test.txt")
        engine.forget("Write", "/tmp/test.txt")
        assert engine.check_memory("Write", "/tmp/test.txt") is False

    def test_memory_is_stored(self):
        """验证 _memories 字典有数据"""
        engine = PermissionEngine()
        engine.remember("Read", "/tmp/a.txt")
        assert len(engine._memories) > 0

    def test_apply_trust_mode_deny_stays_deny(self):
        """即使是 trusted 模式，deny 仍保持 deny"""
        engine = PermissionEngine()
        decision, note = engine.apply_trust_mode("deny", "trusted", "Bash", "")
        assert decision == "deny"

    def test_check_and_log_returns_tuple(self):
        """check_and_log 返回 (decision, risk, reason) 三元组"""
        engine = PermissionEngine()
        result = engine.check_and_log("Read", {"path": "/tmp/x.txt"})
        assert len(result) == 3
        decision, risk, reason = result
        assert decision in ("allow", "ask", "deny")

    def test_get_stats_counts(self):
        """log_audit 应正确累计统计"""
        engine = PermissionEngine()
        engine.log_audit("Read", "allow")
        engine.log_audit("Write", "ask")
        engine.log_audit("Bash", "deny")
        stats = engine.get_stats()
        assert stats["allowed"] >= 1
        assert stats["asked"] >= 1
        assert stats["denied"] >= 1


class TestGetEngine:
    def test_get_engine_returns_instance(self):
        engine = get_engine()
        assert isinstance(engine, PermissionEngine)

    def test_get_engine_is_singleton(self):
        e1 = get_engine()
        e2 = get_engine()
        assert e1 is e2
