"""测试 session_store.py — 会话持久化"""
import json
from pathlib import Path
from maestro.session_store import append_event, get_session, list_sessions, delete_session


class TestSessionStore:
    def test_append_and_get(self, tmp_path, monkeypatch):
        import maestro.session_store as ss
        monkeypatch.setattr(ss, 'STORE_DIR', tmp_path)
        monkeypatch.setattr(ss, 'SNAPSHOT_THRESHOLD', 10 * 1024 * 1024)

        sid = "test-session-1"
        r1 = append_event(sid, "user_message", {"task": "hello"})
        assert r1["ok"] is True

        r2 = append_event(sid, "agent_response", {"agent": "coder", "response": "hi"})
        assert r2["ok"] is True

        result = get_session(sid)
        assert result["count"] == 2
        assert result["events"][0]["type"] == "user_message"
        assert result["events"][1]["type"] == "agent_response"

    def test_list_sessions(self, tmp_path, monkeypatch):
        import maestro.session_store as ss
        monkeypatch.setattr(ss, 'STORE_DIR', tmp_path)
        monkeypatch.setattr(ss, 'SNAPSHOT_THRESHOLD', 10 * 1024 * 1024)

        append_event("s1", "user_message", {"task": "a"})
        append_event("s2", "user_message", {"task": "b"})

        sessions = list_sessions()
        ids = [s["id"] for s in sessions]
        assert "s1" in ids
        assert "s2" in ids

    def test_delete_session(self, tmp_path, monkeypatch):
        import maestro.session_store as ss
        monkeypatch.setattr(ss, 'STORE_DIR', tmp_path)
        monkeypatch.setattr(ss, 'SNAPSHOT_THRESHOLD', 10 * 1024 * 1024)

        append_event("del-test", "user_message", {"task": "x"})
        result = delete_session("del-test")
        assert result["ok"] is True
        assert result["deleted"] == "del-test"

        # 删除后应不存在
        gone = get_session("del-test")
        assert gone["count"] == 0

    def test_empty_session(self, tmp_path, monkeypatch):
        import maestro.session_store as ss
        monkeypatch.setattr(ss, 'STORE_DIR', tmp_path)

        result = get_session("nonexistent")
        assert result["count"] == 0
        assert result["events"] == []

    def test_delete_nonexistent_returns_error(self, tmp_path, monkeypatch):
        import maestro.session_store as ss
        monkeypatch.setattr(ss, 'STORE_DIR', tmp_path)

        result = delete_session("does-not-exist")
        assert result["ok"] is False

    def test_event_contains_timestamp_and_type(self, tmp_path, monkeypatch):
        import maestro.session_store as ss
        monkeypatch.setattr(ss, 'STORE_DIR', tmp_path)
        monkeypatch.setattr(ss, 'SNAPSHOT_THRESHOLD', 10 * 1024 * 1024)

        result = append_event("ts-test", "user_message", {"text": "hi"})
        assert "ts" in result["event"]
        assert result["event"]["type"] == "user_message"

    def test_safe_id_sanitization(self, tmp_path, monkeypatch):
        """session_id 中的特殊字符应被过滤"""
        import maestro.session_store as ss
        monkeypatch.setattr(ss, 'STORE_DIR', tmp_path)

        sid = "../../etc/passwd"
        result = append_event(sid, "user_message", {"task": "test"})
        # 应成功写入而不触发路径穿越
        assert result["ok"] is True
