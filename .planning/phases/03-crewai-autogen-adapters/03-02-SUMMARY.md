---
phase: 03-crewai-autogen-adapters
plan: "02"
subsystem: adapters
tags: [crewai, security, proxy-pattern, duck-typing, synchronous-enforcement]

# Dependency graph
requires:
  - phase: 03-01
    provides: RED test scaffold for CrewAI adapter (test_crewai.py)
  - phase: 02-langchain-adapter
    provides: langchain.py proxy pattern as reference implementation
provides:
  - ArgusCrewAIToolWrapper class intercepting run() synchronously
  - wrap_tools() function returning list[ArgusCrewAIToolWrapper]
  - crewai optional extra in pyproject.toml
affects:
  - 03-03 (AutoGen adapter — same TDD pattern)
  - 04-mcp-wrapper (can reuse adapter pattern)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Proxy wrapper intercepts tool.run() — same proxy pattern as langchain.py but targeting run() not invoke()"
    - "Duck typing with Any — no top-level import of crewai required"
    - "Fail-closed: no try/except around ArgusSecurityError, errors propagate as designed"

key-files:
  created:
    - argus/adapters/crewai.py
  modified:
    - pyproject.toml

key-decisions:
  - "Intercept run() not _run() — run() is the public boundary CrewAI framework calls; intercepting _run() would be bypassed by framework directly"
  - "No top-level crewai import — duck typing with Any keeps crewai as optional extra, not required dep"
  - "String inputs normalized to {input: str} for gateway but passed unchanged to tool.run() — gateway needs dict form; CrewAI tool needs original form"

patterns-established:
  - "CrewAI adapter pattern: proxy run() with pre/post gateway calls, duck typing, no security error catching"

requirements-completed: [ADPT-01, ADPT-02, ADPT-07]

# Metrics
duration: 1min
completed: 2026-03-23
---

# Phase 03 Plan 02: CrewAI Adapter Summary

**ArgusCrewAIToolWrapper proxy intercepts tool.run() synchronously with fail-closed security gates — no crewai install required, duck typed with Any**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-23T00:06:38Z
- **Completed:** 2026-03-23T00:07:42Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Implemented `ArgusCrewAIToolWrapper` mirroring langchain.py proxy pattern but intercepting `run()` instead of `invoke()`
- All 7 tests in `tests/adapters/test_crewai.py` pass GREEN — adapter imports cleanly without crewai installed
- Added `crewai = ["crewai>=1.0"]` optional extra to pyproject.toml following established langchain pattern
- Existing `test_langchain.py` suite (6 tests) continues to pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement argus/adapters/crewai.py** - `60bcf09` (feat)
2. **Task 2: Add crewai optional extra to pyproject.toml** - `ac758c1` (chore)

**Plan metadata:** (docs: complete plan — see final commit)

## Files Created/Modified
- `argus/adapters/crewai.py` - ArgusCrewAIToolWrapper and wrap_tools(); proxy pattern on run() with pre/post gateway enforcement
- `pyproject.toml` - Added crewai optional extra under [project.optional-dependencies]

## Decisions Made
- Intercept `run()` not `_run()` — the plan research noted CrewAI framework calls `run()` as the public boundary; intercepting the private `_run()` would be bypassed by the framework entirely.
- No `try/except` around `ArgusSecurityError` — all security exceptions (`PermissionDeniedError`, `InjectionDetectedError`, `EgressViolationError`) propagate to the caller unchanged, matching ADPT-07 fail-closed requirement.
- String input normalization: `{"input": str}` for gateway pre_tool_call, but original string passed to `tool.run()` — gateway needs dict form for audit/policy checks; CrewAI tool needs the original form for Pydantic validation.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — crewai not installed in .venv as anticipated; proceeded with documented proxy pattern as specified.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- CrewAI adapter complete and tested; 03-03 (AutoGen adapter implementation) is ready to execute
- Pattern is identical: proxy wrapper, run()/invoke() interception, no framework install required
- ADPT-01, ADPT-02, ADPT-07 requirements marked complete for the CrewAI path

---
*Phase: 03-crewai-autogen-adapters*
*Completed: 2026-03-23*
