---
phase: "08-rest-api-sidecar"
plan: "01"
subsystem: "REST API Sidecar — TDD RED"
tags: [tdd, red, rest, serve, fastapi, osp-05, ops-06]
dependency_graph:
  requires: []
  provides:
    - "tests/cli/test_serve.py — RED test suite (10 tests) defining OPS-05 and OPS-06 contract"
    - "argus/cli/serve.py — importable stub with serve_command and build_app seam"
  affects:
    - "argus/cli/main.py — serve_command registered"
    - "pyproject.toml — [rest] optional extra added"
tech_stack:
  added: ["fastapi>=0.100", "uvicorn>=0.20", "httpx>=0.24 (via [rest] extra)"]
  patterns: ["TDD RED/GREEN/REFACTOR", "build_app(gateway) test seam", "FastAPI TestClient for endpoint tests"]
key_files:
  created:
    - "tests/cli/test_serve.py"
    - "argus/cli/serve.py"
  modified:
    - "argus/cli/main.py"
    - "pyproject.toml"
decisions:
  - "serve_command stub accepts --config/--host/--port params so Typer invokes it (raising NotImplementedError/exit 1) instead of exiting 2 for parse error — gives unambiguous RED signal"
  - "build_app(gateway) as the test seam — tests construct a gateway with mocked internals, pass to build_app, test via TestClient — no subprocess invocation needed"
  - "HITL over HTTP returns 503 with violation=hitl_unavailable — terminal HITL cannot block HTTP requests; service returns 503 before calling pre_tool_call"
  - "fastapi/uvicorn/httpx added as [rest] optional extra — consistent with [mcp], [crewai], [autogen] pattern"
  - "test_tool_call_hitl_returns_503 inspects gateway._hitl_config directly — endpoint must check for HITL before calling gateway, without going through the blocking terminal gate"
metrics:
  duration: "~3 minutes"
  completed: "2026-03-27"
  tasks_completed: 2
  files_changed: 4
---

# Phase 8 Plan 1: REST API Sidecar RED Test Suite Summary

**One-liner:** 10-test RED suite for `argus serve` and POST /tool-call using FastAPI TestClient with build_app(gateway) seam.

## What Was Built

### Task 1: RED Test Suite (`tests/cli/test_serve.py`)

10 tests covering the full behavioral contract for OPS-05 (`argus serve` CLI) and OPS-06 (POST /tool-call endpoint):

**Section 1 — CLI tests (Typer CliRunner):**
- `test_serve_missing_config_exits_2` — serve with non-existent config exits 2
- `test_serve_prints_address` — serve with valid config prints "listening on http://" (uvicorn mocked)

**Section 2 — Endpoint tests (FastAPI TestClient via `build_app` seam):**
- `test_tool_call_allowed` — allowed tool returns 200, decision="allow", audit_entry present
- `test_tool_call_blocked_permission` — PermissionDeniedError maps to 403, violation="permission"
- `test_tool_call_blocked_injection` — InjectionDetectedError maps to 403, violation="prompt_shield"
- `test_tool_call_invalid_body` — missing required fields returns 422 (Pydantic validation)
- `test_tool_call_hitl_returns_503` — HITL-configured tool returns 503, violation="hitl_unavailable"
- `test_tool_call_with_output_runs_post_gate` — tool_output field triggers both pre and post gates
- `test_audit_entry_structure_parity` — audit_entry has event_type, agent_role, tool_name keys
- `test_health_check` — GET / returns 200, status="ok"

### Task 2: Stub + Registration

- `argus/cli/serve.py` — importable stub: `serve_command()` (raises NotImplementedError) and `build_app(gateway)` (raises NotImplementedError)
- `serve_command` stub declares `--config`, `--host`, `--port` parameters so Typer invokes it rather than exiting 2 for parse error
- `argus/cli/main.py` — `serve_command` registered in `_register()`
- `pyproject.toml` — `[rest]` optional extra with fastapi, uvicorn, httpx

## Verification

1. `python -m pytest tests/cli/test_serve.py --co -q` — 10 tests collected, 0 skipped
2. `python -m pytest tests/cli/test_serve.py` — **10 failed (RED state confirmed)**
3. `python -c "from argus.cli.serve import serve_command, build_app"` — imports succeed
4. `python -m pytest tests/ --ignore=tests/cli/test_serve.py` — 283 passed, 1 skipped

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] fastapi/uvicorn/httpx not installed**
- **Found during:** Task 1 verification
- **Issue:** `ModuleNotFoundError: No module named 'uvicorn'` prevented test collection
- **Fix:** Installed fastapi, uvicorn, httpx via pip; added `[rest]` extra to pyproject.toml
- **Files modified:** `pyproject.toml`
- **Commit:** a9813f4

**2. [Rule 1 - Bug] test_serve_missing_config_exits_2 passed accidentally (RED violation)**
- **Found during:** Task 2 verification
- **Issue:** Stub `serve_command()` had no parameters; Typer returned exit 2 for "No such option: --config" — test passed accidentally
- **Fix:** Added `--config`/`--host`/`--port` parameters to stub so Typer invokes serve_command, which raises NotImplementedError (exit 1), causing the assertion `exit_code == 2` to fail (true RED)
- **Files modified:** `argus/cli/serve.py`
- **Commit:** a9813f4

## Self-Check: PASSED

- tests/cli/test_serve.py: FOUND
- argus/cli/serve.py: FOUND
- 08-01-SUMMARY.md: FOUND
- commit 3ee707f: FOUND
- commit a9813f4: FOUND
