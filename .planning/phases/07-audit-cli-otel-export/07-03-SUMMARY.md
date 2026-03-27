---
phase: 07-audit-cli-otel-export
plan: "03"
subsystem: observability
tags: [opentelemetry, otlp, otel, security, gateway, config, grpc]

requires:
  - phase: 07-01
    provides: RED test contracts for OPS-03 and OPS-04 violation span emission

provides:
  - OtelConfig dataclass with exporter/endpoint/headers fields
  - load_otel_config() section loader with ${ENV_VAR} header substitution
  - emit_security_violation() method on OtelEmitter with fail-open error handling
  - build_security_otel_emitter() factory for OTLPSpanExporter construction
  - GatewayConfig.otel field wired through load_gateway_config
  - SecurityGateway.security_otel injection parameter with _emit_violation helper
  - Violation spans emitted on permission block, HITL deny, injection block, redaction diff

affects:
  - SecurityGateway callers (must construct emitter and pass as security_otel)
  - argus.yaml users adding otel: section

tech-stack:
  added: [opentelemetry-exporter-otlp-proto-grpc>=1.20, grpcio, googleapis-common-protos, opentelemetry-exporter-otlp-proto-common]
  patterns:
    - "Fail-open OTel emission: try/except in emit_security_violation never propagates to security enforcement path"
    - "Local TracerProvider per OtelEmitter instance — no global trace.set_tracer_provider() calls"
    - "Headers as tuple-of-tuples for gRPC OTLP exporter (not dict)"
    - "Lazy-typed otel field on GatewayConfig (Optional[Any]) to avoid circular imports between argus.llm and argus.security"
    - "Violation span emission only on blocked/denied outcomes — allowed calls emit nothing"

key-files:
  created: []
  modified:
    - argus/llm/config.py
    - argus/observability/otel.py
    - argus/security/gateway.py
    - pyproject.toml

key-decisions:
  - "Datadog and Grafana backends treated as OTLP aliases — no special exporter handling, same OTLPSpanExporter for all"
  - "Emitter injected into SecurityGateway via security_otel parameter — not constructed internally (separation of concerns)"
  - "load_otel_config returns OtelConfig even for empty otel:{} section (uses defaults), returns None only when otel key absent"
  - "Egress violations do NOT emit OTel spans — egress is log-only in v1, not a blocked outcome"
  - "Headers tuple-of-tuples passed to OTLPSpanExporter to avoid gRPC dict pitfall"

patterns-established:
  - "Violation span wiring: catch block -> obs.on_security_event -> _emit_violation (consistent ordering)"
  - "Redaction violation detected via output diff (clean_output != tool_output) not exception"

requirements-completed: [OPS-03, OPS-04]

duration: 15min
completed: 2026-03-27
---

# Phase 7 Plan 03: OTel Security Violation Span Emission Summary

**OtelConfig dataclass + load_otel_config section loader + emit_security_violation on OtelEmitter + SecurityGateway violation span wiring via OTLPSpanExporter with fail-open error handling**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-27T18:15:00Z
- **Completed:** 2026-03-27T18:30:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `OtelConfig` dataclass and `load_otel_config()` section loader with `${ENV_VAR}` substitution in header values, wired into `load_gateway_config` to pass `otel=` to `GatewayConfig`
- Added `emit_security_violation()` to `OtelEmitter` emitting `argus.security.violation` spans with event_type, tool_name, severity, and agent_role attributes — wrapped in fail-open try/except
- Added `build_security_otel_emitter()` factory using `OTLPSpanExporter` with headers as tuple-of-tuples; added `security_otel` parameter to `SecurityGateway` with `_emit_violation()` helper wired into Gate 1 (permission), Gate 1.5 (HITL deny), Gate 3 (injection), and Gate 4 redaction diff check
- Added `opentelemetry-exporter-otlp-proto-grpc` dependency; all 283 tests pass with zero regressions

## Task Commits

1. **Task 1: Add OtelConfig, load_otel_config, emit_security_violation, build_security_otel_emitter** - `a41922f` (feat)
2. **Task 2: Wire SecurityGateway to emit violation spans and complete config-to-gateway path** - `12a91dc` (feat)

## Files Created/Modified

- `argus/llm/config.py` - Added OtelConfig dataclass, load_otel_config() loader, updated load_gateway_config() to include otel field
- `argus/observability/otel.py` - Added emit_security_violation() method, build_security_otel_emitter() factory, security span attribute constants
- `argus/security/gateway.py` - Added GatewayConfig.otel field, SecurityGateway.security_otel parameter, _emit_violation() helper, violation span wiring in all gate catch blocks and redaction diff
- `pyproject.toml` - Added opentelemetry-exporter-otlp-proto-grpc dependency (added via uv add)

## Decisions Made

- `load_otel_config` returns `OtelConfig` (with defaults) even when `otel: {}` is empty — only returns `None` when the `otel` key is entirely absent from the raw dict (empty dict has a different meaning than missing key)
- Datadog and Grafana treated as OTLP aliases — no custom exporter paths needed in v1
- Emitter passed into SecurityGateway via constructor injection (not built internally) so callers control lifecycle
- Egress gate does not emit violation spans — egress is log-only (not a block outcome) in v1

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed load_otel_config returning None for empty otel: {} section**
- **Found during:** Task 1 (verifying test_load_otel_config_defaults)
- **Issue:** Original implementation used `otel_raw = raw.get("otel") or {}; if not otel_raw: return None` which caused `{"otel": {}}` to return None instead of OtelConfig with defaults
- **Fix:** Changed to `if "otel" not in raw: return None` to distinguish missing key from empty dict
- **Files modified:** argus/llm/config.py
- **Verification:** test_load_otel_config_defaults passes GREEN
- **Committed in:** a41922f (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Required for correct behavior — empty `otel: {}` section should use defaults, not return None.

## Issues Encountered

None - implementation went smoothly after the otel key detection fix.

## User Setup Required

Callers that construct `SecurityGateway` directly must perform the 2-line wiring when `config.otel` is present:

```python
from argus.observability.otel import build_security_otel_emitter
security_otel = build_security_otel_emitter(config.otel) if config.otel else None
gateway = SecurityGateway(config=config, audit_logger=..., security_otel=security_otel)
```

## Next Phase Readiness

- Phase 7 complete: audit CLI (07-02) + OTel violation spans (07-03) fully implemented
- Phase 8 (REST sidecar) can now proceed — full security stack including OTel emission is stable
- OPS-01 through OPS-04 requirements all fulfilled

---
*Phase: 07-audit-cli-otel-export*
*Completed: 2026-03-27*
