---
phase: 09-multi-agent-enforcement
plan: 02
subsystem: security
tags: [identity, multi-agent, contextvars, otel, hitl, delegation, gateway]

requires:
  - phase: 09-01
    provides: "identity.py (AgentRegistry, get_caller_context, set_caller_context), DelegationDepthError, SecurityEvent.caller_id/hop_depth fields"

provides:
  - "Gate 0.5 (identity) enforced in SecurityGateway.pre_tool_call — before permission check"
  - "DelegationDepthError raised fail-closed when hop_depth exceeds max_delegation_depth"
  - "Audit log entries include caller_id and hop_depth for every tool call"
  - "OTel violation spans include argus.security.caller_id and argus.security.hop_depth attributes"
  - "HITL approval banner shows delegation context (Delegated by: {name} (hop {N}/{max})) for sub-agent calls"

affects: [10-anomaly-detection]

tech-stack:
  added: []
  patterns:
    - "Gate 0.5 resolves caller_id from explicit param first, then ContextVars — explicit always wins"
    - "AgentRegistry constructed in __init__, injected as self._agent_registry — reused per call"
    - "_emit_violation extended with caller_id/hop_depth kwargs — all call sites pass identity context"
    - "HITLGate.check extended with optional caller_id/hop_depth/max_depth — backward compat via defaults"

key-files:
  created: []
  modified:
    - argus/security/gateway.py
    - argus/security/hitl.py
    - argus/observability/otel.py
    - tests/security/test_gateway.py
    - tests/security/test_hitl.py
    - tests/observability/test_otel.py

key-decisions:
  - "pre_tool_call uses keyword-only params (*, caller_id=None, hop_depth=None) — prevents positional call breakage"
  - "hop_depth=None sentinel distinguishes 'not passed' from 'passed as 0' — resolves ContextVar fallback correctly"
  - "severity_map extended with identity:HIGH — DelegationDepthError is equally HIGH as permission denial"
  - "Existing test test_gateway_emits_violation_on_permission_block updated to use call_args kwargs dict — assert_called_once_with incompatible with new caller_id/hop_depth defaults in _emit_violation"

patterns-established:
  - "Gate 0.5 pattern: explicit param > ContextVar > default(None/0)"
  - "Identity flows through all enforcement: audit, OTel, HITL banner"

requirements-completed: [MAGNT-01, MAGNT-03, MAGNT-04, MAGNT-05, MAGNT-07]

duration: 7min
completed: 2026-04-09
---

# Phase 09 Plan 02: Gate 0.5 Identity Enforcement Summary

**Gate 0.5 caller identity resolution and delegation depth enforcement in SecurityGateway — audit, OTel spans, and HITL banner all carry caller_id/hop_depth**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-09T23:19:25Z
- **Completed:** 2026-04-09T23:22:48Z
- **Tasks:** 1 (TDD: RED + GREEN + full suite)
- **Files modified:** 6

## Accomplishments
- Gate 0.5 identity check inserted before Gate 1 in `pre_tool_call` — reads caller_id from explicit kwarg or ContextVar, resolves agent_role from AgentRegistry, enforces delegation depth fail-closed
- `DelegationDepthError` raised (and OTel violation emitted) when hop_depth > max_delegation_depth; hop_depth == max is explicitly allowed (boundary condition)
- All audit `tool_call_pre` entries now carry `caller_id` and `hop_depth` fields — full attribution for every tool call
- `OtelEmitter.emit_security_violation` extended with `caller_id`/`hop_depth` params and two new span attributes (`argus.security.caller_id`, `argus.security.hop_depth`)
- HITL approval banner shows `Delegated by: {caller_id} (hop {depth}/{max})` when hop_depth > 0 — operator sees full delegation context before approving

## Task Commits

1. **Task 1: Implement Gate 0.5 in SecurityGateway and extend OTel/HITL** - `fd7ea0d` (feat)

**Plan metadata:** (docs commit — see final_commit below)

## Files Created/Modified
- `argus/security/gateway.py` — Gate 0.5 in pre_tool_call; _emit_violation extended with identity; AgentRegistry constructed in __init__
- `argus/security/hitl.py` — HITLGate.check() extended with caller_id/hop_depth/max_depth optional params and delegation banner
- `argus/observability/otel.py` — emit_security_violation extended with caller_id/hop_depth params; two new span attribute constants
- `tests/security/test_gateway.py` — 7 new Gate 0.5 tests; 1 existing test updated (assert_called_once_with -> kwargs dict)
- `tests/security/test_hitl.py` — 3 new TestHITLSubAgentBanner tests
- `tests/observability/test_otel.py` — 2 new OTel identity attribute tests

## Decisions Made
- Used `keyword-only` params via `*` separator in `pre_tool_call` — prevents any positional call from breaking
- Used `None` sentinel for `hop_depth` param (not `0`) — allows distinguishing "not provided" from "explicitly 0", enabling correct ContextVar fallback
- `_emit_violation` updated at all call sites to pass identity context — permisison/hitl/redaction/prompt_shield violations also carry the caller attribution
- Updated `test_gateway_emits_violation_on_permission_block` to use `call_args[1]` dict assertion instead of `assert_called_once_with` — the latter doesn't support partial matching when new defaults are added

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing OTel test assertion to be compatible with new _emit_violation signature**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** `test_gateway_emits_violation_on_permission_block` used `assert_called_once_with(...)` which requires exact argument match — now fails because `_emit_violation` passes additional `caller_id=None, hop_depth=0` kwargs to `emit_security_violation`
- **Fix:** Changed assertion to `call_args[1]` dict check verifying only the four original fields
- **Files modified:** tests/security/test_gateway.py
- **Verification:** Full suite 336 passed, 1 skipped
- **Committed in:** fd7ea0d (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug fix)
**Impact on plan:** Necessary correctness fix — existing assertion was brittle against new kwargs. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Gate 0.5 identity enforcement is fully operational — every tool call carries caller_id, hop_depth, and resolved agent_role
- AgentRegistry is wired into SecurityGateway — Phase 10 AnomalyDetector can use agent_id from the same registry
- ContextVar propagation tested — LangGraph/framework adapters from Phase 09-03 can set_caller_context() and it flows through automatically

---
*Phase: 09-multi-agent-enforcement*
*Completed: 2026-04-09*
