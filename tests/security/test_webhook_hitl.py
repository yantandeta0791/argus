"""v0.7 webhook HITL tests (HITL-06)."""

from __future__ import annotations

import json

import pytest

from argus.security.exceptions import ApprovalDeniedError
from argus.security.hitl import HITLConfig, HITLGate


class _Response:
    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_webhook_approve_bypasses_terminal_input(monkeypatch):
    cfg = HITLConfig(
        require_approval={"deploy": True},
        webhook_url="https://approval.example.test/argus",
        webhook_secret="test-secret",
    )
    captured = {}

    def fake_urlopen(request, timeout):
        captured["body"] = request.data
        captured["signature"] = request.headers.get("X-argus-signature")
        return _Response(b'{"decision":"approve"}')

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    HITLGate(cfg).check("deploy", {"env": "prod"}, provenance="user_originated")

    assert captured["signature"].startswith("sha256=")
    assert json.loads(captured["body"])["tool_name"] == "deploy"


def test_webhook_deny_fails_closed(monkeypatch):
    cfg = HITLConfig(
        require_approval={"deploy": True}, webhook_url="https://approval.example.test"
    )
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *a, **kw: _Response(b'{"decision":"deny"}')
    )
    with pytest.raises(ApprovalDeniedError, match="webhook_denied"):
        HITLGate(cfg).check("deploy", {})


def test_webhook_transport_failure_fails_closed(monkeypatch):
    cfg = HITLConfig(
        require_approval={"deploy": True}, webhook_url="https://approval.example.test"
    )
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **kw: (_ for _ in ()).throw(OSError("down")),
    )
    with pytest.raises(ApprovalDeniedError, match="webhook_unavailable"):
        HITLGate(cfg).check("deploy", {})
