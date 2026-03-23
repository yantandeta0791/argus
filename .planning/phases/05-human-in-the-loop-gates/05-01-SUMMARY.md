---
phase: 05-human-in-the-loop-gates
plan: 01
subsystem: testing
tags: [hitl, tdd, pytest, mocking, security-gates]

requires:
  - phase: 04-mcp-server-wrapper
    provides: MCP adapter (ArgusMCPMiddleware) that HITL propagation test extends
  - phase: 03-framework-adapters
    provides: LangChain, CrewAI, AutoGen adapters that HITL propagation tests extend

provides:
  - RED test suite for HITLGate approve/deny/retry/timeout/skip behaviors
  - RED tests for load_hitl_config() YAML parsing
  - RED tests for SecurityGateway HITL gate sequencing (gate 1.5 after permission, before audit)
  - RED tests for ApprovalDeniedError propagation through all four adapters

affects:
  - 05-02 (implements HITLGate, HITLConfig, ApprovalDeniedError, load_hitl_config to turn RED GREEN)

tech-stack:
  added: []
  patterns:
    - "Top-level module imports (not inside test functions) force RED collection failure at pytest collection time"
    - "Mock builtins.input and _read_with_timeout for HITL gate interaction testing without real stdin"
    - "ApprovalDeniedError carries timed_out bool to distinguish timeout from human-deny path"

key-files:
  created:
    - tests/security/test_hitl.py
  modified:
    - tests/security/test_gateway.py
    - tests/adapters/test_langchain.py
    - tests/adapters/test_crewai.py
    - tests/adapters/test_autogen.py
    - tests/adapters/test_mcp.py

key-decisions:
  - "HITLGate._read_with_timeout patched via patch.object (not builtins.input) for timeout test — allows timeout sentinel (None) independent of retry logic"
  - "Gateway HITL sequencing tests mock argus.security.gateway.HITLGate not the instance — gateway instantiates it internally from config.hitl"
  - "MCP adapter test asserts ToolError (plain Exception in stub) not ApprovalDeniedError — matching existing MCP error conversion pattern"
  - "AutoGen propagation test confirms error escapes unchanged — adapter does not catch ArgusSecurityError subclasses"

patterns-established:
  - "TDD RED phase: top-level imports of non-existent modules guarantee collection-time failure"
  - "HITL retry limit: two invalid inputs before auto-deny — documented via side_effect=['oops','also_wrong']"
  - "HITL gate position: Gate 1.5 after permission (Gate 1), before audit send in pre_tool_call"

requirements-completed: [HITL-01, HITL-02, HITL-03, HITL-04, HITL-05]

duration: 3min
completed: 2026-03-23
---

# Phase 5 Plan 1: HITL RED Test Suite Summary

**11-test RED suite for HITLGate behaviors and load_hitl_config parsing, plus 4 gateway sequencing tests and 4 adapter propagation tests across all framework adapters**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-23T20:24:11Z
- **Completed:** 2026-03-23T20:27:XX Z
- **Tasks:** 2/2
- **Files modified:** 6

## Accomplishments

- Created `tests/security/test_hitl.py` with 11 RED tests covering all 5 HITL requirements (approve, deny, retry, timeout, skip)
- Added 4 HITL gate sequencing tests to `tests/security/test_gateway.py` (gate order, deny propagation, skip-when-None, audit event)
- Added `ApprovalDeniedError` propagation tests to all 4 adapter test files (LangChain, CrewAI, AutoGen, MCP)
- All 6 files fail at pytest collection with ImportError/ModuleNotFoundError — confirming RED state

## Task Commits

Each task was committed atomically:

1. **Task 1: Write RED test suite for HITLGate unit behaviors and load_hitl_config parsing** - `57a3429` (test)
2. **Task 2: Write RED tests for gateway HITL sequencing and adapter propagation** - `49b57cf` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `tests/security/test_hitl.py` - 11 RED unit tests for HITLGate and load_hitl_config (new file)
- `tests/security/test_gateway.py` - 4 HITL sequencing tests appended + module-level HITLConfig import
- `tests/adapters/test_langchain.py` - ApprovalDeniedError propagation test appended + module import
- `tests/adapters/test_crewai.py` - ApprovalDeniedError propagation test appended + module import
- `tests/adapters/test_autogen.py` - ApprovalDeniedError propagation test appended + module import
- `tests/adapters/test_mcp.py` - ApprovalDeniedError-to-ToolError conversion test appended + module import

## Decisions Made

- `HITLGate._read_with_timeout` patched via `patch.object` (not `builtins.input`) for the timeout test, allowing None as the timeout sentinel without interfering with retry logic
- Gateway sequencing tests mock `argus.security.gateway.HITLGate` (the class) not an instance — plan 02 will instantiate it internally from `config.hitl`
- MCP adapter propagation test asserts `Exception` (ToolError stub), not raw `ApprovalDeniedError` — matching the existing MCP error conversion pattern
- AutoGen adapter propagation test confirms error escapes unchanged through async wrapper — adapter does not catch `ArgusSecurityError` subclasses

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- RED test suite complete — plan 05-02 implements HITLGate, HITLConfig, ApprovalDeniedError, and load_hitl_config to turn all RED tests GREEN
- Gateway modification plan 05-02 must insert HITLGate at gate position 1.5 in pre_tool_call
- No blockers

---
*Phase: 05-human-in-the-loop-gates*
*Completed: 2026-03-23*
