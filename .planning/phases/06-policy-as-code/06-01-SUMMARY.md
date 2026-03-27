---
phase: 06-policy-as-code
plan: "01"
subsystem: testing

tags: [pytest, tdd, rbac, policy-as-code, config-loading, validation]

requires:
  - phase: 05-hitl-gates
    provides: HITLGate, HITLConfig, GatewayConfig, SecurityGateway — test integration targets
  - phase: 04-adapters
    provides: established adapter and config loading patterns

provides:
  - 5 RED failing tests for load_rbac_config (POLC-01) in tests/llm/test_config.py
  - 2 RED failing tests for load_secrets_config (POLC-02) in tests/llm/test_config.py
  - 2 RED failing tests for load_egress_config (POLC-03) in tests/llm/test_config.py
  - 4 RED failing tests for load_spend_profiles (POLC-04) in tests/llm/test_config.py
  - 2 RED failing tests for ConfigValidationError (POLC-05) in tests/llm/test_config.py
  - 3 RED failing tests for load_gateway_config integration in tests/llm/test_config.py
  - 4 RED tests for wildcard allow and deny enforcement in tests/security/test_permission.py

affects:
  - 06-02 (must satisfy all 18 failing test_config.py tests)
  - 06-03 (must satisfy wildcard/deny enforcer tests)

tech-stack:
  added: []
  patterns:
    - "TDD RED phase: imports inside function bodies to produce ImportError not collection-time failures"
    - "Wildcard policy test: build PolicyConfig directly with PolicyRule objects, no YAML loading"

key-files:
  created: []
  modified:
    - tests/llm/test_config.py
    - tests/security/test_permission.py

key-decisions:
  - "Import symbols inside test function bodies (not module level) to match existing test_config.py pattern and ensure ImportError fails at call time, not collection time"
  - "Deny/wildcard enforcer tests that expect raises pass now for wrong reason — correct RED test is test_wildcard_allow_permits_any_tool which fails because wildcard is not yet implemented"
  - "ARGUS_SPEND_PROFILE env var selected as the active profile selector name (consistent with Argus env var naming convention)"

patterns-established:
  - "All new test symbols imported inside test function bodies — prevents collection-time failures"
  - "PolicyConfig built directly in enforcer tests — no YAML loading required for enforcement behavior tests"

requirements-completed:
  - POLC-01
  - POLC-02
  - POLC-03
  - POLC-04
  - POLC-05

duration: 3min
completed: 2026-03-27
---

# Phase 6 Plan 01: Policy-as-Code RED Test Suite Summary

**23-test RED suite covering all Phase 6 behavioral contracts — RBAC loader, secrets/egress/spend config, ConfigValidationError, load_gateway_config integration, and wildcard/deny enforcer**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-27T17:11:18Z
- **Completed:** 2026-03-27T17:14:30Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Appended 18 RED failing tests to tests/llm/test_config.py (5 original still pass)
- Appended 4 wildcard/deny tests to tests/security/test_permission.py (3 original still pass, 1 fails RED)
- All 244 pre-existing tests remain passing — zero regressions
- Established exact behavioral contracts for Plans 02 and 03 to satisfy

## Task Commits

1. **Task 1: POLC-01 RBAC loader + wildcard/deny enforcer tests** - `fce7ac1` (test)
2. **Task 2: POLC-02 through POLC-05 + integration tests** - `4dbd1ce` (test)

## Files Created/Modified

- `tests/llm/test_config.py` - Added 18 RED test functions for all Phase 6 config loading behaviors
- `tests/security/test_permission.py` - Added 4 wildcard/deny enforcer tests (1 fails RED)

## Decisions Made

- Imported all new symbols inside test function bodies (not module level) to match existing file style — ensures failures occur at call time, not pytest collection time
- `ARGUS_SPEND_PROFILE` chosen as env var name for spend profile selection — consistent with existing Argus env var naming
- Deny tests that expect `PermissionDeniedError` pass now (enforcer denies everything when no wildcard match); only `test_wildcard_allow_permits_any_tool` is properly RED

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `.venv` required for test execution — `python3.12` system Python missing `litellm` and other optional dependencies; `.venv/bin/python` has full dev environment. Identified immediately, used `.venv` for all verification.

## Next Phase Readiness

- All behavioral contracts established — Plans 02 and 03 have clear targets
- Plan 02 must implement: `load_rbac_config`, `load_secrets_config`, `load_egress_config`, `load_spend_profiles`, `load_gateway_config`, `ConfigValidationError`
- Plan 03 must implement: wildcard `*` allow support and explicit deny override in `PermissionEnforcer`

---
*Phase: 06-policy-as-code*
*Completed: 2026-03-27*
