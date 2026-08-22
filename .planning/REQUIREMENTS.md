# Requirements: Argus v0.5

**Defined:** 2026-05-09
**Milestone:** v0.5 — Provenance-Aware Execution + v0.4 Stabilization
**Core Value:** Every tool call passes through deterministic enforcement code the LLM cannot influence.

## v0.5 Requirements

### v0.4 Stabilization (Phase 11)

- [ ] **CLEAN-01**: Every `anomaly_blocked` and `anomaly_warn` audit payload includes `hop_depth` alongside `caller_id` — matches the `tool_call_pre` event schema (closes INT-01, completes MAGNT-03 + ANOM-04)
- [ ] **CLEAN-02**: Gate 5.5 post-call egress `HITLGate.check` invocation forwards the configured `max_delegation_depth` so the banner renders the correct hop-out-of-max ratio (closes INT-02, completes MAGNT-07)
- [ ] **CLEAN-03**: REST sidecar 503 `hitl_unavailable` guard short-circuits before terminal-only HITL is invoked when an anomaly-only ESCALATE fires for a non-approval-gated tool (closes INT-03, completes ANOM-06)
- [ ] **CLEAN-04**: `SecurityEvent` instances constructed at the permission-block and prompt-shield call sites in `argus/security/gateway.py` populate `caller_id` and `hop_depth` from the active execution context (closes INT-04)
- [ ] **CLEAN-05**: Phase 9 and Phase 10 `VALIDATION.md` files are signed off — `nyquist_compliant: true`, `wave_0_complete: true`, all approval checkboxes ticked, with documented evidence for each Wave 0 requirement
- [ ] **CLEAN-06**: `requirements-completed:` frontmatter is populated in `09-01-SUMMARY.md`, `09-03-SUMMARY.md`, and `10-02-SUMMARY.md` so `gsd-tools summary-extract --fields requirements_completed` returns each plan's claimed REQ-IDs as structured data
- [ ] **CLEAN-07**: New regression tests cover the cleanup invariants — REST endpoint returns 403 with `violation="anomaly"` when `AnomalyBlockedError` fires, anomaly audit-payload assertions check `hop_depth` presence at every emission site, an end-to-end test sets ContextVars via the LangChain adapter and verifies `AnomalyDetector._state` is keyed by the adapter-supplied `caller_id`

### Provenance-Aware Execution (Phase 12)

- [ ] **PROV-01**: Developer can read and write instruction provenance via Python ContextVar primitives — `set_provenance(value, *, reset=True)` and `get_provenance() -> Provenance` — with values from a closed enum: `untrusted_retrieval`, `user_originated`, `system`. The API mirrors v0.4's `set_caller_context` / `get_caller_context` shape exactly.
- [ ] **PROV-02**: LangChain, CrewAI, AutoGen, MCP server wrapper, and REST sidecar adapters set the provenance ContextVar at the boundary where external content returns into LLM context — `untrusted_retrieval` for content originating outside the agent process — and reset via the established token-based finally pattern. No manual threading required by application code.
- [ ] **PROV-03**: Tools declare a `provenance_required` field in `argus.yaml` (per-tool, optional, accepts the same enum values plus `any`). Read-only tools default to `any`; write/export/delete capabilities can require `user_originated`. Misconfiguration produces a startup validation error with a clear path to the offending tool.
- [ ] **PROV-04**: A new `Gate 0.75` (between Gate 0.5 identity and Gate 1 permission) checks the active provenance against the tool's required provenance. Mismatch raises `ProvenanceViolationError` (a subclass of `ArgusSecurityError`) before the permission check runs — fail-closed, same semantics as `DelegationDepthError`.
- [ ] **PROV-05**: Audit log entries and OTel violation spans include an `argus.security.provenance` attribute on every gated tool call — present in `tool_call_pre`, all `*_blocked` events, and HITL decision events. Same emission path identity already uses (`argus.security.caller_id` → `argus.security.provenance`).
- [ ] **PROV-06**: HITL banner displays provenance alongside delegation context — when `provenance != user_originated`, prints a line like `Provenance: untrusted_retrieval` immediately above the `Delegated by:` line; otherwise omits both lines for backward compatibility.
- [ ] **PROV-07**: REST sidecar `ToolCallRequest` accepts an optional `provenance` field forwarded to the gateway. Default is `user_originated` so existing clients continue to work unchanged. The endpoint validates the value against the closed enum and returns 422 on unknown values.

## Future Requirements (v0.6+)

### Adapter Coverage
- **ADPT-08**: Developer can wrap LlamaIndex tools with SecurityGateway

### Anomaly Detection Extensions
- **ANOM-07**: Tool sequence / Markov anomaly detection for unusual tool combinations
- **ANOM-08**: Anomaly baseline persistence to SQLite across restarts

### Multi-Agent Extensions
- **MAGNT-08**: AutoGen + MCP adapter ContextVar propagation (extends MAGNT-06 to remaining adapters)

### HITL Extensions
- **HITL-06**: Webhook-based HITL approval — POST tool details, await approve/deny response

### Memory + Skill Distribution
- Redis hot memory layer + Qdrant semantic memory
- OCI skill registry via `oras-py`
- Local model support via Ollama (LiteLLM already supports it; needs validation pass)

### V2 PromptShield (research-gated)
- Classifier-based semantic injection scoring with empirical false-positive rate calibration on benign technical / compliance corpora — DO NOT ship before publishing FP numbers and the test corpus

## Out of Scope (v0.5)

| Feature | Reason |
|---------|--------|
| GUI dashboard / SaaS | Premature — CLI + REST API is sufficient |
| Model fine-tuning / alignment | Out of domain — Argus is runtime enforcement only |
| Cryptographic delegation tokens (AIP/IBCT) | Requires key infrastructure Argus doesn't have |
| LLM-mediated provenance classification | Violates core principle: deterministic enforcement only |
| Adaptive provenance auto-promotion (e.g. retrieved → user_originated after N approvals) | Trust-laundering risk; promotion requires explicit user-in-the-loop confirmation |
| Cross-process provenance state (provenance_required enforced via shared store) | Same reason as fleet-anomaly: requires Redis/deployment-model change |
| Provenance inferred from prompt content | Provenance must be set deterministically at the source boundary, not guessed from context |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLEAN-01 | Phase 11 | Pending |
| CLEAN-02 | Phase 11 | Pending |
| CLEAN-03 | Phase 11 | Pending |
| CLEAN-04 | Phase 11 | Pending |
| CLEAN-05 | Phase 11 | Pending |
| CLEAN-06 | Phase 11 | Pending |
| CLEAN-07 | Phase 11 | Pending |
| PROV-01 | Phase 12 | Pending |
| PROV-02 | Phase 12 | Pending |
| PROV-03 | Phase 12 | Pending |
| PROV-04 | Phase 12 | Pending |
| PROV-05 | Phase 12 | Pending |
| PROV-06 | Phase 12 | Pending |
| PROV-07 | Phase 12 | Pending |

**Coverage:**
- v0.5 requirements: 14 total — 7 stabilization (CLEAN-01..07) + 7 provenance (PROV-01..07)
- Mapped to phases: 14 (Phase 11: 7, Phase 12: 7) ✓
- Unmapped: 0

---
*Requirements defined: 2026-05-09 — v0.5 milestone start*
