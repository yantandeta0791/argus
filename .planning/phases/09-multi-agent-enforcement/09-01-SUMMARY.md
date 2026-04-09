---
phase: 09-multi-agent-enforcement
plan: "01"
subsystem: security/identity
tags: [multi-agent, identity, context-vars, rbac, exceptions, events, config]
dependency_graph:
  requires: []
  provides:
    - argus.security.identity (ContextVars, AgentRegistry, AgentRegistryConfig)
    - argus.security.exceptions.DelegationDepthError
    - argus.security.events.GateType.IDENTITY
    - argus.security.events.SecurityEvent.caller_id / hop_depth
    - argus.llm.config.load_agents_config
    - argus.security.gateway.GatewayConfig.agents / max_delegation_depth
  affects:
    - 09-02 (Gate 0.5 identity check uses AgentRegistry and DelegationDepthError)
    - 09-03 (framework adapters call set_caller_context / get_caller_context)
tech_stack:
  added: []
  patterns:
    - ContextVar propagation for async call stacks (stdlib contextvars)
    - Lazy import in config loaders to avoid circular imports
    - Permissive fallback resolution (unknown caller_id uses adapter-supplied role)
key_files:
  created:
    - argus/security/identity.py
    - tests/security/test_identity.py
  modified:
    - argus/security/exceptions.py
    - argus/security/events.py
    - argus/llm/config.py
    - argus/security/gateway.py
    - tests/llm/test_config.py
decisions:
  - "AgentRegistry uses permissive fallback (unknown caller_id returns adapter-supplied role) — prevents single-agent breakage when no agents: section configured"
  - "DelegationDepthError follows ApprovalDeniedError pattern exactly — consistent exception hierarchy"
  - "GatewayConfig.agents lazily typed as Optional[Any] — same pattern as otel field, avoids circular import"
  - "load_agents_config returns None for absent/empty agents section — backward compatible"
  - "SecurityEvent.caller_id and hop_depth default to None/0 — all existing SecurityEvent construction unaffected"
metrics:
  duration: "175 seconds"
  completed_date: "2026-04-09"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 5
  tests_added: 30
  tests_total: 324
---

# Phase 9 Plan 01: Identity Infrastructure Summary

**One-liner:** ContextVar-based caller identity propagation with AgentRegistry for permissive caller_id-to-RBAC-role resolution and DelegationDepthError exception hierarchy.

## What Was Built

Plan 09-01 establishes all type contracts and data structures required by Phase 9's Gate 0.5 (Plan 02) and framework adapter contextvars (Plan 03).

### argus/security/identity.py (new)

- `_current_caller_id: ContextVar[str | None]` (default=None) — propagates caller identity through async call stacks
- `_current_hop_depth: ContextVar[int]` (default=0) — propagates delegation chain depth
- `set_caller_context(caller_id, hop_depth) -> tuple` — sets both ContextVars, returns reset tokens
- `get_caller_context() -> (str | None, int)` — reads current identity context
- `reset_caller_context(tokens)` — restores previous values using saved tokens
- `AgentRegistryConfig` dataclass — `agents: dict[str, str]` + `max_delegation_depth: int = 3`
- `AgentRegistry` — `resolve_role(caller_id, fallback_role)` with permissive fallback; `max_depth` property

### argus/security/exceptions.py (extended)

- `DelegationDepthError(ArgusSecurityError)` — adds `caller_id` and `hop_depth` attributes; follows exact `ApprovalDeniedError` pattern

### argus/security/events.py (extended)

- `GateType.IDENTITY = "identity"` — new enum member for Gate 0.5
- `SecurityEvent.caller_id: str | None = None` — backward-compatible field
- `SecurityEvent.hop_depth: int = 0` — backward-compatible field

### argus/llm/config.py (extended)

- `load_agents_config(raw: dict)` — parses `agents:` YAML section with `registry:` and `max_delegation_depth:` subkeys; returns `AgentRegistryConfig | None`; uses lazy import pattern
- `load_gateway_config()` — updated to call `load_agents_config()` and populate new `GatewayConfig` fields

### argus/security/gateway.py (extended)

- `GatewayConfig.agents: Optional[Any] = None` — holds `AgentRegistryConfig` (lazily typed)
- `GatewayConfig.max_delegation_depth: int = 3` — mirrors registry config

## Deviations from Plan

None — plan executed exactly as written.

## Tests

- 22 new tests in `tests/security/test_identity.py`
- 8 new tests in `tests/llm/test_config.py`
- Full suite: 324 passed, 1 skipped (0 failures)

## Self-Check: PASSED

- FOUND: argus/security/identity.py
- FOUND: tests/security/test_identity.py
- FOUND commit 4782299: feat(09-01): create identity module and extend exceptions/events
- FOUND commit d5afd66: feat(09-01): add load_agents_config and extend GatewayConfig with agents fields
