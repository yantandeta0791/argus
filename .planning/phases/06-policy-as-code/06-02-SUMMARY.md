---
phase: 06-policy-as-code
plan: "02"
subsystem: security
tags: [casbin, pydantic, rbac, policy, regex, spend-profiles, egress, secrets]

# Dependency graph
requires:
  - phase: 06-01
    provides: RED test suite for POLC-01 through POLC-05 + integration tests

provides:
  - ConfigValidationError(ValueError) in argus/security/exceptions.py
  - Wildcard allow (_wildcard_roles) and deny (_deny_rules) short-circuits in PermissionEnforcer
  - load_rbac_config converting role-centric YAML to PolicyConfig (POLC-01)
  - load_secrets_config with SecretsConfig Pydantic model and regex validation (POLC-02/POLC-05)
  - load_egress_config returning list[str] allowlist (POLC-03)
  - load_spend_profiles with named profiles and env var support (POLC-04)

affects: [06-03, security-gateway, policy-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Deny-before-wildcard-before-Casbin evaluation order in PermissionEnforcer.enforce()"
    - "Lazy imports inside function bodies for all cross-subsystem references (avoids circular imports)"
    - "Pydantic field_validator for early regex validation with re.compile()"
    - "ConfigValidationError wraps Pydantic ValidationError to surface at config load time"

key-files:
  created: []
  modified:
    - argus/security/exceptions.py
    - argus/security/permission/enforcer.py
    - argus/llm/config.py
    - tests/llm/test_config.py

key-decisions:
  - "Deny rules checked FIRST (before wildcard) — explicit deny must override all allow paths"
  - "Casbin enforcer skipped when CSV is empty (only deny/wildcard rules present) — avoid building Casbin for degenerate case"
  - "Empty sets initialized in permissive mode — prevents AttributeError if enforce() called unexpectedly"
  - "load_rbac_config returns None (not empty PolicyConfig) when no roles defined — matches load_hitl_config pattern"
  - "ARGUS_SPEND_PROFILE env var honored but active_profile argument takes explicit priority"

patterns-established:
  - "All cross-subsystem config loaders use lazy imports inside function body (not module level)"
  - "ConfigValidationError raised at load time, not enforcement time — fail fast on bad YAML"

requirements-completed: [POLC-01, POLC-02, POLC-03, POLC-04, POLC-05]

# Metrics
duration: 15min
completed: 2026-03-27
---

# Phase 6 Plan 02: Policy-as-Code Implementations Summary

**ConfigValidationError, wildcard/deny PermissionEnforcer short-circuits, and four YAML section loaders (rbac, secrets, egress, spend profiles) turning all Plan 01 RED tests GREEN**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-27T17:20:00Z
- **Completed:** 2026-03-27T17:35:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- ConfigValidationError(ValueError) added to exceptions hierarchy — surfaces bad YAML at startup
- PermissionEnforcer now handles wildcard allow ("*") and deny rules in pre-Casbin short-circuits with correct priority: deny > wildcard > Casbin
- Four section loaders added to argus/llm/config.py with all lazy imports, turning 20 new tests GREEN
- SecretsConfig Pydantic model validates regex patterns at construction time using re.compile()
- Full suite: 263 passed, 1 skipped, only 3 Plan 03 integration stubs still failing as expected

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ConfigValidationError and fix PermissionEnforcer for wildcard + deny** - `25c6613` (feat)
2. **Task 2: Add SecretsConfig and four section loaders to argus/llm/config.py** - `33a5496` (feat)

## Files Created/Modified

- `argus/security/exceptions.py` - Added ConfigValidationError(ValueError) class
- `argus/security/permission/enforcer.py` - Added _wildcard_roles, _deny_rules; updated enforce() priority logic
- `argus/llm/config.py` - Added SecretsConfig, load_rbac_config, load_secrets_config, load_egress_config, load_spend_profiles
- `tests/llm/test_config.py` - Fixed missing `import pytest` (Rule 1 bug fix)

## Decisions Made

- Deny rules checked before wildcard — explicit deny must override all allow paths including wildcard
- Casbin enforcer conditionally built only when specific allow rules exist (non-wildcard, non-deny)
- Empty _wildcard_roles/_deny_rules sets always initialized in permissive mode to prevent AttributeError
- load_rbac_config returns None (not empty PolicyConfig) for absent/empty YAML section — consistent with load_hitl_config pattern

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed missing `import pytest` in tests/llm/test_config.py**
- **Found during:** Task 2 (running tests after implementing loaders)
- **Issue:** test_load_spend_profiles_unknown_profile_raises used `pytest.raises` but the file had no `import pytest` — NameError at runtime
- **Fix:** Added `import pytest` at the top of tests/llm/test_config.py
- **Files modified:** tests/llm/test_config.py
- **Verification:** All 20 non-gateway config tests pass GREEN
- **Committed in:** 33a5496 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Necessary fix — test file was broken; the missing import was a bug in the Plan 01 RED suite, not in the implementation.

## Issues Encountered

None - implementation matched the plan specification exactly.

## Next Phase Readiness

- All POLC-01 through POLC-05 implementations are complete
- Plan 03 integration tests (load_gateway_config) are still RED — those are the next plan's target
- PermissionEnforcer is ready for integration with the full GatewayConfig flow

---
*Phase: 06-policy-as-code*
*Completed: 2026-03-27*
