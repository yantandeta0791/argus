"""Tests for argus.security.identity — ContextVars, AgentRegistry, AgentRegistryConfig."""

import pytest


# --- ContextVar helpers ---


def test_get_caller_context_defaults_to_none_and_zero():
    from argus.security.identity import get_caller_context

    caller_id, hop_depth = get_caller_context()
    # Defaults: None and 0 when no context has been set
    assert caller_id is None
    assert hop_depth == 0


def test_set_and_get_caller_context():
    from argus.security.identity import set_caller_context, get_caller_context, reset_caller_context

    tokens = set_caller_context("agent_a", 2)
    try:
        caller_id, hop_depth = get_caller_context()
        assert caller_id == "agent_a"
        assert hop_depth == 2
    finally:
        reset_caller_context(tokens)


def test_reset_caller_context_restores_previous_values():
    from argus.security.identity import set_caller_context, get_caller_context, reset_caller_context

    # Set initial context
    tokens1 = set_caller_context("parent_agent", 1)
    try:
        tokens2 = set_caller_context("child_agent", 2)
        try:
            caller_id, hop_depth = get_caller_context()
            assert caller_id == "child_agent"
            assert hop_depth == 2
        finally:
            reset_caller_context(tokens2)
        # After reset, should be back to parent_agent
        caller_id, hop_depth = get_caller_context()
        assert caller_id == "parent_agent"
        assert hop_depth == 1
    finally:
        reset_caller_context(tokens1)


def test_set_caller_context_returns_tokens_tuple():
    from argus.security.identity import set_caller_context, reset_caller_context

    tokens = set_caller_context("agent_b", 3)
    assert isinstance(tokens, tuple)
    assert len(tokens) == 2
    reset_caller_context(tokens)


# --- AgentRegistryConfig ---


def test_agent_registry_config_defaults():
    from argus.security.identity import AgentRegistryConfig

    config = AgentRegistryConfig(agents={"supervisor": "supervisor_role"})
    assert config.max_delegation_depth == 3


def test_agent_registry_config_custom_depth():
    from argus.security.identity import AgentRegistryConfig

    config = AgentRegistryConfig(agents={}, max_delegation_depth=5)
    assert config.max_delegation_depth == 5


# --- AgentRegistry ---


def test_agent_registry_resolves_known_caller_id():
    from argus.security.identity import AgentRegistry, AgentRegistryConfig

    config = AgentRegistryConfig(agents={"supervisor": "supervisor_role"})
    registry = AgentRegistry(config)
    role = registry.resolve_role("supervisor", "default")
    assert role == "supervisor_role"


def test_agent_registry_falls_back_for_unknown_caller_id():
    from argus.security.identity import AgentRegistry, AgentRegistryConfig

    config = AgentRegistryConfig(agents={"supervisor": "supervisor_role"})
    registry = AgentRegistry(config)
    role = registry.resolve_role("unknown_agent", "fallback")
    assert role == "fallback"


def test_agent_registry_returns_fallback_when_config_is_none():
    from argus.security.identity import AgentRegistry

    registry = AgentRegistry(None)
    role = registry.resolve_role("any_agent", "fallback_role")
    assert role == "fallback_role"


def test_agent_registry_max_depth_from_config():
    from argus.security.identity import AgentRegistry, AgentRegistryConfig

    config = AgentRegistryConfig(agents={}, max_delegation_depth=5)
    registry = AgentRegistry(config)
    assert registry.max_depth == 5


def test_agent_registry_max_depth_default_when_config_none():
    from argus.security.identity import AgentRegistry

    registry = AgentRegistry(None)
    assert registry.max_depth == 3


# --- DelegationDepthError ---


def test_delegation_depth_error_is_argus_security_error():
    from argus.security.exceptions import DelegationDepthError, ArgusSecurityError

    assert issubclass(DelegationDepthError, ArgusSecurityError)


def test_delegation_depth_error_stores_all_fields():
    from argus.security.exceptions import DelegationDepthError

    exc = DelegationDepthError(
        gate="identity",
        blocked="tool_x",
        rule="hop=4>max=3",
        caller_id="agent",
        hop_depth=4,
    )
    assert exc.gate == "identity"
    assert exc.blocked == "tool_x"
    assert exc.rule == "hop=4>max=3"
    assert exc.caller_id == "agent"
    assert exc.hop_depth == 4


def test_delegation_depth_error_default_fields():
    from argus.security.exceptions import DelegationDepthError

    exc = DelegationDepthError(gate="identity", blocked="tool_y", rule="hop=5>max=3")
    assert exc.caller_id is None
    assert exc.hop_depth == 0


# --- GateType.IDENTITY ---


def test_gate_type_identity_exists():
    from argus.security.events import GateType

    assert GateType.IDENTITY.value == "identity"


# --- SecurityEvent caller_id / hop_depth fields ---


def test_security_event_accepts_caller_id_and_hop_depth():
    from argus.security.events import SecurityEvent, GateType

    event = SecurityEvent(
        gate=GateType.IDENTITY,
        outcome="blocked",
        caller_id="agent_a",
        hop_depth=2,
    )
    assert event.caller_id == "agent_a"
    assert event.hop_depth == 2


def test_security_event_defaults_caller_id_and_hop_depth():
    from argus.security.events import SecurityEvent, GateType

    event = SecurityEvent(gate=GateType.PERMISSION, outcome="allowed")
    assert event.caller_id is None
    assert event.hop_depth == 0
