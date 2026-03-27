---
phase: 07-audit-cli-otel-export
plan: "01"
subsystem: testing
tags: [tdd, red-tests, cli, otel, audit, security]
dependency_graph:
  requires: []
  provides:
    - "RED test contracts for OPS-01 through OPS-04 behaviors"
    - "tests/cli/test_audit.py — 10 RED tests for argus audit CLI"
    - "tests/llm/test_config.py — 5 RED tests for OTel config loading and wiring"
    - "tests/observability/test_otel.py — 1 RED test for emit_security_violation"
    - "tests/security/test_gateway.py — 1 RED test for gateway OTel wiring"
  affects:
    - "Plans 07-02 and 07-03 implement production code to make these RED tests GREEN"
tech_stack:
  added: []
  patterns:
    - "Module-level import for CLI tests forces collection-time RED (ModuleNotFoundError)"
    - "Function-body imports for config/otel/gateway tests fail at call time (ImportError/TypeError)"
    - "InMemorySpanExporter for OTel span assertions"
    - "CliRunner from typer.testing for CLI invocation"
    - "_make_event() helper for JSONL fixture creation"
key_files:
  created:
    - tests/cli/test_audit.py
  modified:
    - tests/llm/test_config.py
    - tests/observability/test_otel.py
    - tests/security/test_gateway.py
decisions:
  - "Module-level import in test_audit.py ensures RED at collection time, not assertion time — consistent with existing MCP test pattern"
  - "Function-body imports in test_config.py preserve existing GREEN tests while making new tests RED at call time — matches existing POLC test style"
  - "test_load_gateway_config_with_otel_builds_emitter is intentionally RED for three independent reasons: GatewayConfig.otel missing, build_security_otel_emitter missing, SecurityGateway.security_otel parameter missing"
metrics:
  duration: "~3 minutes"
  completed: "2026-03-27"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 3
---

# Phase 7 Plan 01: RED Test Suites for OPS-01 through OPS-04 Summary

**One-liner:** Failing test contracts for audit CLI display/filtering, OTel config loading, security violation span emission, and config-to-gateway wiring.

## What Was Built

Created 17 new failing test functions across 4 files establishing behavioral contracts for all Phase 7 requirements before any production code exists.

### Task 1 — tests/cli/test_audit.py (OPS-01, OPS-02)

10 test functions. Module-level `from argus.cli.audit import audit_command` guarantees `ModuleNotFoundError` at pytest collection time.

**OPS-01 tests (display):**
- `test_audit_prints_events` — Verifies tool_name appears for each event in JSONL log
- `test_audit_empty_log_exits_zero` — Empty file yields "No audit events found", exit 0
- `test_audit_missing_log_exits_zero` — Non-existent path yields "No audit events found", exit 0
- `test_audit_hides_chain_fields` — prev_hash and event_id are NOT shown in output
- `test_audit_outcome_colors` — Both "blocked" and "allowed" render in output

**OPS-02 tests (filtering):**
- `test_audit_filter_type` — `--type permission` hides egress events
- `test_audit_filter_severity` — `--severity HIGH` shows only blocked events
- `test_audit_filter_since` — `--since 1h` hides events older than 1 hour
- `test_audit_filter_until` — `--until 1h` hides recent events, shows old
- `test_audit_filter_no_match_exits_zero` — "No events match" when filter finds nothing

### Task 2 — Three Existing Test Files (OPS-03, OPS-04)

**tests/llm/test_config.py — 5 new tests:**
- `test_load_otel_config_returns_none_when_absent` — {} returns None
- `test_load_otel_config_parses_endpoint_and_exporter` — parses exporter + endpoint
- `test_load_otel_config_substitutes_env_vars` — ${VAR} placeholder expansion
- `test_load_otel_config_defaults` — safe defaults when otel section is empty
- `test_load_gateway_config_with_otel_builds_emitter` — full OPS-03+OPS-04 wiring path

**tests/observability/test_otel.py — 1 new test:**
- `test_emit_security_violation_span` — InMemorySpanExporter captures span with correct name and 4 attributes

**tests/security/test_gateway.py — 1 new test:**
- `test_gateway_emits_violation_on_permission_block` — SecurityGateway calls mock_otel.emit_security_violation after PermissionDeniedError

## RED State Confirmed

| File | RED Reason |
|------|-----------|
| tests/cli/test_audit.py | `ModuleNotFoundError: No module named 'argus.cli.audit'` at collection |
| test_load_otel_config_* | `ImportError: cannot import name 'load_otel_config'` at call time |
| test_load_gateway_config_with_otel_builds_emitter | `ImportError: cannot import name 'build_security_otel_emitter'` (first failure) |
| test_emit_security_violation_span | `AttributeError: 'OtelEmitter' has no attribute 'emit_security_violation'` |
| test_gateway_emits_violation_on_permission_block | `TypeError: SecurityGateway.__init__() got an unexpected keyword argument 'security_otel'` |

## Existing Tests: All GREEN

- 23 existing tests in test_config.py: PASS
- 4 existing tests in test_otel.py: PASS
- 13 existing tests in test_gateway.py: PASS

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 2c95070 | test(07-01): add failing RED tests for argus audit CLI (OPS-01, OPS-02) |
| 2 | f2eaf9c | test(07-01): add failing RED tests for OTel config, violation spans, gateway wiring (OPS-03, OPS-04) |

## Self-Check: PASSED

- [x] tests/cli/test_audit.py exists (10 functions)
- [x] tests/llm/test_config.py appended (5 new functions)
- [x] tests/observability/test_otel.py appended (1 new function)
- [x] tests/security/test_gateway.py appended (1 new function)
- [x] All 17 new tests RED for correct reasons
- [x] 40 existing tests GREEN
- [x] Task commits 2c95070 and f2eaf9c exist
