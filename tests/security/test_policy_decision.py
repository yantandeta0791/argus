"""Tests for policy mode configuration and normalized policy decision events."""

from __future__ import annotations

import pytest

from argus.llm.config import load_gateway_config
from argus.security.exceptions import ConfigValidationError
from argus.security.policy_decision import PolicyDecision, PolicyMode


def test_load_gateway_config_defaults_policy_mode_to_enforce():
    assert load_gateway_config({}).policy_mode == "enforce"


def test_load_gateway_config_accepts_shadow_mode():
    cfg = load_gateway_config({"policy": {"mode": "shadow"}})
    assert cfg.policy_mode == "shadow"


def test_load_gateway_config_rejects_unknown_policy_mode():
    with pytest.raises(ConfigValidationError, match="policy.mode"):
        load_gateway_config({"policy": {"mode": "observe"}})


def test_policy_decision_to_audit_event_has_stable_schema():
    decision = PolicyDecision(
        decision_id="decision-123",
        mode=PolicyMode.SHADOW,
        outcome="would_block",
        gate="provenance",
        tool_name="export_data",
        agent_role="analyst",
        rule="provenance_required=user_originated but active=untrusted_retrieval",
        reason="Tool requires user-originated instruction",
        caller_id="caller-7",
        hop_depth=2,
        provenance="untrusted_retrieval",
        policy_metadata={"policy_hash": "abc123", "policy_name": "baseline"},
    )

    assert decision.to_audit_event() == {
        "event_type": "policy_decision",
        "decision_id": "decision-123",
        "mode": "shadow",
        "outcome": "would_block",
        "gate": "provenance",
        "tool_name": "export_data",
        "agent_role": "analyst",
        "rule": "provenance_required=user_originated but active=untrusted_retrieval",
        "reason": "Tool requires user-originated instruction",
        "caller_id": "caller-7",
        "hop_depth": 2,
        "provenance": "untrusted_retrieval",
        "policy_hash": "abc123",
        "policy_name": "baseline",
    }
