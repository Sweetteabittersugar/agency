from __future__ import annotations

import pytest

from maestro import remote


def test_non_loopback_listener_requires_explicit_auth(monkeypatch):
    monkeypatch.delenv("AGENCY_TOKEN", raising=False)
    monkeypatch.setattr(remote, "_token", "")
    with pytest.raises(RuntimeError, match="non-loopback"):
        remote.require_remote_auth("0.0.0.0")


def test_non_loopback_listener_accepts_configured_auth(monkeypatch):
    monkeypatch.setattr(remote, "_token", "test-token")
    remote.require_remote_auth("0.0.0.0")
