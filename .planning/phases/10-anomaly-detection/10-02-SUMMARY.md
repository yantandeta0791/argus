---
phase: 10-anomaly-detection
plan: "02"
subsystem: security-gateway
tags: [anomaly-detection, gate-1.75, gate-5.5, hitl, otel, tdd]
dependency_graph:
  requires: ["10-01"]
  provides: ["ANOM-01-enforcement", "ANOM-02-enforcement", "ANOM-03", "ANOM-04", "ANOM-06"]
  affects: ["argus.security.gateway", "argus.security.hitl"]
tech_stack:
  added: []
  patterns:
    - "AnomalyDetector injected into SecurityGateway; two instances (frequency + egress)"
    - "Gate 1.75 pre-computes anomaly before Gate 1.5 HITL for merged single-prompt path"
    - "Gate 5.5 post-redaction egress volume check; BLOCK replaces output, not exception"
key_files:
  created: []
  modified:
    - argus/security/gateway.py
    - argus/security/hitl.py
    - tests/security/test_gateway.py
    - tests/security/test_hitl.py
decisions:
  - "Gate 1.75 pre-computes anomaly result before Gate 1.5 so anomaly_context can merge into single HITL prompt"
  - "Gate 5.5 uses output replacement (not raise) for egress BLOCK to match post_tool_call contract"
  - "HITLGate anomaly-only escalation: gate fires when anomaly_context present even if needs_approval is False"
  - "hitl_decision audit event only logged when needs_hitl is True (not for anomaly-only HITL paths)"
metrics:
  duration_seconds: 274
  completed_date: "2026-04-10"
  tasks_completed: 2
  files_modified: 4
---

# Phase 10 Plan 02: Gate Integration (Anomaly Enforcement) Summary

**One-liner:** Wired AnomalyDetector into SecurityGateway as Gate 1.75 (pre-call frequency anomaly) and Gate 5.5 (post-call egress volume anomaly) with graduated HITL escalation, audit logging, and OTel span emission.

## What Was Built

### Gate 1.75 — Frequency Anomaly (pre_tool_call)

Inserted between Gate 1.5 (HITL) and Gate 2 (Audit). The gate pre-computes the anomaly result before Gate 1.5 fires so the context can be merged into a single HITL prompt when both `require_approval` and `escalate_z` trigger on the same tool call.

**Graduated response:**
- `BLOCK` — raises `AnomalyBlockedError`, sends `anomaly_blocked` audit event, emits OTel violation span
- `ESCALATE` — builds `anomaly_context` dict, passes it into `HITLGate.check()` (merged or standalone prompt)
- `WARN` — sends `anomaly_warn` audit event after HITL gate completes; no interruption
- `OK` — no action

### Gate 5.5 — Egress Volume Anomaly (post_tool_call)

Inserted between Gate 4 (Redaction) and Gate 5 (Egress allowlist). Measures `len(clean_output)` after redaction — correct gate ordering. Uses ContextVars for per-agent egress attribution.

**Graduated response:**
- `BLOCK` — replaces `clean_output` with `"[ANOMALY: output suppressed]"` (no exception — post-call contract), sends `anomaly_blocked` audit event, emits OTel violation span
- `ESCALATE` — triggers `HITLGate.check()` with egress `anomaly_context`; on `ApprovalDeniedError`, suppresses output
- `WARN` — sends `anomaly_warn` audit event; output unchanged
- `OK` — no action

### HITLGate anomaly_context parameter

Added optional `anomaly_context: dict | None = None` to `HITLGate.check()`. When present:
- Gate fires even when tool is not in `require_approval` (anomaly-only escalation path)
- Prints `[ARGUS ANOMALY]` banner before HITL tool banner and JSON input
- Banner includes: metric type, observed rate, baseline, z-score, last N recent calls
- Delegation context (`Delegated by: {caller_id} (hop {n}/{max})`) still shown when `hop_depth > 0`

### OTel severity_map update

Added `"anomaly": "HIGH"` to `_emit_violation`'s severity map.

## Test Coverage

- 9 Gate 1.75 tests (BLOCK/ESCALATE/WARN/OK/None-config/HITL-merge/OTel/severity-map)
- 9 Gate 5.5 tests (BLOCK/ESCALATE/WARN/OK/None-config/gate-order/caller-attribution/audit/OTel)
- 7 HITLGate anomaly_context tests (banner content/ordering/anomaly-only path/delegation/deny/no-banner-without-context)
- All 25 new tests pass; all 51 gateway+hitl tests pass; 140 security tests pass; 389 total pass

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] hitl_decision audit only logged for require_approval tools**

- **Found during:** Task 1 GREEN
- **Issue:** The plan's HITL restructure combined two separate audit code paths. When anomaly-only HITL fires (no `require_approval`), logging a `hitl_decision` event would be incorrect — no hitl config decision was made.
- **Fix:** Added `if needs_hitl:` guard around `hitl_decision` audit logging in both approve and deny paths. Anomaly-only HITL denials still suppress the tool call (via `ApprovalDeniedError` re-raise).
- **Files modified:** `argus/security/gateway.py`

None of the original tests broke; the fix preserves existing `test_gateway_approval_denied_propagates_audit_not_called` behavior.

## Self-Check: PASSED

Files created/modified:
- FOUND: argus/security/gateway.py
- FOUND: argus/security/hitl.py
- FOUND: tests/security/test_gateway.py
- FOUND: tests/security/test_hitl.py

Commits:
- FOUND: 7baa203 (RED tests Task 1)
- FOUND: d955fa9 (GREEN Task 1)
- FOUND: 0865045 (RED tests Task 2)
- FOUND: 7b373c3 (GREEN Task 2)
