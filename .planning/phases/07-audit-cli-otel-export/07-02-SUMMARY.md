---
phase: 07-audit-cli-otel-export
plan: 02
subsystem: cli
tags: [typer, rich, jsonl, audit, streaming, panels]

# Dependency graph
requires:
  - phase: 07-01
    provides: RED test suites for OPS-01 and OPS-02 audit CLI tests
provides:
  - argus audit CLI command with streaming JSONL reader and Rich panel rendering
  - Outcome-based border colors (blocked=red, allowed=green, redacted=yellow)
  - Filter flags --type, --severity, --since, --until (AND semantics)
  - Friendly empty/missing log handling (exit 0)
  - Zero-match filter message (exit 0)
affects:
  - 07-03 (OTel export wiring that reuses audit log path)
  - Phase 08 (REST sidecar that wraps full stack)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Streaming generator pattern for JSONL: open file, yield one line at a time — never load full file"
    - "Outcome-to-border-color mapping dict for Rich panel styling"
    - "All-AND filter composition: type_filter AND severity AND since_dt AND until_dt"

key-files:
  created:
    - argus/cli/audit.py
  modified:
    - argus/cli/main.py

key-decisions:
  - "--since/--until use relative duration strings only (30m, 1h, 2d) — no ISO-8601 per prior decision"
  - "--type accepts exact GateType enum values only — no aliases"
  - "prev_hash and event_id are never rendered — chain integrity fields for internal use only"
  - "Empty/missing log: friendly message + exit 0 (not exit 1)"
  - "Zero-match filter: 'No events match your filter' + exit 0"

patterns-established:
  - "audit_command uses streaming generator _iter_events — no readlines() or file.read() for large-file safety"
  - "Severity derived from gate+outcome mapping, not stored in event — _derive_severity(event)"

requirements-completed: [OPS-01, OPS-02]

# Metrics
duration: 2min
completed: 2026-03-27
---

# Phase 7 Plan 02: Audit CLI Command Summary

**Terminal-native `argus audit` command streams JSONL log into Rich panels with outcome-based border colors (red/green/yellow) and four filter flags (--type, --severity, --since, --until)**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-27T18:11:23Z
- **Completed:** 2026-03-27T18:13:39Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- Implemented `argus/cli/audit.py` with streaming JSONL reader (generator, not load-all)
- Rich Panel rendering with outcome-based border colors: blocked=red, allowed=green, redacted=yellow
- Four filter flags with AND semantics: --type (gate exact match), --severity (CRITICAL/HIGH/INFO), --since (relative duration), --until (relative duration)
- Graceful handling: empty/missing log prints friendly message and exits 0; zero-match filter prints "No events match your filter" and exits 0
- chain fields (prev_hash, event_id) never appear in rendered output
- Registered `audit_command` in `argus/cli/main.py` following run/scan/demo pattern
- All 10 OPS-01/OPS-02 tests pass GREEN; full CLI suite (20 tests) unaffected

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement argus/cli/audit.py with streaming reader, panel rendering, and filters** - `a8ed243` (feat)

**Plan metadata:** (docs commit — following this summary)

## Files Created/Modified
- `argus/cli/audit.py` - Full audit CLI implementation: duration parser, streaming reader, severity deriver, event filter, panel renderer, main command
- `argus/cli/main.py` - Added `from argus.cli.audit import audit_command` and `app.command(name="audit")(audit_command)` in `_register()`

## Decisions Made
- Used `_derive_severity()` function rather than reading a severity field — consistent with events not storing pre-computed severity
- Duration strings only (no ISO-8601) for --since/--until: matches prior project decision in STATE.md
- Panel content shows only: timestamp, gate type, outcome, tool name, agent role, rule triggered — everything else omitted

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- OPS-01 and OPS-02 now GREEN — `argus audit` is fully functional
- Plan 07-03 remaining: OTel config loading, violation spans, and gateway wiring
- No blockers for 07-03

---
*Phase: 07-audit-cli-otel-export*
*Completed: 2026-03-27*
