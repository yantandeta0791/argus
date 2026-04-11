# Requirements: Argus

**Defined:** 2026-03-15
**Updated:** 2026-04-09
**Core Value:** Every tool call passes through deterministic enforcement code the LLM cannot influence.

## v0.3 Requirements (Complete)

### Framework Adapters

- [x] **ADPT-01**: Developer can wrap CrewAI tools with SecurityGateway using wrap_tools() — full parity with LangChain adapter
- [x] **ADPT-02**: CrewAI adapter enforces permissions, injection scan, secret redaction, egress check, and audit log on every tool call
- [x] **ADPT-03**: Developer can wrap AutoGen tools with SecurityGateway using wrap_tools() — full parity with LangChain adapter
- [x] **ADPT-04**: AutoGen adapter enforces permissions, injection scan, secret redaction, egress check, and audit log on every tool call
- [x] **ADPT-05**: Developer can wrap any MCP server so all tool calls pass through SecurityGateway
- [x] **ADPT-06**: MCP server wrapper enforces the full security stack on every MCP tool invocation
- [x] **ADPT-07**: All three adapters fail-closed — a security violation blocks the tool call, never warns-and-continues

### Human-in-the-Loop Gates

- [x] **HITL-01**: Developer can mark individual tools as require_approval: true in argus.yaml
- [x] **HITL-02**: When a require_approval tool is called, execution pauses and a clear prompt is printed to the terminal
- [x] **HITL-03**: Human can type "approve" or "deny" at the terminal prompt — deny stops the tool call and logs the rejection
- [x] **HITL-04**: Approval decision is written to the audit log with timestamp and tool arguments
- [x] **HITL-05**: Timeout can be configured in argus.yaml — if no response within N seconds, default to deny

### Policy-as-Code

- [x] **POLC-01**: Developer can define RBAC roles and allowed/denied tools entirely in argus.yaml — no Python Casbin config required
- [x] **POLC-02**: Developer can define custom secret detection patterns (regex) in argus.yaml — applied alongside built-in patterns
- [x] **POLC-03**: Developer can define egress allowlist (domains/IPs) in argus.yaml — full declarative config
- [x] **POLC-04**: Developer can define named spend cap profiles (e.g. dev/staging/prod) in argus.yaml and select profile at runtime
- [x] **POLC-05**: argus.yaml validation reports clear errors for misconfigured policy rules on startup

### Operationalization

- [x] **OPS-01**: Developer can run `argus audit` to pretty-print the JSONL audit log with colored output and severity filtering
- [x] **OPS-02**: `argus audit --filter` accepts type, severity, and time range flags to query specific events
- [x] **OPS-03**: Developer can configure OTel exporters in argus.yaml to push security events to external systems (Datadog, Grafana, OTLP endpoint)
- [x] **OPS-04**: Security violations (permission denied, injection detected, credential exposed) emit OTel spans with structured attributes
- [x] **OPS-05**: Developer can start Argus as a REST API sidecar (`argus serve`) that exposes a /tool-call endpoint
- [x] **OPS-06**: The REST sidecar accepts tool call requests, runs the full security stack, and returns allow/block + audit entry — enabling non-Python agents to use Argus

## v0.4 Requirements

### Multi-Agent Enforcement

- [x] **MAGNT-01**: Developer can propagate caller identity (`caller_id` + `hop_depth`) through SecurityGateway on every agent-to-agent tool call
- [x] **MAGNT-02**: Each agent in a multi-agent system has its own declared role and permission scope in argus.yaml
- [x] **MAGNT-03**: Audit log entries include `caller_id` and `hop_depth` for every tool call in a delegation chain
- [x] **MAGNT-04**: OTel violation spans include `argus.security.caller_id` and `argus.security.hop_depth` attributes
- [x] **MAGNT-05**: Developer can set `max_delegation_depth` in argus.yaml — exceeding it raises `DelegationDepthError` (fail-closed)
- [x] **MAGNT-06**: CrewAI and LangChain adapters propagate agent identity via `contextvars` in supervisor/worker patterns
- [x] **MAGNT-07**: HITL banner for sub-agent tool calls shows originating supervisor and hop depth

### Anomaly Detection

