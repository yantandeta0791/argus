# Roadmap: Argus

## Milestones

- ✅ **v0.2.0 Security Foundation + LangChain** — Phases 1–2 (shipped 2026-03-08)
- ✅ **v0.3 Framework Adapters + Operationalization** — Phases 3–8 (shipped 2026-03-28)
- 📋 **v0.4 Multi-Agent + Anomaly Detection** — Phases 9–10 (planned)

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

### 📋 v0.4 Multi-Agent + Anomaly Detection (Planned)

- [ ] **Phase 9: Multi-Agent Enforcement** - Identity propagation, per-agent RBAC, delegation depth limits, A2A audit attribution, adapter context vars
- [x] **Phase 10: Anomaly Detection** - Per-agent EWMA frequency + egress spike detection, HITL escalation, audit/OTel, graduated response levels (completed 2026-04-11)

## Phase Details

### Phase 9: Multi-Agent Enforcement
**Goal**: Every agent-to-agent tool call passes through SecurityGateway with the calling agent's identity verified, hop depth enforced, and full audit attribution — so delegation chains are fully visible and privilege escalation across agents is impossible.
**Depends on**: Phase 8 (complete SecurityGateway + REST sidecar)
**Requirements**: MAGNT-01, MAGNT-02, MAGNT-03, MAGNT-04, MAGNT-05, MAGNT-06, MAGNT-07
**Success Criteria** (what must be TRUE):
  1. Developer can pass `caller_id` and `hop_depth` to `SecurityGateway.pre_tool_call()` and every audit log entry for that call includes both fields
  2. When `max_delegation_depth` is exceeded in a supervisor→worker chain, the tool call is blocked with `DelegationDepthError` — not warned-and-continued
  3. Each agent declared in `agents:` in argus.yaml gets its own role and permission scope; a worker agent calling a tool allowed only for supervisors is denied
  4. A supervisor→worker tool call made via the CrewAI or LangChain adapter propagates agent identity automatically via `contextvars` without the developer manually threading `caller_id`
  5. The HITL terminal banner for a sub-agent tool call shows the originating supervisor name and current hop depth alongside the tool arguments
**Plans:** 3 plans

Plans:
- [ ] 09-01-PLAN.md — Identity infrastructure: ContextVars, AgentRegistry, DelegationDepthError, config parser
- [ ] 09-02-PLAN.md — Gate 0.5 in SecurityGateway, OTel identity attributes, HITL sub-agent banner
- [ ] 09-03-PLAN.md — LangChain/CrewAI ContextVar propagation, REST sidecar identity fields

### Phase 10: Anomaly Detection
**Goal**: Argus detects when an agent's tool call rate or egress volume spikes above its established baseline, escalates to a HITL gate with structured context, and records every anomaly decision in the audit log and OTel — so operators can catch runaway or compromised agents before damage is done.
**Depends on**: Phase 9 (agent identity infrastructure required for per-agent window attribution)
**Requirements**: ANOM-01, ANOM-02, ANOM-03, ANOM-04, ANOM-05, ANOM-06
**Success Criteria** (what must be TRUE):
  1. After a warmup period, an agent making tool calls at 3x its established frequency triggers a HITL prompt with a banner showing call rate, EWMA baseline, z-score, and last N calls
  2. An agent generating egress volume above its EWMA baseline by the configured z-threshold triggers a HITL prompt with the spike context
  3. Anomaly events appear in `argus audit` output and in OTel spans with `GateType.ANOMALY` — the same observability path as permission violations
  4. Developer can set `window_seconds`, `z_threshold`, `min_observations`, and `enabled` in an `anomaly:` block in argus.yaml and the detector respects these values at runtime
  5. Graduated response levels (`warn_z`, `escalate_z`, `block_z`) allow low-confidence anomalies to log-only while high-confidence anomalies escalate to HITL — reducing false-positive alert fatigue
**Plans:** 2/2 plans complete

Plans:
- [ ] 10-01-PLAN.md — AnomalyDetector engine, AnomalyConfig, config loading, GateType.ANOMALY, AnomalyBlockedError
- [ ] 10-02-PLAN.md — Gate 1.75 + Gate 5.5 in SecurityGateway, HITL escalation merge, audit/OTel integration

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
| 9. Multi-Agent Enforcement | v0.4 | 3/3 | Complete | — |
| 10. Anomaly Detection | 2/2 | Complete    | 2026-04-11 | — |

---
*Roadmap last updated: 2026-04-10 after Phase 10 planning*
