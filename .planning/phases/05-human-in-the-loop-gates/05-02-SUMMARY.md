---
phase: 05-human-in-the-loop-gates
plan: 02
subsystem: security
tags: [hitl, terminal-approval, fail-closed, audit, security-gates, pytest]

requires:
  - phase: 05-human-in-the-loop-gates
    provides: RED test suite for HITLGate, gateway sequencing, and adapter propagation (05-01)
  - phase: 04-mcp-server-wrapper
    provides: ArgusMCPMiddleware with ArgusSecurityError catch that ApprovalDeniedError inherits

provides:
  - HITLGate terminal approval gate with approve/deny/retry/timeout semantics
  - HITLConfig dataclass with needs_approval() convenience method
  - ApprovalDeniedError(ArgusSecurityError) with timed_out bool attribute
  - GateType.HITL = "hitl" enum entry
  - load_hitl_config(raw_dict) YAML parser in argus/llm/config.py
  - Gate 1.5 (HITL) in SecurityGateway.pre_tool_call() with audit hitl_decision logging
  - argus.yaml documentation for tools: and hitl: sections

affects:
  - 06-policy-as-code (load_hitl_config integrates into full YAML bootstrap)
  - 07-observability (hitl_decision audit events feed OTel pipeline)

tech-stack:
  added: []
  patterns:
    - "Lazy HITLGate instantiation per-call in pre_tool_call keeps module-level name patchable for unit tests"
    - "Fail-closed after one retry: two invalid inputs auto-deny without blocking indefinitely"
    - "select.select() for real tty timeout; threading.Timer fallback for CI/pipe environments"
    - "Lazy import of HITLConfig in load_hitl_config() avoids circular imports between argus.llm and argus.security"
    - "ApprovalDeniedError as ArgusSecurityError subclass: MCP adapter catches it automatically via existing except clause"

key-files:
  created:
    - argus/security/hitl.py
  modified:
    - argus/security/exceptions.py
    - argus/security/events.py
    - argus/security/gateway.py
    - argus/llm/config.py
    - argus.yaml

key-decisions:
  - "Lazy HITLGate instantiation per pre_tool_call call (not stored in __init__) keeps the module-level HITLGate name patchable during tests — stored instance would escape patch scope"
  - "On HITL deny, ApprovalDeniedError propagates without any audit.send call — denied calls must not appear in audit log as successful pre-calls"
  - "hitl_decision audit event only sent on approve path, before Gate 2 (tool_call_pre)"
  - "No code changes needed in LangChain, CrewAI, AutoGen, or MCP adapters — ApprovalDeniedError inherits ArgusSecurityError and each adapter's existing error handling covers it"
  - "GateType.HITL added to events.py for future structured SecurityEvent emission in Phase 7"

patterns-established:
  - "HITL gate position: Gate 1.5 after permission (Gate 1), before audit pre-call (Gate 2) in pre_tool_call"
  - "Terminal prompt: [ARGUS HITL] banner + json.dumps(tool_input, indent=2) before input()"
  - "Fail-closed semantics: timeout and two invalid inputs both raise ApprovalDeniedError"

requirements-completed: [HITL-01, HITL-02, HITL-03, HITL-04, HITL-05]

duration: 4min
completed: 2026-03-23
---

# Phase 5 Plan 2: HITL Gate Implementation Summary

**Terminal approval gate (HITLGate) with fail-closed semantics, configurable timeout, audit logging on approve path, and ApprovalDeniedError propagation through all four framework adapters**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-23T20:29:58Z
- **Completed:** 2026-03-23T20:33:52Z
- **Tasks:** 2/2
- **Files modified:** 6

## Accomplishments

- Created `argus/security/hitl.py` with HITLGate (approve/deny/retry/timeout) and HITLConfig dataclass using only stdlib (select, threading, json, sys, dataclasses)
- Added ApprovalDeniedError with timed_out attribute to exceptions.py, GateType.HITL to events.py, and load_hitl_config() with lazy HITLConfig import to llm/config.py
- Wired Gate 1.5 (HITL) into SecurityGateway.pre_tool_call() with lazy HITLGate instantiation for test patchability; all 4 adapters handle ApprovalDeniedError via existing ArgusSecurityError catch
- Full test suite GREEN: 244 passed, 1 skipped — all RED tests from plan 05-01 now pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Create HITLGate module, update exceptions + events, add load_hitl_config()** - `02b42c6` (feat)
2. **Task 2: Wire HITL gate into gateway + update adapters + argus.yaml** - `c69d655` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `argus/security/hitl.py` - HITLConfig dataclass + HITLGate with check(), _read_with_timeout() (new file)
- `argus/security/exceptions.py` - ApprovalDeniedError(ArgusSecurityError, timed_out: bool) appended
- `argus/security/events.py` - GateType.HITL = "hitl" added to enum
- `argus/security/gateway.py` - GatewayConfig.hitl field + Gate 1.5 HITL in pre_tool_call()
- `argus/llm/config.py` - load_hitl_config(raw_dict) appended after load_config()
- `argus.yaml` - Documented tools: and hitl: sections (commented out, safe defaults)

## Decisions Made

- Lazy HITLGate instantiation per pre_tool_call call (not cached in `__init__`) keeps the module-level `HITLGate` name patchable via `patch("argus.security.gateway.HITLGate")` in tests — a stored instance would escape the patch scope
- On HITL deny, `ApprovalDeniedError` re-raises immediately without calling `audit.send` — denied calls must not produce `tool_call_pre` audit entries
- `hitl_decision` audit event (approved=True) is sent only on the approve path, placed between Gate 1.5 and Gate 2 so the decision is traceable before the standard pre-call log
- No code changes needed in any adapter — `ApprovalDeniedError` as `ArgusSecurityError` subclass is covered by existing error handling in all four adapters

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

The gateway HITL sequencing test (`test_gateway_hitl_called_after_permission_before_audit`) patches `argus.security.gateway.HITLGate` at the class level, but the gateway is constructed before entering the patch context. Storing `HITLGate(config.hitl)` in `__init__` would capture the real instance, making it unreachable by the patch. Resolved by lazy instantiation in `pre_tool_call` using the module-level `HITLGate` name directly, which is replaced by the patch at call time.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- HITL-01 through HITL-05 all verified by 10 passing unit tests + 4 gateway sequencing tests + 4 adapter propagation tests
- Phase 6 policy-as-code can call `load_hitl_config(raw)` from the YAML bootstrap to activate HITL for real deployments
- argus.yaml `tools:` and `hitl:` sections documented and ready for users to uncomment
- No blockers

## Self-Check: PASSED

All claimed files exist and commits are present in git history.

---
*Phase: 05-human-in-the-loop-gates*
*Completed: 2026-03-23*
