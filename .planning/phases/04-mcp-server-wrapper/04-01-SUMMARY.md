---
phase: 04-mcp-server-wrapper
plan: "01"
subsystem: testing
tags: [mcp, fastmcp, tdd, middleware, security]

# Dependency graph
requires:
  - phase: 03-crewai-autogen-adapters
    provides: adapter pattern (stub modules in sys.modules, gateway gates via pre/post_tool_call)
provides:
  - RED test suite defining behavioral contracts for wrap_mcp_server() and ArgusMCPMiddleware
affects:
  - 04-02 (MCP adapter implementation — turns these tests GREEN)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Stub fastmcp/mcp modules injected via autouse monkeypatch fixture (no hard dep on real packages)
    - Top-level import of adapter module triggers RED immediately (confirms no implementation yet)
    - _StubMiddleware as base class enables ArgusMCPMiddleware subclassing in tests

key-files:
  created:
    - tests/adapters/test_mcp.py
  modified: []

key-decisions:
  - "Top-level import of argus.adapters.mcp at module level (not inside test body) ensures clean RED failure at collection time"
  - "ToolError stubbed as plain Exception so tests work without fastmcp installed — adapter must re-raise as its own ToolError"
  - "Five tests cover the full gateway contract: pre fires, post fires, pre-block prevents tool call, post-block after tool ran, None args coerced"

patterns-established:
  - "MCP stub pattern: create ModuleType for fastmcp, fastmcp.server.middleware, fastmcp.exceptions, mcp, mcp.types and inject all five"
  - "_StubServer with .add_middleware() list for verifying middleware attachment in wrap_mcp_server tests"

requirements-completed: [ADPT-05, ADPT-06]

# Metrics
duration: 5min
completed: 2026-03-22
---

# Phase 4 Plan 01: MCP Server Wrapper RED Tests Summary

**RED test suite with stub fastmcp/mcp modules defining gateway contract for ArgusMCPMiddleware.on_call_tool() and wrap_mcp_server()**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-23T00:32:44Z
- **Completed:** 2026-03-23T00:37:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created `tests/adapters/test_mcp.py` with stub fastmcp/mcp modules injected via autouse fixture
- Defined 5 behavioral tests covering pre_tool_call firing, post_tool_call firing, permission-denied block (tool never called), injection-detected block (tool did run), and None-arguments coercion
- Verified RED state: `pytest tests/adapters/test_mcp.py -x` exits non-zero with `ModuleNotFoundError: No module named 'argus.adapters.mcp'`
- Added `TestWrapMcpServer` confirming wrap_mcp_server() attaches ArgusMCPMiddleware and returns the same server object

## Task Commits

Each task was committed atomically:

1. **Task 1: Write RED test suite for MCP adapter** - `c865ece` (test)

**Plan metadata:** (docs commit — in progress)

## Files Created/Modified

- `tests/adapters/test_mcp.py` - RED test suite for MCP adapter covering ADPT-05 and ADPT-06

## Decisions Made

- Top-level import of `argus.adapters.mcp` at module level ensures pytest collection fails immediately with ImportError, confirming RED state without ambiguity.
- `ToolError` stubbed as `Exception` so tests can assert `pytest.raises(Exception)` — the real adapter will raise `ToolError` which is a subclass of `Exception`.
- Used five tests (not four) — split "gateway fires" into two tests (pre+post together, and post-text-replacement) for clearer behavioral specification.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- RED test suite complete; plan 02 can now implement `argus/adapters/mcp.py` to turn all tests GREEN.
- Stub pattern mirrors test_autogen.py exactly — implementation author has clear reference.

---
*Phase: 04-mcp-server-wrapper*
*Completed: 2026-03-22*
