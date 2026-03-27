# Roadmap: Argus v0.3.0

**Milestone:** v0.3.0 — Framework Adapters, HITL Gates, Policy-as-Code, Operationalization
**Granularity:** Standard
**Coverage:** 24/24 requirements mapped

---

## Phases

- [x] **Phase 3: CrewAI + AutoGen Adapters** — Extend SecurityGateway to CrewAI and AutoGen with full enforcement parity and fail-closed guarantees (completed 2026-03-23)
- [x] **Phase 4: MCP Server Wrapper** — Wrap any MCP server so all tool invocations pass through the security stack (completed 2026-03-23)
- [x] **Phase 5: Human-in-the-Loop Gates** — Terminal approval flow for high-risk tools, audit-logged decisions, configurable timeout (completed 2026-03-23)
- [x] **Phase 6: Policy-as-Code** — Full declarative argus.yaml configuration for RBAC, secrets, egress, spend caps, and startup validation (completed 2026-03-27)
- [ ] **Phase 7: Audit CLI + OTel Export** — `argus audit` command with filtering and push export of security events to Datadog/Grafana/OTLP
- [ ] **Phase 8: REST API Sidecar** — `argus serve` exposes a /tool-call endpoint enabling non-Python agents to use Argus

---

## Phase Details

### Phase 3: CrewAI + AutoGen Adapters
**Goal:** Developers using CrewAI or AutoGen can wrap their tools with SecurityGateway using the same wrap_tools() interface as the LangChain adapter, with every security enforcement path active and fail-closed.
**Depends on:** Phase 2 (LangChain adapter pattern established)
**Requirements:** ADPT-01, ADPT-02, ADPT-03, ADPT-04, ADPT-07
**Success Criteria** (what must be TRUE):
  1. A developer can call wrap_tools() on a list of CrewAI tools and get back security-wrapped equivalents with no changes to their CrewAI agent setup
  2. A developer can call wrap_tools() on a list of AutoGen tools and get back security-wrapped equivalents with no changes to their AutoGen agent setup
  3. A permission violation on a CrewAI or AutoGen tool call results in a blocked execution, not a warning — the agent never receives a response
  4. Prompt injection, secret redaction, and egress checks all fire on CrewAI and AutoGen tool calls identically to how they fire on LangChain tool calls
  5. Both adapters have test coverage demonstrating fail-closed behavior under injection, permission denied, and egress violation conditions
**Plans:** 3/3 plans complete

Plans:
- [ ] 03-01-PLAN.md — TDD test scaffolds: failing RED test suites for CrewAI and AutoGen adapters
- [ ] 03-02-PLAN.md — CrewAI adapter: implement argus/adapters/crewai.py, turn test_crewai.py GREEN
- [ ] 03-03-PLAN.md — AutoGen adapter: implement argus/adapters/autogen.py, turn test_autogen.py GREEN

### Phase 4: MCP Server Wrapper
**Goal:** Developers can place Argus in front of any MCP server so that every tool call flowing through MCP is subject to the full security stack, with fail-closed enforcement.
**Depends on:** Phase 3
**Requirements:** ADPT-05, ADPT-06
**Success Criteria** (what must be TRUE):
  1. A developer can pass an MCP server reference to a wrap_mcp_server() function and receive a security-wrapped MCP server that the rest of their code uses transparently
  2. Every tool invocation routed through the wrapped MCP server is subject to permission enforcement, injection scanning, secret redaction, egress check, and audit logging
  3. A security violation on an MCP tool call blocks the invocation and records it in the audit log — the MCP server never executes the blocked tool
**Plans:** 2/2 plans complete

Plans:
- [ ] 04-01-PLAN.md — TDD RED: write failing test suite for MCP adapter (stub fastmcp/mcp modules)
- [ ] 04-02-PLAN.md — Implement argus/adapters/mcp.py + add fastmcp optional dep, turn tests GREEN

### Phase 5: Human-in-the-Loop Gates
**Goal:** Developers can designate individual tools as requiring human approval before execution; when those tools are called, the agent pauses and waits for a terminal approve/deny decision that is recorded in the audit log.
**Depends on:** Phase 3
**Requirements:** HITL-01, HITL-02, HITL-03, HITL-04, HITL-05
**Success Criteria** (what must be TRUE):
  1. A developer can add require_approval: true to a tool entry in argus.yaml and that tool will never execute without explicit human confirmation
  2. When a require_approval tool is triggered, the terminal prints a clear prompt showing the tool name and its arguments, and execution is fully paused until input arrives
  3. Typing "approve" resumes the tool call; typing "deny" stops it and logs the rejection with tool arguments and timestamp in the audit log
  4. If no response is received within the configured timeout period, the tool call is automatically denied and logged — no silent hang
