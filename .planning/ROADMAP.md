# Roadmap: Argus

## Milestones

- ✅ **v0.2.0 Security Foundation + LangChain** — Phases 1–2 (shipped 2026-03-08)
- ✅ **v0.3 Framework Adapters + Operationalization** — Phases 3–8 (shipped 2026-03-28)
- ✅ **v0.4 Multi-Agent + Anomaly Detection** — Phases 9–10 (shipped 2026-04-20) — see [milestones/v0.4-ROADMAP.md](milestones/v0.4-ROADMAP.md)
- 🚧 **v0.5 Provenance-Aware Execution + v0.4 Stabilization** — Phases 11–12 (in progress, started 2026-05-09)

## Phases

<details>
<summary>✅ v0.2.0 Security Foundation + LangChain (Phases 1–2) — SHIPPED 2026-03-08</summary>

- [x] Phase 1: Security Core (bootstrapped outside GSD) — completed 2026-03-08
- [x] Phase 2: LangChain Adapter (bootstrapped outside GSD) — completed 2026-03-08

</details>

<details>
<summary>✅ v0.3 Framework Adapters + Operationalization (Phases 3–8) — SHIPPED 2026-03-28</summary>

- [x] Phase 3: CrewAI + AutoGen Adapters (3/3 plans) — completed 2026-03-23
- [x] Phase 4: MCP Server Wrapper (2/2 plans) — completed 2026-03-23
- [x] Phase 5: Human-in-the-Loop Gates (2/2 plans) — completed 2026-03-23
- [x] Phase 6: Policy-as-Code (3/3 plans) — completed 2026-03-27
- [x] Phase 7: Audit CLI + OTel Export (3/3 plans) — completed 2026-03-27
- [x] Phase 8: REST API Sidecar (2/2 plans) — completed 2026-03-27

</details>

<details>
<summary>✅ v0.4 Multi-Agent + Anomaly Detection (Phases 9–10) — SHIPPED 2026-04-20</summary>

- [x] Phase 9: Multi-Agent Enforcement (3/3 plans) — completed 2026-04-09
- [x] Phase 10: Anomaly Detection (2/2 plans) — completed 2026-04-11

**Known gaps carried to v0.5:** see `.planning/MILESTONES.md` → v0.4 → Known Gaps (INT-01/02/03/04, Nyquist sign-off, frontmatter debt) — closed in Phase 11.

</details>

### 🚧 v0.5 Provenance-Aware Execution + v0.4 Stabilization (Phases 11–12)

- [ ] **Phase 11: v0.4 Integration Debt Closure** (3 plans planned 2026-05-15) — Close partial requirements (MAGNT-03/07, ANOM-04/06), populate SecurityEvent identity fields, complete Nyquist sign-off, backfill SUMMARY frontmatter, add regression tests
- [ ] **Phase 12: Provenance-Aware Execution** — Add deterministic instruction-provenance dimension with Gate 0.75; provenance set at adapter boundaries via ContextVar; audit + OTel + HITL banner + REST sidecar field integration

## Phase Details

### Phase 11: v0.4 Integration Debt Closure
**Goal**: Bring v0.4 to 100% requirement satisfaction by closing the four partial requirements (MAGNT-03, MAGNT-07, ANOM-04, ANOM-06), populating SecurityEvent identity fields at remaining call sites, completing Nyquist sign-off for Phases 9 and 10, backfilling SUMMARY frontmatter, and adding regression tests so the gaps don't recur.
**Depends on**: Phase 10 (v0.4 shipped)
**Requirements**: CLEAN-01, CLEAN-02, CLEAN-03, CLEAN-04, CLEAN-05, CLEAN-06, CLEAN-07
**Success Criteria** (what must be TRUE):
  1. Every `anomaly_blocked` and `anomaly_warn` audit payload emitted by `argus/security/gateway.py` carries both `caller_id` and `hop_depth` — schema parity with `tool_call_pre` is verifiable by inspecting any audit log line at all five emission sites (gateway.py lines 229, 314, 386, 423, 443 — verified against HEAD by RESEARCH.md).
  2. A REST client invoking a non-approval-gated tool that triggers an anomaly-only ESCALATE (Gate 1.75 frequency OR Gate 5.5 egress, per D-03) receives a `503` response with `violation="anomaly_escalate"` and the verbatim HITL banner schema in the body (D-01/D-02); the worker process never reaches `HITLGate.check()` over stdin.
  3. `SecurityEvent` records produced at the permission-block (gateway.py:198) and prompt-shield (gateway.py:357) call sites have `caller_id` and `hop_depth` populated from the active execution context via `SecurityEvent.from_context()` — no longer `None`. (Line numbers updated per RESEARCH.md verification — CONTEXT.md refs 181-187 / 323-328 are stale.)
  4. Phase 9 and Phase 10 `VALIDATION.md` files are signed off (`nyquist_compliant: true`, `wave_0_complete: true`, all approval checkboxes ticked) and `gsd-tools summary-extract --fields requirements_completed` returns the correct REQ-IDs for `09-01-SUMMARY.md` ([MAGNT-01, MAGNT-02, MAGNT-03, MAGNT-05]), `09-03-SUMMARY.md` ([MAGNT-06]), and `10-02-SUMMARY.md` ([ANOM-01, ANOM-02, ANOM-03, ANOM-04, ANOM-06]).
  5. The regression test suite includes (a) a REST endpoint test that returns 403 with `violation="anomaly"` when `AnomalyBlockedError` fires, (b) `hop_depth`-presence assertions on every anomaly audit payload site in `tests/security/test_gateway.py` (shared `_assert_audit_carries_identity` helper invoked at all 5 sites), (c) an end-to-end LangChain-adapter → Gate 1.75 test that proves `AnomalyDetector._state` is keyed by the adapter-supplied `caller_id`, and (d) a REST endpoint test that returns 503 with `violation="anomaly_escalate"` and the full HITL banner schema when `AnomalyEscalateError` fires.
