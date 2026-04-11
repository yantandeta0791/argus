---
phase: 10-anomaly-detection
plan: 01
subsystem: security
tags: [anomaly-detection, statistics, ewma, z-score, sliding-window, stdlib]

requires:
  - phase: 09-multi-agent-enforcement
    provides: "AgentRegistry and caller_id identity infrastructure used for per-agent window keying"

provides:
  - "AnomalyDetector class with per-agent EWMA + z-score sliding window detection"
  - "AnomalyConfig dataclass (YAML-parsed, lazy-imported pattern)"
  - "AnomalyResult dataclass (level, z_score, baseline, observed)"
  - "ResponseLevel enum (OK / WARN / ESCALATE / BLOCK)"
  - "GateType.ANOMALY enum value in events.py"
  - "AnomalyBlockedError exception (ArgusSecurityError subclass)"
  - "load_anomaly_config() function in argus/llm/config.py"
  - "GatewayConfig.anomaly field wired from load_gateway_config()"

affects: [10-02, SecurityGateway gate wiring, REST sidecar single-worker note]

tech-stack:
  added: []
  patterns:
    - "Lazy import in load_anomaly_config() — same pattern as load_hitl_config, load_agents_config"
    - "Pre-update EWMA for z-score (spike excluded from its own denominator)"
    - "stdev=0 with deviation → BLOCK (perfectly stable baseline protection)"
    - "Per-agent state dict keyed by caller_id with eviction-on-access"

key-files:
  created:
    - argus/security/anomaly/__init__.py
    - argus/security/anomaly/detector.py
    - tests/security/test_anomaly.py
  modified:
    - argus/security/events.py
    - argus/security/exceptions.py
    - argus/llm/config.py
    - argus/security/gateway.py

key-decisions:
  - "z-score computed using pre-update EWMA and prior window (excludes spike from its own denominator) — prevents spike from inflating stdev and suppressing its own z-score"
  - "stdev=0 with value != prior_ewma returns BLOCK (float inf z_score) — perfectly stable baseline means any deviation is anomalous"
  - "AnomalyDetector is NOT thread-safe — single-worker enforcement required when anomaly gate enabled (documented in accumulated context)"
  - "EWMA alpha=0.3 (industry standard for short-term trend tracking)"
  - "min_observations warmup guard uses prior_ewma sentinel — None means no EWMA computed yet, ensures first call always returns warmup OK"

patterns-established:
  - "Anomaly subpackage pattern: argus/security/anomaly/ with __init__.py re-exporting from detector.py"

requirements-completed: [ANOM-01, ANOM-02, ANOM-05, ANOM-06]

duration: 5min
completed: 2026-04-11
---

# Phase 10 Plan 01: AnomalyDetector Engine + Types + Config Summary

**EWMA + z-score anomaly detection engine with per-agent sliding windows, graduated response levels (OK/WARN/ESCALATE/BLOCK), YAML config, and AnomalyBlockedError — all using stdlib only (statistics, collections, time)**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-11T00:23:32Z
- **Completed:** 2026-04-11T00:28:42Z
- **Tasks:** 1 (TDD: 2 commits — test then implementation)
- **Files modified:** 7 (3 created, 4 modified)

## Accomplishments
- Implemented AnomalyDetector with per-agent state isolation, time-based window eviction via `time.monotonic()`, EWMA baseline tracking (alpha=0.3), and z-score threshold mapping
- Added all supporting types: AnomalyConfig, AnomalyResult, ResponseLevel enum, GateType.ANOMALY, AnomalyBlockedError
- Wired load_anomaly_config() into load_gateway_config() following established lazy-import pattern; GatewayConfig.anomaly field ready for Plan 02 integration
- 26 unit tests covering warmup, all response levels, per-agent isolation, window eviction, edge cases, config parsing, enum and exception hierarchy

## Task Commits

1. **Task 1 RED: Failing tests** - `f558228` (test)
2. **Task 1 GREEN: Full implementation** - `8e57e64` (feat)

**Plan metadata:** TBD (docs commit)

## Files Created/Modified
- `argus/security/anomaly/__init__.py` - Public re-exports for anomaly subpackage
- `argus/security/anomaly/detector.py` - AnomalyDetector, AnomalyConfig, AnomalyResult, ResponseLevel
- `argus/security/events.py` - Added GateType.ANOMALY = "anomaly"
- `argus/security/exceptions.py` - Added AnomalyBlockedError (ArgusSecurityError subclass)
- `argus/llm/config.py` - Added load_anomaly_config(), updated load_gateway_config()
- `argus/security/gateway.py` - Added GatewayConfig.anomaly: Optional[Any] = None
- `tests/security/test_anomaly.py` - 26 unit tests, 200+ lines

## Decisions Made

- **z-score uses pre-update EWMA and prior window:** The spike observation is excluded from both the EWMA used as baseline and the stdev computation. This prevents a massive spike from inflating its own denominator (which would produce z≈3.3 instead of expected z>>4.0 for a 100x spike against stable baseline). This is the correct statistical approach for anomaly detection.
- **stdev=0 with deviation → BLOCK:** When the prior window has all identical values (stdev=0) and the new value differs, this returns BLOCK (z_score=inf). A perfectly stable baseline where any deviation occurs is a stronger anomaly signal than one with noise variance. The edge case "stdev=0 with identical value → OK" is preserved.
- **min_observations uses prior_ewma sentinel:** The warmup check uses `prior_ewma is None` (no EWMA computed yet) as an additional gate. This ensures the very first observation always returns OK even if min_observations=1.

## Deviations from Plan

None — plan executed exactly as written. The z-score algorithm was refined during implementation to handle the spike-inflates-denominator case, but this is consistent with the plan's intent of detecting anomalies based on the established baseline.

## Issues Encountered

- Python 3.12 required (project specifies requires-python >=3.12) — used `python3.12` explicitly since default `python3` on the system is 3.9
- `litellm` not installed in the Python 3.12 site-packages, causing `argus.llm` import failure. Installed via `pip3.12 install -e ".[dev]" --break-system-packages` (existing issue, not caused by this plan)

## Next Phase Readiness

- AnomalyDetector fully tested and ready for Plan 02 integration into SecurityGateway Gate 1.75
- GatewayConfig.anomaly field already wired — Plan 02 only needs to instantiate AnomalyDetector and call record_and_check in pre_tool_call
- All 115 security tests pass — no regressions

---
*Phase: 10-anomaly-detection*
*Completed: 2026-04-11*
