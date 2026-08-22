"""Tests for Phase 12 provenance enforcement (PROV-03..07)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from argus.security.exceptions import PermissionDeniedError, ProvenanceViolationError
from argus.security.gateway import GatewayConfig, SecurityGateway
from argus.security.provenance import (
    Provenance,
    reset_provenance,
    set_provenance,
)


class _CaptureAudit:
    def __init__(self):
        self.sent = []

    def send(self, payload):
        self.sent.append(payload)


def _make_gateway(provenance_required=None) -> SecurityGateway:
    config = GatewayConfig(provenance_required=provenance_required)
    return SecurityGateway(config=config, audit_logger=_CaptureAudit())


# ---------------------------------------------------------------- Gate 0.75


def test_gate075_blocks_untrusted_provenance_on_restricted_tool():
    gw = _make_gateway({"export_data": "user_originated"})
    tokens = set_provenance(Provenance.UNTRUSTED_RETRIEVAL)
    try:
        with pytest.raises(ProvenanceViolationError) as exc_info:
            gw.pre_tool_call("agent", "export_data", {})
        assert exc_info.value.provenance == "untrusted_retrieval"
        assert exc_info.value.required == "user_originated"
    finally:
        reset_provenance(tokens)


def test_gate075_allows_user_originated_on_restricted_tool():
    gw = _make_gateway({"export_data": "user_originated"})
    # default provenance is user_originated — no context set needed
    assert gw.pre_tool_call("agent", "export_data", {}) == {}


def test_gate075_fires_before_permission_check():
    """PROV-04: mismatch raises ProvenanceViolationError even when permission
    would also deny — provenance gate runs first."""

    class DenyAll:
        def enforce(self, role, tool):
            raise PermissionDeniedError(gate="permission", blocked=tool, rule="r")

    gw = _make_gateway({"export_data": "user_originated"})
    gw._permission = DenyAll()
    tokens = set_provenance(Provenance.UNTRUSTED_RETRIEVAL)
    try:
        with pytest.raises(ProvenanceViolationError):
            gw.pre_tool_call("agent", "export_data", {})
    finally:
        reset_provenance(tokens)


def test_gate075_ignores_unrestricted_tools():
    gw = _make_gateway({"export_data": "user_originated"})
    tokens = set_provenance(Provenance.SYSTEM)
    try:
        # different tool, no declaration — allowed under any provenance
        assert gw.pre_tool_call("agent", "search", {}) == {}
    finally:
        reset_provenance(tokens)


def test_gate075_any_declaration_accepts_everything():
    gw = _make_gateway({"search": "any"})
    for prov in Provenance:
        tokens = set_provenance(prov)
        try:
            assert gw.pre_tool_call("agent", "search", {}) == {}
        finally:
            reset_provenance(tokens)


# ---------------------------------------------------------------- PROV-05


def test_audit_pre_call_carries_provenance():
    gw = _make_gateway()
    tokens = set_provenance(Provenance.UNTRUSTED_RETRIEVAL)
    try:
        gw.pre_tool_call("agent", "search", {})
        payload = gw._audit.sent[-1]
        assert payload["event_type"] == "tool_call_pre"
        assert payload["provenance"] == "untrusted_retrieval"
    finally:
        reset_provenance(tokens)


# ---------------------------------------------------------------- PROV-06


def test_hitl_banner_shows_provenance_when_not_user_originated(capsys):
    from argus.security.hitl import HITLConfig, HITLGate

    with patch(
        "argus.security.hitl.HITLGate._read_with_timeout", return_value="approve"
    ):
        HITLGate(HITLConfig(require_approval={"export": True})).check(
            tool_name="export",
            tool_input={},
            provenance="untrusted_retrieval",
        )
    out = capsys.readouterr().out
    assert "Provenance: untrusted_retrieval" in out


def test_hitl_banner_unchanged_when_user_originated(capsys):
    from argus.security.hitl import HITLConfig, HITLGate

    with patch(
        "argus.security.hitl.HITLGate._read_with_timeout", return_value="approve"
    ):
        HITLGate(HITLConfig(require_approval={"export": True})).check(
            tool_name="export",
            tool_input={},
            provenance="user_originated",
        )
    out = capsys.readouterr().out
    assert "Provenance:" not in out


def test_hitl_banner_omits_line_when_provenance_none(capsys):
    """Backward compat: no provenance kwarg → v0.4 output unchanged."""
    from argus.security.hitl import HITLConfig, HITLGate

    with patch(
        "argus.security.hitl.HITLGate._read_with_timeout", return_value="approve"
    ):
        HITLGate(HITLConfig(require_approval={"export": True})).check(
            tool_name="export",
            tool_input={},
        )
    out = capsys.readouterr().out
    assert "Provenance:" not in out


# ---------------------------------------------------------------- PROV-03


def test_load_gateway_config_parses_provenance_required():
    from argus.llm.config import load_gateway_config

    raw = {"tools": {"export_data": {"provenance_required": "user_originated"}}}
    cfg = load_gateway_config(raw)
    assert cfg.provenance_required == {"export_data": "user_originated"}


def test_load_gateway_config_rejects_invalid_provenance_value():
    from argus.llm.config import load_gateway_config
    from argus.security.exceptions import ConfigValidationError

    raw = {"tools": {"export_data": {"provenance_required": "sometimes"}}}
    with pytest.raises(ConfigValidationError, match="export_data"):
        load_gateway_config(raw)


def test_load_gateway_config_accepts_any_keyword():
    from argus.llm.config import load_gateway_config

    raw = {"tools": {"search": {"provenance_required": "any"}}}
    cfg = load_gateway_config(raw)
    assert cfg.provenance_required == {"search": "any"}


# ---------------------------------------------------------------- PROV-07


def _rest_client(gateway):
    from fastapi.testclient import TestClient

    from argus.cli.serve import build_app

    app = build_app(gateway)
    return TestClient(app)


def test_rest_default_provenance_is_user_originated():
    gw = _make_gateway({"export_data": "user_originated"})
    client = _rest_client(gw)
    resp = client.post(
        "/tool-call",
        json={"agent_role": "agent", "tool_name": "export_data", "tool_input": {}},
    )
    assert resp.status_code == 200  # omitted field defaults to user_originated


def test_rest_untrusted_provenance_blocked_at_gate075():
    gw = _make_gateway({"export_data": "user_originated"})
    client = _rest_client(gw)
    resp = client.post(
        "/tool-call",
        json={
            "agent_role": "agent",
            "tool_name": "export_data",
            "tool_input": {},
            "provenance": "untrusted_retrieval",
        },
    )
    assert resp.status_code == 403
    assert resp.json()["violation"] == "provenance"


def test_rest_unknown_provenance_returns_422():
    gw = _make_gateway()
    client = _rest_client(gw)
    resp = client.post(
        "/tool-call",
        json={
            "agent_role": "agent",
            "tool_name": "search",
            "tool_input": {},
            "provenance": "not_a_real_value",
        },
    )
    assert resp.status_code == 422
