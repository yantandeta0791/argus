---
phase: 06-policy-as-code
plan: "03"
subsystem: config
tags: [policy-as-code, gateway, rbac, secrets, egress, hitl, pydantic]

requires:
  - phase: 06-02
    provides: load_rbac_config, load_secrets_config, load_egress_config, load_spend_profiles, ConfigValidationError
  - phase: 05-02
    provides: HITLConfig, GatewayConfig

provides:
  - load_gateway_config(raw: dict) -> GatewayConfig in argus/llm/config.py
  - Single orchestrating loader for all argus.yaml policy sections
  - All POLC-01 through POLC-05 requirements satisfied with GREEN tests

affects:
  - Phase 7 (OTel config — reads argus.yaml through same config layer)
  - Phase 8 (REST sidecar — calls load_gateway_config for config loading)

tech-stack:
  added: []
  patterns:
    - "Lazy import pattern for circular-import-safe cross-module references (lazy GatewayConfig import inside function body)"
    - "Orchestrator loader delegates to section loaders — no validation logic in gateway loader itself"

key-files:
  created: []
  modified:
    - argus/llm/config.py

key-decisions:
  - "load_gateway_config does not call load_spend_profiles — SpendConfig is a ModelConfig field, not a GatewayConfig field"
  - "GatewayConfig lazily imported inside load_gateway_config to avoid argus.llm <-> argus.security circular imports"
  - "ConfigValidationError from section loaders propagates unchanged (not re-wrapped)"

patterns-established:
  - "Phase 6 TDD pattern: RED tests in 06-01, implementations in 06-02, integration loader in 06-03 turns all GREEN"

requirements-completed: [POLC-01, POLC-02, POLC-03, POLC-04, POLC-05]

duration: 8min
completed: 2026-03-27
---

# Phase 6 Plan 03: Policy-as-Code Gateway Config Loader Summary

**Single `load_gateway_config(raw: dict) -> GatewayConfig` orchestrator in `argus/llm/config.py` wires all four section loaders (RBAC, secrets, egress, HITL) into a fully populated GatewayConfig, turning 3 integration tests GREEN and completing Phase 6 (266 tests, 0 failures)**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-27T17:20:00Z
- **Completed:** 2026-03-27T17:28:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Added `load_gateway_config(raw: dict) -> GatewayConfig` to `argus/llm/config.py`
- Lazy GatewayConfig import inside function body avoids circular imports between `argus.llm` and `argus.security`
- All five POLC requirements (POLC-01 through POLC-05) verified GREEN by 30 tests in test_config.py and test_permission.py
- Full suite 266 passed, 1 skipped — zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add load_gateway_config and turn integration tests GREEN** - `c26e787` (feat)
2. **Task 2: Smoke-test all five POLC requirements** - verification only, no code changes

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `argus/llm/config.py` - Added `load_gateway_config` function (22 lines, after `load_spend_profiles`)

## Decisions Made

- `load_gateway_config` does not call `load_spend_profiles` — spend config lives in `ModelConfig`, not `GatewayConfig`
- Lazy import of `GatewayConfig` inside function body (same pattern as `load_rbac_config` and `load_secrets_config`) avoids circular imports
- `ConfigValidationError` propagates unchanged from section loaders — no re-wrapping at the gateway layer

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 6 (Policy-as-Code) is complete — all POLC-01 through POLC-05 requirements satisfied
- `load_gateway_config` is the single entry point for argus.yaml policy loading — Phase 7 (OTel) and Phase 8 (REST sidecar) can call it directly
- Ready for `/gsd:verify-work` on Phase 6

## Self-Check: PASSED

- FOUND: argus/llm/config.py (contains load_gateway_config)
- FOUND: .planning/phases/06-policy-as-code/06-03-SUMMARY.md
- FOUND: commit c26e787 (feat(06-03): add load_gateway_config to argus/llm/config.py)
- Full test suite: 266 passed, 1 skipped, 0 failed

---
*Phase: 06-policy-as-code*
*Completed: 2026-03-27*
