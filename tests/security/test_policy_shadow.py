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
    config = GatewayConfig(
        policy_metadata={"policy_hash": "policy-abc"}, **config_kwargs
    )
    return SecurityGateway(config=config, audit_logger=audit), audit


def policy_decisions(audit: CaptureAudit) -> list[dict]:
    return [
        event for event in audit.sent if event.get("event_type") == "policy_decision"
    ]


def test_shadow_provenance_mismatch_records_would_block_and_allows():
    gateway, audit = make_gateway(
        policy_mode="shadow",
        provenance_required={"export_data": "user_originated"},
    )
    tokens = set_provenance(Provenance.UNTRUSTED_RETRIEVAL)
    try:
        assert (
            gateway.pre_tool_call(
                "agent", "export_data", {}, caller_id="caller-1", hop_depth=2
            )
            == {}
        )
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


def test_shadow_permission_denial_records_would_block_and_allows():
    gateway, audit = make_gateway(
        policy_mode="shadow",
        permissions={
            "rules": [{"role": "analyst", "tool": "export_data", "effect": "deny"}]
        },
    )
    assert gateway.pre_tool_call("analyst", "export_data", {}) == {}
    event = policy_decisions(audit)[0]
    assert event["outcome"] == "would_block"
    assert event["gate"] == "permission"


def test_enforce_permission_denial_still_raises():
    gateway, audit = make_gateway(
        policy_mode="enforce",
        permissions={
            "rules": [{"role": "analyst", "tool": "export_data", "effect": "deny"}]
        },
    )
    with pytest.raises(PermissionDeniedError):
        gateway.pre_tool_call("analyst", "export_data", {})
    assert policy_decisions(audit)[0]["outcome"] == "block"


def test_shadow_provenance_and_permission_denials_record_in_gate_order():
    gateway, audit = make_gateway(
        policy_mode="shadow",
        provenance_required={"export_data": "user_originated"},
        permissions={
            "rules": [{"role": "analyst", "tool": "export_data", "effect": "deny"}]
        },
    )
    tokens = set_provenance(Provenance.UNTRUSTED_RETRIEVAL)
    try:
        gateway.pre_tool_call("analyst", "export_data", {})
    finally:
        reset_provenance(tokens)

    assert [(event["gate"], event["outcome"]) for event in policy_decisions(audit)] == [
        ("provenance", "would_block"),
        ("permission", "would_block"),
    ]


def test_shadow_permission_allow_records_allow_decision():
    gateway, audit = make_gateway(
        policy_mode="shadow",
        permissions={
            "rules": [{"role": "analyst", "tool": "search", "effect": "allow"}]
        },
    )
    assert gateway.pre_tool_call("analyst", "search", {}) == {}
    event = policy_decisions(audit)[0]
    assert event["gate"] == "permission"
    assert event["outcome"] == "allow"
    assert event["policy_hash"] == "policy-abc"


def test_shadow_decision_without_policy_section_has_hash():
    from argus.llm.config import load_gateway_config

    audit = CaptureAudit()
    gateway = SecurityGateway(
        config=load_gateway_config(
            {
                "policy": {"mode": "shadow"},
                "tools": {"export_data": {"provenance_required": "user_originated"}},
            }
        ),
        audit_logger=audit,
    )
    tokens = set_provenance(Provenance.UNTRUSTED_RETRIEVAL)
    try:
        gateway.pre_tool_call("agent", "export_data", {})
    finally:
        reset_provenance(tokens)
    assert len(policy_decisions(audit)[0]["policy_hash"]) == 64
