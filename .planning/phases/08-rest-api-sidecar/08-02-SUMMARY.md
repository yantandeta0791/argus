---
phase: 08-rest-api-sidecar
plan: 02
subsystem: api
tags: [fastapi, uvicorn, pydantic, httpx, rest, sidecar, security-gateway]

# Dependency graph
requires:
  - phase: 08-01
    provides: stub serve.py and RED tests for OPS-05, OPS-06
  - phase: 07-03
    provides: SecurityGateway OTel wiring, load_gateway_config
provides:
  - Full REST sidecar via argus serve command with /tool-call and / endpoints
  - build_app() testable seam for FastAPI endpoint unit tests
  - Exception-to-HTTP mapping (ArgusSecurityError -> 403, HITL -> 503)
  - pyproject.toml rest optional extra (fastapi, uvicorn)
affects: [integration-testing, non-python-agents, rest-clients]

# Tech tracking
tech-stack:
  added: [fastapi>=0.115, uvicorn>=0.30, httpx>=0.27 (dev)]
  patterns:
    - Lazy import of fastapi/uvicorn inside _serve_async and build_app (not module level)
    - build_app(gateway) testable seam pattern — avoids uvicorn in unit tests
    - isinstance(hitl_config, HITLConfig) guard — prevents MagicMock attribute auto-creation false positives
    - uvicorn.Server(...).serve() instead of uvicorn.run() (avoids nested event loop)
    - audit_entry in REST response mirrors AuditLogger.send canonical format

key-files:
  created: []
  modified:
    - argus/cli/serve.py
    - pyproject.toml

key-decisions:
  - "Use isinstance(hitl_config, HITLConfig) not getattr/None check — MagicMock auto-creates any attribute as truthy MagicMock"
  - "ToolCallRequest and ToolCallResponse defined at module level not inside build_app — FastAPI annotation resolution fails for locally-scoped Pydantic models"
  - "HITL guard returns 503 before calling pre_tool_call — terminal-based approval impossible over HTTP"
  - "audit_entry in response uses event_type/agent_role/tool_name keys to match AuditLogger canonical format"
  - "httpx moved to dev deps (not rest extra) — only needed by FastAPI TestClient in tests"

patterns-established:
  - "build_app(gateway) seam: inject real or mock gateway, call TestClient, assert HTTP responses — no uvicorn needed"
  - "Lazy imports of optional REST dependencies inside _serve_async with ImportError -> Exit(2) fallback"

requirements-completed: [OPS-05, OPS-06]

# Metrics
duration: 15min
completed: 2026-03-27
---

# Phase 08 Plan 02: REST Sidecar Implementation Summary

**FastAPI sidecar with /tool-call endpoint, HITL 503 guard, and ArgusSecurityError->403 mapping enabling non-Python agents to use Argus via HTTP**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-27T20:45:00Z
- **Completed:** 2026-03-27T21:00:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Replaced stub serve.py with full implementation: ToolCallRequest/ToolCallResponse models, build_app() seam, serve_command(), _serve_async()
- All 10 tests in test_serve.py GREEN: allowed=200, blocked=403, HITL=503, invalid=422, health=200, audit parity
- Updated pyproject.toml: rest extra bumped to fastapi>=0.115/uvicorn>=0.30, httpx>=0.27 in dev deps
- Full test suite: 293 passed, 0 regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement argus/cli/serve.py — full REST sidecar** - `8c213e2` (feat)
2. **Task 2: Add rest optional extra and verify full suite** - `1128545` (chore)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `argus/cli/serve.py` — Full REST sidecar: Pydantic models, build_app(), serve_command(), _serve_async() with daemon lifecycle
- `pyproject.toml` — Updated rest extra versions, added httpx to dev deps

## Decisions Made
- `isinstance(hitl_config, HITLConfig)` guard instead of `getattr(..., None)` check — MagicMock auto-creates `_hitl_config` as a truthy MagicMock when accessed, which caused false 503 returns for all non-HITL gateways in tests
- Pydantic models at module level (not inside build_app) — FastAPI's annotation resolver cannot find locally-scoped types at route registration time, causing 422 for all requests
- `uvicorn.Server(...).serve()` async pattern — `uvicorn.run()` blocks and triggers nested event loop error inside `asyncio.run()`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed MagicMock attribute auto-creation causing false HITL 503**
- **Found during:** Task 1 (test_tool_call_allowed failing with 503)
- **Issue:** `getattr(gateway, "_hitl_config", None)` on a MagicMock returns a MagicMock (truthy), not None. `hitl_config.needs_approval()` also returns a MagicMock (truthy), so all non-HITL gateways triggered 503.
- **Fix:** Changed guard to `isinstance(hitl_config, HITLConfig)` with explicit import of HITLConfig inside the route handler
- **Files modified:** argus/cli/serve.py
- **Verification:** test_tool_call_allowed passes (200), test_tool_call_hitl_returns_503 still passes (503)
- **Committed in:** 8c213e2 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed Pydantic model scope — moved models to module level**
- **Found during:** Task 1 (test_tool_call_allowed failing with 422 "Field required: req")
- **Issue:** Defining ToolCallRequest inside build_app() caused FastAPI to fail annotation resolution at route registration time, treating `req` as a query parameter instead of request body
- **Fix:** Moved ToolCallRequest and ToolCallResponse to module-level scope
- **Files modified:** argus/cli/serve.py
- **Verification:** All endpoint tests pass with correct status codes
- **Committed in:** 8c213e2 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs discovered during test-driven implementation)
**Impact on plan:** Both auto-fixes necessary for correct FastAPI behavior. No scope creep.

## Issues Encountered
Two FastAPI-specific bugs found during test execution — both fixed inline before committing Task 1.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- OPS-05 (argus serve CLI) and OPS-06 (REST /tool-call endpoint) complete
- Phase 08 (REST API sidecar) fully complete — all plans done
- Non-Python agents can now POST tool calls to Argus REST sidecar at localhost:8080

---
*Phase: 08-rest-api-sidecar*
*Completed: 2026-03-27*
