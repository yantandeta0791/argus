# Requirements: Argus

**Defined:** 2026-03-15
**Core Value:** Every tool call passes through deterministic enforcement code the LLM cannot influence.

## v0.3.0 Requirements

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

- [ ] **POLC-01**: Developer can define RBAC roles and allowed/denied tools entirely in argus.yaml — no Python Casbin config required
- [ ] **POLC-02**: Developer can define custom secret detection patterns (regex) in argus.yaml — applied alongside built-in patterns
- [ ] **POLC-03**: Developer can define egress allowlist (domains/IPs) in argus.yaml — full declarative config
- [ ] **POLC-04**: Developer can define named spend cap profiles (e.g. dev/staging/prod) in argus.yaml and select profile at runtime
- [ ] **POLC-05**: argus.yaml validation reports clear errors for misconfigured policy rules on startup

### Operationalization

- [ ] **OPS-01**: Developer can run `argus audit` to pretty-print the JSONL audit log with colored output and severity filtering
- [ ] **OPS-02**: `argus audit --filter` accepts type, severity, and time range flags to query specific events
- [ ] **OPS-03**: Developer can configure OTel exporters in argus.yaml to push security events to external systems (Datadog, Grafana, OTLP endpoint)
- [ ] **OPS-04**: Security violations (permission denied, injection detected, credential exposed) emit OTel spans with structured attributes
- [ ] **OPS-05**: Developer can start Argus as a REST API sidecar (`argus serve`) that exposes a /tool-call endpoint
- [ ] **OPS-06**: The REST sidecar accepts tool call requests, runs the full security stack, and returns allow/block + audit entry — enabling non-Python agents to use Argus

## Future Requirements

### Multi-Agent Enforcement

- **MAGNT-01**: Agent-to-agent calls are enforced by SecurityGateway the same as tool calls
- **MAGNT-02**: Each agent in a multi-agent system has its own declared role and permission scope
- **MAGNT-03**: Cross-agent permission escalation attempts are blocked and logged

### Anomaly Detection

- **ANOM-01**: Argus detects and flags unusual tool call frequency patterns (e.g. 50 calls in 10 seconds)
- **ANOM-02**: Argus detects and flags sudden egress spikes across sessions
- **ANOM-03**: Anomaly thresholds are configurable in argus.yaml

### LlamaIndex Adapter

- **ADPT-08**: Developer can wrap LlamaIndex tools with SecurityGateway

### Webhook Approval

- **HITL-06**: Developer can configure a webhook URL for human-in-the-loop approval — posts tool details, awaits response

## Out of Scope

| Feature | Reason |
|---------|--------|
| GUI dashboard / SaaS | Premature — CLI + REST API is sufficient for v0.3.0 |
| Model fine-tuning / alignment | Out of domain — Argus is runtime enforcement only |
| Risk-score auto-detection for HITL | Deferred — config-based is simpler and more predictable for v0.3.0 |
| LlamaIndex adapter | Deferred to v0.4.0 — lower risk profile than autonomous agent frameworks |
| Multi-agent enforcement | Deferred to v0.4.0 — requires deeper architecture work |

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
| POLC-01 | Phase 6 | Pending |
| POLC-02 | Phase 6 | Pending |
| POLC-03 | Phase 6 | Pending |
| POLC-04 | Phase 6 | Pending |
| POLC-05 | Phase 6 | Pending |
| OPS-01 | Phase 7 | Pending |
| OPS-02 | Phase 7 | Pending |
| OPS-03 | Phase 7 | Pending |
| OPS-04 | Phase 7 | Pending |
| OPS-05 | Phase 8 | Pending |
| OPS-06 | Phase 8 | Pending |

**Coverage:**
- v0.3.0 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-15*
*Last updated: 2026-03-15 — traceability finalized after roadmap creation*
