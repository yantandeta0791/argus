"""Public gateway-seam tests for policy shadow decisions."""

from __future__ import annotations

import pytest

from argus.security.exceptions import PermissionDeniedError, ProvenanceViolationError
from argus.security.gateway import GatewayConfig, SecurityGateway
from argus.security.provenance import Provenance, reset_provenance, set_provenance


class CaptureAudit:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    def send(self, payload: dict) -> None:
        self.sent.append(payload)


def make_gateway(**config_kwargs) -> tuple[SecurityGateway, CaptureAudit]:
    audit = CaptureAudit()
    config = GatewayConfig(policy_metadata={"policy_hash": "policy-abc"}, **config_kwargs)
    return SecurityGateway(config=config, audit_logger=audit), audit


def policy_decisions(audit: CaptureAudit) -> list[dict]:
    return [event for event in audit.sent if event.get("event_type") == "policy_decision"]


def test_shadow_provenance_mismatch_records_would_block_and_allows():
    gateway, audit = make_gateway(
        policy_mode="shadow",
        provenance_required={"export_data": "user_originated"},
    )
    tokens = set_provenance(Provenance.UNTRUSTED_RETRIEVAL)
    try:
        assert gateway.pre_tool_call(
            "agent", "export_data", {}, caller_id="caller-1", hop_depth=2
        ) == {}
    finally:
        reset_provenance(tokens)

    event = policy_decisions(audit)[0]
    assert event["outcome"] == "would_block"
    assert event["gate"] == "provenance"
    assert event["policy_hash"] == "policy-abc"
    assert event["decision_id"]
    assert event["caller_id"] == "caller-1"
    assert event["hop_depth"] == 2
    assert event["provenance"] == "untrusted_retrieval"


def test_enforce_provenance_mismatch_still_raises():
    gateway, audit = make_gateway(
        policy_mode="enforce",
        provenance_required={"export_data": "user_originated"},
    )
    tokens = set_provenance(Provenance.UNTRUSTED_RETRIEVAL)
    try:
        with pytest.raises(ProvenanceViolationError):
            gateway.pre_tool_call("agent", "export_data", {})
    finally:
        reset_provenance(tokens)

    assert policy_decisions(audit)[0]["outcome"] == "block"