- [x] **ANOM-01**: Argus tracks tool call frequency per agent role via sliding window and detects spikes using EWMA baseline + z-score
- [x] **ANOM-02**: Argus tracks egress volume per agent role and detects sudden spikes above the EWMA baseline
- [ ] **ANOM-03**: When an anomaly is detected, Argus escalates to HITL gate with context banner showing rate, baseline, z-score, and last N tool calls
- [ ] **ANOM-04**: Anomaly events are written to audit log and emitted as OTel spans (`GateType.ANOMALY`)
- [x] **ANOM-05**: Developer can configure anomaly thresholds in argus.yaml (`anomaly:` section — `window_seconds`, `z_threshold`, `min_observations`, `enabled`)
- [x] **ANOM-06**: Graduated response levels (configurable `warn_z` / `escalate_z` / `block_z` thresholds) reduce HITL fatigue for moderate anomalies

## Future Requirements (v0.5+)

### LlamaIndex Adapter

- **ADPT-08**: Developer can wrap LlamaIndex tools with SecurityGateway

### Anomaly Detection Extensions

- **ANOM-07**: Tool sequence / Markov anomaly detection for unusual tool combinations
- **ANOM-08**: Anomaly baseline persistence to SQLite across restarts

### Multi-Agent Extensions

- **MAGNT-08**: AutoGen + MCP adapter contextvars propagation

### Webhook Approval

- **HITL-06**: Developer can configure a webhook URL for human-in-the-loop approval — posts tool details, awaits response

## Out of Scope

| Feature | Reason |
|---------|--------|
| GUI dashboard / SaaS | Premature — CLI + REST API is sufficient |
| Model fine-tuning / alignment | Out of domain — Argus is runtime enforcement only |
| Cryptographic delegation tokens (AIP/IBCT) | Requires key infrastructure Argus doesn't have |
| LLM-mediated anomaly classification | Violates core principle: deterministic enforcement only |
| Adaptive baseline that auto-incorporates anomalies | Normalization-of-deviance risk; baseline updates require HITL approval |
| Fleet-level anomaly detection | Requires shared state store (Redis), changes deployment model |
| Token consumption as anomaly metric | Not available in REST sidecar mode; tool frequency + egress are universal |
| Full agent graph topology enforcement | Requires deep framework coupling; role + caller_id enforcement is equivalent |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ADPT-01 | Phase 3 | Complete |
| ADPT-02 | Phase 3 | Complete |
| ADPT-03 | Phase 3 | Complete |
| ADPT-04 | Phase 3 | Complete |
| ADPT-05 | Phase 4 | Complete |
| ADPT-06 | Phase 4 | Complete |
| ADPT-07 | Phase 3 | Complete |
| HITL-01 | Phase 5 | Complete |
| HITL-02 | Phase 5 | Complete |
| HITL-03 | Phase 5 | Complete |
| HITL-04 | Phase 5 | Complete |
| HITL-05 | Phase 5 | Complete |
| POLC-01 | Phase 6 | Complete |
| POLC-02 | Phase 6 | Complete |
| POLC-03 | Phase 6 | Complete |
| POLC-04 | Phase 6 | Complete |
| POLC-05 | Phase 6 | Complete |
| OPS-01 | Phase 7 | Complete |
| OPS-02 | Phase 7 | Complete |
| OPS-03 | Phase 7 | Complete |
| OPS-04 | Phase 7 | Complete |
| OPS-05 | Phase 8 | Complete |
| OPS-06 | Phase 8 | Complete |
| MAGNT-01 | Phase 9 | Complete |
| MAGNT-02 | Phase 9 | Complete |
| MAGNT-03 | Phase 9 | Complete |
| MAGNT-04 | Phase 9 | Complete |
| MAGNT-05 | Phase 9 | Complete |
| MAGNT-06 | Phase 9 | Complete |
| MAGNT-07 | Phase 9 | Complete |
| ANOM-01 | Phase 10 | Complete |
| ANOM-02 | Phase 10 | Complete |
| ANOM-03 | Phase 10 | Pending |
| ANOM-04 | Phase 10 | Pending |
| ANOM-05 | Phase 10 | Complete |
| ANOM-06 | Phase 10 | Complete |

**Coverage:**
- v0.3 requirements: 24 total (24 complete)
- v0.4 requirements: 13 total
- Mapped to phases: 13 (Phase 9: 7, Phase 10: 6) ✓
- Unmapped: 0

---
*Requirements defined: 2026-03-15*
*Last updated: 2026-04-08 after v0.4 roadmap creation*