**Plans**: 3 plans
- [ ] 11-01-PLAN.md — Mechanical fixes + SecurityEvent refactor (CLEAN-01, CLEAN-02, CLEAN-04)
- [ ] 11-02-PLAN.md — REST anomaly_escalate response + regression tests (CLEAN-03, CLEAN-07)
- [ ] 11-03-PLAN.md — Documentation hygiene (Nyquist sign-off + SUMMARY frontmatter) (CLEAN-05, CLEAN-06)

### Phase 12: Provenance-Aware Execution
**Goal**: Add a deterministic instruction-provenance dimension orthogonal to v0.4's `caller_id`, with a new Gate 0.75 (between identity and permission), provenance set at every external-content-returning adapter boundary via the established ContextVar pattern, and provenance carried through audit + OTel + HITL banner + REST sidecar — so write/export/delete tools are gated against where the triggering instruction came from (user vs retrieval vs system).
**Depends on**: Phase 11 (clean v0.4 baseline required before extending the Gate stack)
**Requirements**: PROV-01, PROV-02, PROV-03, PROV-04, PROV-05, PROV-06, PROV-07
**Success Criteria** (what must be TRUE):
  1. A developer can call `set_provenance("untrusted_retrieval")` and `get_provenance()` from Python code, with the API mirroring `set_caller_context` / `get_caller_context` exactly (closed enum: `untrusted_retrieval | user_originated | system`, token-based reset, async-safe via ContextVar).
  2. When a tool wrapped by any of LangChain, CrewAI, AutoGen, MCP, or REST sidecar adapters returns external content into LLM context, the active provenance is `untrusted_retrieval` for the duration of the LLM's next decision — no application-level threading required.
  3. A tool declared with `provenance_required: user_originated` in `argus.yaml` invoked while the active provenance is `untrusted_retrieval` raises `ProvenanceViolationError` (subclass of `ArgusSecurityError`) before the permission check runs — fail-closed, identical semantics to `DelegationDepthError`.
  4. Every gated tool call's `tool_call_pre` audit event, every `*_blocked` event, every HITL decision event, and every OTel violation span carries an `argus.security.provenance` attribute alongside `argus.security.caller_id`.
  5. When the active provenance is not `user_originated`, the HITL approval banner displays a `Provenance: <value>` line immediately above the `Delegated by:` line; when provenance is `user_originated`, the banner is unchanged from v0.4 (backward compatible).
  6. A REST client posting `ToolCallRequest` with `"provenance": "untrusted_retrieval"` sees that value enforced at Gate 0.75; clients that omit the field continue to work unchanged (default `user_originated`); unknown enum values return 422.
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Security Core | v0.2.0 | — | Complete | 2026-03-08 |
| 2. LangChain Adapter | v0.2.0 | — | Complete | 2026-03-08 |
| 3. CrewAI + AutoGen Adapters | v0.3 | 3/3 | Complete | 2026-03-23 |
| 4. MCP Server Wrapper | v0.3 | 2/2 | Complete | 2026-03-23 |
| 5. Human-in-the-Loop Gates | v0.3 | 2/2 | Complete | 2026-03-23 |
| 6. Policy-as-Code | v0.3 | 3/3 | Complete | 2026-03-27 |
| 7. Audit CLI + OTel Export | v0.3 | 3/3 | Complete | 2026-03-27 |
| 8. REST API Sidecar | v0.3 | 2/2 | Complete | 2026-03-27 |
| 9. Multi-Agent Enforcement | v0.4 | 3/3 | Complete | 2026-04-09 |
| 10. Anomaly Detection | v0.4 | 2/2 | Complete | 2026-04-11 |
| 11. v0.4 Integration Debt Closure | v0.5 | 3/3 | Complete | 2026-08-22 |
| 12. Provenance-Aware Execution | v0.5 | 7/7 reqs | Complete | 2026-08-22 |

---
*Roadmap last updated: 2026-05-15 — Phase 11 planned (3 plans: 11-01, 11-02, 11-03)*