**Plans:** 2/2 plans complete

Plans:
- [ ] 05-01-PLAN.md — TDD RED: write failing test suite for HITLGate, gateway sequencing, and adapter propagation
- [ ] 05-02-PLAN.md — Implement argus/security/hitl.py + ApprovalDeniedError + gateway gate 1.5 + adapter wiring, turn tests GREEN

### Phase 6: Policy-as-Code
**Goal:** Developers can configure all of Argus's enforcement rules — RBAC roles, secret patterns, egress allowlists, and spend cap profiles — entirely in argus.yaml, with no Python Casbin configuration required, and receive clear validation errors at startup for any misconfigured rules.
**Depends on:** Phase 5
**Requirements:** POLC-01, POLC-02, POLC-03, POLC-04, POLC-05
**Success Criteria** (what must be TRUE):
  1. A developer can define roles, tool permissions, and deny rules entirely in argus.yaml and have them enforced at runtime with no Casbin Python code
  2. A developer can add custom regex patterns under a secrets section in argus.yaml and have those patterns applied to every tool input and output alongside built-in patterns
  3. A developer can specify allowed domains and IPs under an egress section in argus.yaml and have those rules enforced without any code changes
  4. A developer can define named spend cap profiles (e.g. dev/staging/prod) and select the active profile via an environment variable or CLI flag at startup
  5. When argus.yaml contains invalid policy rules, startup fails with a specific, human-readable error message identifying the offending rule — no silent misconfiguration
**Plans:** 3/3 plans complete

Plans:
- [ ] 06-01-PLAN.md — TDD RED: write failing test suites for all POLC-01 through POLC-05 behaviors
- [ ] 06-02-PLAN.md — ConfigValidationError, PermissionEnforcer wildcard/deny fix, and four section loaders; turn unit tests GREEN
- [ ] 06-03-PLAN.md — load_gateway_config orchestrator; turn integration tests GREEN; full suite gate

### Phase 7: Audit CLI + OTel Export
**Goal:** Developers can inspect the audit log from the terminal using `argus audit` with filtering options, and can push security events to external observability systems via OTel exporters configured in argus.yaml.
**Depends on:** Phase 6
**Requirements:** OPS-01, OPS-02, OPS-03, OPS-04
**Success Criteria** (what must be TRUE):
  1. Running `argus audit` prints the JSONL audit log to the terminal with colored output, severity indicators, and human-readable timestamps
  2. Running `argus audit --filter` with type, severity, or time range flags returns only the matching events — all other events are hidden
  3. A developer can configure an OTel exporter endpoint (Datadog, Grafana, or OTLP) in argus.yaml and have security events pushed to that endpoint without code changes
  4. Permission denied, injection detected, and credential exposed events each emit an OTel span with structured attributes (event type, tool name, severity, agent role)
**Plans:** 3 plans

Plans:
- [ ] 07-01-PLAN.md — TDD RED: write failing test suites for all OPS-01 through OPS-04 behaviors
- [ ] 07-02-PLAN.md — Implement argus audit CLI command with streaming reader, Rich panels, and filter flags (OPS-01, OPS-02)
- [ ] 07-03-PLAN.md — OtelConfig + load_otel_config + emit_security_violation + SecurityGateway violation span wiring (OPS-03, OPS-04)

### Phase 8: REST API Sidecar
**Goal:** Non-Python agents can use Argus by sending tool call requests to a local REST sidecar started with `argus serve`, which runs the full security stack and returns an allow/block decision with an audit entry.
**Depends on:** Phase 7
**Requirements:** OPS-05, OPS-06
**Success Criteria** (what must be TRUE):
  1. Running `argus serve` starts a local HTTP server and prints the address — the process stays alive until interrupted
  2. A POST to /tool-call with a JSON body containing tool name and arguments returns a JSON response with an allow/block decision and the corresponding audit entry
  3. A blocked tool call from the REST sidecar produces an audit log entry identical in structure to one blocked by the Python adapter — there is no second-class path through the REST interface
**Plans:** TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 3. CrewAI + AutoGen Adapters | 3/3 | Complete    | 2026-03-23 |
| 4. MCP Server Wrapper | 2/2 | Complete   | 2026-03-23 |
| 5. Human-in-the-Loop Gates | 2/2 | Complete   | 2026-03-23 |
| 6. Policy-as-Code | 3/3 | Complete   | 2026-03-27 |
| 7. Audit CLI + OTel Export | 0/3 | In progress | - |
| 8. REST API Sidecar | 0/? | Not started | - |

---
*Roadmap created: 2026-03-15*
*Milestone: v0.3.0*
