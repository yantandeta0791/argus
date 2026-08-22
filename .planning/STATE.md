---
gsd_state_version: 1.0
milestone: v0.5
milestone_name: Provenance-Aware Execution + v0.4 Stabilization
status: executing
last_updated: "2026-05-16T03:27:06.089Z"
last_activity: 2026-05-16 -- Phase 11 planning complete
progress:
  total_phases: 2
  completed_phases: 2
  total_plans: 3
  completed_plans: 3
  percent: 100
---

# State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-09)

**Core value:** Every tool call passes through deterministic enforcement code the LLM cannot influence.
**Current focus:** v0.5 — Phase 11 (v0.4 debt closure) then Phase 12 (provenance-aware execution).

## Current Position

Milestone: v0.5 — Provenance-Aware Execution + v0.4 Stabilization (planning complete)

Phase: 11 (next — not started)
Plan: —
Status: Ready to execute
Last activity: 2026-05-16 -- Phase 11 planning complete

Progress: [░░░░░░░░░░] 0%

## Accumulated Context

- LangChain proxy pattern is the established model for all adapters; ContextVars extend it for cross-adapter identity propagation. v0.5 extends the same pattern to **instruction provenance** as a separate dimension.
- CrewAI + AutoGen + MCP + LangChain shipped under full SecurityGateway enforcement; LlamaIndex is the next adapter candidate (deferred to v0.6).
- HITL gates are terminal-only (approve/deny/timeout) at Gate 1.5; webhook HITL (HITL-06) deferred to v0.6.
- Policy-as-code via argus.yaml is the single config surface — all gate configs parsed by `load_gateway_config`.
- `argus audit` streams JSONL (no load-all); OTel emits to Datadog/Grafana/OTLP via single OTLPSpanExporter.
- REST sidecar (`argus serve`) enables non-Python agents; single-worker enforcement required when anomaly detection is enabled.
- Anomaly detection is stdlib-only (EWMA + z-score); cold-start warmup suppresses escalation until baseline is established.
- Gate order (post-v0.5): 0.5 Identity → **0.75 Provenance** (NEW) → 1 Permission → 1.5 HITL → 1.75 Anomaly (pre) → 2 Audit pre → [execute] → 3 Injection → 4 Redaction → 5.5 Egress anomaly → 5 Egress allowlist → 6 Audit post.
- Provenance values: `untrusted_retrieval` (RAG, web fetch, MCP server response, file read of user-uploaded content) | `user_originated` (direct user prompt) | `system` (config or framework-internal). Tagging happens at the adapter return boundary, identical pattern to v0.4 caller_id/hop_depth.
- **Phase 11 sequencing rationale:** Phase 12 introduces a new Gate (0.75) and extends audit/OTel/HITL emission paths. Doing this on top of an unclean v0.4 baseline (missing `hop_depth` in anomaly payloads, unpopulated `SecurityEvent` fields) would compound the integration debt. Phase 11 first delivers a clean substrate.

## Open Blockers / v0.4 Debt Being Closed in Phase 11

- **CLEAN-01 (closes INT-01 / completes MAGNT-03 + ANOM-04)** — `hop_depth` missing in 5 anomaly audit emission sites in `argus/security/gateway.py`
- **CLEAN-02 (closes INT-02 / completes MAGNT-07)** — Gate 5.5 post-call HITL banner does not forward `max_depth`
- **CLEAN-03 (closes INT-03 / completes ANOM-06)** — REST sidecar 503 guard does not cover anomaly-only ESCALATE; worker can hang on stdin
- **CLEAN-04 (closes INT-04)** — `SecurityEvent.caller_id`/`hop_depth` not populated at `gateway.py:181-187` and `323-328`
- **CLEAN-05** — Phase 9 + 10 `VALIDATION.md` still `nyquist_compliant: false`, `wave_0_complete: false`
- **CLEAN-06** — `requirements-completed:` frontmatter missing in 09-01, 09-03, 10-02 SUMMARY.md
- **CLEAN-07** — Test coverage backfill (REST AnomalyBlockedError 403, audit hop_depth assertions, adapter→Gate 1.75 keying E2E)

## Key Decisions

Full decision log lives in `.planning/PROJECT.md` → Key Decisions. STATE.md no longer duplicates.

## Session Continuity

Next action: `/gsd-plan-phase 11` to decompose the v0.4 integration debt closure into executable plans, then `/gsd-plan-phase 12` for the provenance-aware execution layer.
Roadmap: .planning/ROADMAP.md (v0.5 — Phases 11 & 12 defined, success criteria locked)
Requirements: .planning/REQUIREMENTS.md (14 REQ-IDs mapped: CLEAN-01..07 → Phase 11, PROV-01..07 → Phase 12)
Archive: .planning/milestones/v0.4-ROADMAP.md, v0.4-REQUIREMENTS.md, v0.4-MILESTONE-AUDIT.md

---
*State initialized: 2026-03-15*
*Milestone: v0.5 (planning complete; execution pending)*
*Last updated: 2026-05-09 — v0.5 roadmap created (Phases 11–12)*
