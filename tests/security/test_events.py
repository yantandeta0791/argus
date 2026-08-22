"""Tests for SecurityEvent.from_context() — CLEAN-04."""

import pytest

from argus.security.events import GateType, SecurityEvent
from argus.security.identity import reset_caller_context, set_caller_context


@pytest.fixture(autouse=True)
def _clean_caller_context():
    """Ensure ContextVars are reset between tests — even on failure."""
    yield


def test_from_context_reads_caller_id_from_contextvar():
    """CLEAN-04: from_context() reads caller_id/hop_depth from ContextVars."""
    tokens = set_caller_context("agent-x", 2)
    try:
        event = SecurityEvent.from_context(
            gate=GateType.PERMISSION, outcome="blocked", tool_name="search"
        )
        assert event.caller_id == "agent-x"
        assert event.hop_depth == 2
    finally:
        reset_caller_context(tokens)


def test_from_context_defaults_to_none_when_no_context():
    """CLEAN-04: from_context() defaults to caller_id=None, hop_depth=0 outside a context."""
    event = SecurityEvent.from_context(gate=GateType.PROMPT_SHIELD, outcome="blocked")
    assert event.caller_id is None
    assert event.hop_depth == 0


def test_from_context_preserves_explicit_fields():
    """CLEAN-04: explicit keyword fields are preserved alongside resolved identity."""
    tokens = set_caller_context("agent-x", 1)
    try:
        event = SecurityEvent.from_context(
            gate=GateType.PERMISSION,
            outcome="blocked",
            agent_role="worker",
            tool_name="search",
            rule_triggered="permission_denied",
        )
        assert event.gate == GateType.PERMISSION
        assert event.outcome == "blocked"
        assert event.agent_role == "worker"
        assert event.tool_name == "search"
        assert event.rule_triggered == "permission_denied"
        assert event.caller_id == "agent-x"
        assert event.hop_depth == 1
    finally:
        reset_caller_context(tokens)
