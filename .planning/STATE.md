---
gsd_state_version: 1.0
milestone: v0.4
milestone_name: Multi-Agent + Anomaly Detection
status: completed
stopped_at: Completed 10-02-PLAN.md
last_updated: "2026-04-11T00:36:47.031Z"
last_activity: 2026-04-09 — Phase 09 Plan 03 (adapter identity propagation + REST sidecar) complete
progress:
  total_phases: 2
  completed_phases: 2
  total_plans: 5
  completed_plans: 5
  percent: 100
---

# State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-08)

**Core value:** Every tool call passes through deterministic enforcement code the LLM cannot influence.
**Current focus:** v0.4 Multi-Agent + Anomaly Detection — roadmap ready, phase planning next

## Current Position

Phase: 10-anomaly-detection
Plan: 2/2 complete
Status: Complete — Phase 10 all plans done
Last activity: 2026-04-09 — Phase 09 Plan 03 (adapter identity propagation + REST sidecar) complete

Progress: [██████████] 100%

## Performance Metrics

- Phases complete (v0.4): 0/2
- Plans complete (v0.4): 0 (TBD during phase planning)
- Requirements mapped: 13/13
- v0.3 requirements shipped: 24/24 (all complete)

## Accumulated Context

- v0.1.0 + v0.2.0 shipped successfully (phases 1–2)
- LangChain adapter (proxy pattern, fail-closed) is the established pattern for all new adapters
- CrewAI and AutoGen are the highest-demand framework targets
- MCP server wrapper follows adapter pattern — treat MCP server as a tool host
- HITL gates operate at the argus.yaml + terminal level — no GUI, no webhook in v0.3.0
- Policy-as-code goal: zero Python Casbin config required for standard RBAC setups
- `argus audit` must be fast on large JSONL files — streaming read, not load-all
- REST sidecar enables non-Python agents (JS, Go, etc.) to use Argus without binding
- v0.4: Zero new core dependencies — contextvars (stdlib), deque+statistics (stdlib), OTel baggage (already in dep tree)
- v0.4: LangGraph is the only new optional extra (`argus[langgraph]`) using `ToolNode(wrap_tool_call=...)`
- v0.4: `agent_role` must be bound at `wrap_tools()` construction time, not passed dynamically — prevents privilege escalation via REST sidecar
- v0.4: Anomaly detector cold-start: warmup_calls / min_observations (default 10) must suppress escalation before baseline is established
- v0.4: REST sidecar single-worker enforcement required when anomaly detection enabled (multi-worker splits state)
- v0.4: Gate order — Gate 0.5 (Identity) → Gate 1 (Permission) → Gate 1.5 (HITL) → Gate 1.75 (Anomaly) → Gate 2 (Audit pre) → [execute] → Gate 3 (Injection) → Gate 4 (Redaction) → Gate 5.5 (Egress record) → Gate 5 (Egress) → Gate 6 (Audit post)
- v0.4: Phase 9 strictly before Phase 10 — AnomalyDetector uses `agent_id` from identity registry built in Phase 9

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Phase 3 before Phase 4 | CrewAI/AutoGen adapters establish adapter pattern; MCP wrapper can reuse it |
| Phase 5 after Phase 3 | HITL gates need at least one adapter working to be testable end-to-end |
| Phase 6 after Phase 5 | Policy-as-code subsumes HITL config — better to have HITL working first |
| Phase 7 after Phase 6 | OTel export config lives in argus.yaml — POLC must land first |
| Phase 8 last | REST sidecar wraps the full stack — needs everything else stable |
| Phase 9 before Phase 10 | AnomalyDetector uses agent_id for per-agent window attribution — requires identity infrastructure from Phase 9; Gate 1.75 follows Gate 0.5 in the same call |
| CrewAI tests use .run() not .invoke() | CrewAI BaseTool API differs from LangChain — different method name |
| AutoGen tests patch sys.modules with stub FunctionTool | Avoids autogen_core install; stub exposes inner async func for gateway gate testing |
| CrewAI adapter intercepts run() not _run() | public boundary prevents framework bypass; _run() would be called directly by framework |
| No crewai top-level import in adapter | duck typing with Any keeps crewai optional, not required — import only needed at runtime |
| AutoGen plain callable detection uses iscoroutinefunction(tool) | hasattr(tool, 'run_json') is unreliable — MagicMock auto-creates any attribute; iscoroutinefunction is False for BaseTool instances, True for async callables |
| MCP tests use top-level import of argus.adapters.mcp | Ensures RED failure at pytest collection time, not inside test body |
| MCP ToolError stubbed as plain Exception | Tests work without fastmcp installed; real adapter raises ToolError (subclass of Exception) |
| ArgusMCPMiddleware uses plain class (no Middleware inheritance) — FastMCP duck-types on on_call_tool | Avoids module-level fastmcp import; module importable without optional package installed |
| fastmcp listed as optional extra (pip install argus[mcp]) | Importing argus.adapters.mcp without fastmcp installed raises no ImportError |
| HITLGate._read_with_timeout patched via patch.object for timeout test | Allows None sentinel independent of retry logic — cleaner than patching builtins.input |
| Gateway HITL tests mock argus.security.gateway.HITLGate class not instance | Plan 02 instantiates HITLGate internally from config.hitl; tests verify construction and check() delegation |
| MCP HITL test asserts ToolError (Exception stub), not raw ApprovalDeniedError | Matches existing MCP error conversion pattern — ApprovalDeniedError is ArgusSecurityError subclass |
| Lazy HITLGate instantiation per pre_tool_call call (not __init__) | Module-level HITLGate name must stay patchable; stored instance escapes patch scope in tests |
| HITL deny path re-raises without audit.send | Denied calls must not produce tool_call_pre audit entries; hitl_decision only logged on approve |
| 06-01 RED test imports inside function bodies | Ensures ImportError at call time not collection time — matches existing test_config.py style |
| ARGUS_SPEND_PROFILE env var for spend profiles | Consistent with Argus env var naming convention (ARGUS_ prefix) |
| load_gateway_config does not call load_spend_profiles | SpendConfig is a ModelConfig field, not a GatewayConfig field — spend config is separate concern |
| GatewayConfig lazily imported inside load_gateway_config | Avoids circular imports between argus.llm and argus.security — same lazy import pattern as other section loaders |
| Module-level import in test_audit.py (not function-body) | Forces collection-time RED for CLI tests — consistent with MCP test pattern; more immediate failure signal |
| test_load_gateway_config_with_otel_builds_emitter is RED for three reasons | GatewayConfig.otel, build_security_otel_emitter, SecurityGateway.security_otel — all three must land in Plan 03 |
| --since/--until accept relative duration strings only (30m, 1h, 2d) | No ISO-8601 per user decision; consistent with argus duration format convention |
| prev_hash and event_id never rendered in audit panels | Chain integrity fields for internal use only — not exposed to CLI users |
| Datadog/Grafana treated as OTLP aliases — single OTLPSpanExporter for all backends | Per user decision; simplifies implementation, no special-casing needed |
| SecurityGateway security_otel is constructor-injected, not built internally | Separation of concerns; caller controls emitter lifecycle |
| Egress gate does not emit violation spans in v1 | Egress is log-only (not a blocked outcome) — span emission only for blocked/denied calls |
| Phase 08 P01 | 3 | 2 tasks | 4 files |
| Phase 08-rest-api-sidecar P02 | 15 | 2 tasks | 2 files |
| isinstance(hitl_config, HITLConfig) guard in /tool-call | MagicMock auto-creates _hitl_config as truthy mock; isinstance prevents false HITL 503 for non-HITL gateways in tests |
| Pydantic models at module level not inside build_app | FastAPI annotation resolver fails for locally-scoped Pydantic models; all requests returned 422 until moved to module scope |
| Phase 09 P01 | 175 | 2 tasks | 7 files |
| AgentRegistry uses permissive fallback | Unknown caller_id returns adapter-supplied role — prevents single-agent breakage when no agents: section configured |
| GatewayConfig.agents lazily typed as Optional[Any] | Same pattern as otel field — avoids circular import between argus.llm and argus.security |
| SecurityEvent caller_id/hop_depth default to None/0 | All existing SecurityEvent construction remains backward compatible |
| Phase 09-multi-agent-enforcement P02 | 7 | 1 tasks | 6 files |
| pre_tool_call uses keyword-only params (* separator) — hop_depth=None sentinel for ContextVar fallback | Prevents positional call breakage; None vs 0 distinction allows correct fallback to ContextVar when caller does not pass hop_depth |
| severity_map extended with identity:HIGH; _emit_violation carries caller_id/hop_depth through all gates | DelegationDepthError treated equally to permission denial; all violation spans carry full identity context |
| Lazy import of set_caller_context inside invoke()/run() | Avoids import-time dependency on identity module; keeps adapters importable without identity module loaded |
| tokens=None sentinel pattern in adapters | Only reset_caller_context when set was called — prevents errors on non-identity code paths; caller_id=None skips ContextVar entirely |
| Phase 09 P03 | 3 | 2 tasks | 6 files |
| Phase 10-anomaly-detection P01 | 5 | 1 tasks | 7 files |
| z-score uses pre-update EWMA and prior window (10-01) | Prevents spike from inflating its own denominator — ensures 100x spike against stable baseline returns BLOCK not WARN |
| stdev=0 with deviation → BLOCK (10-01) | Perfectly stable baseline means any deviation is maximally anomalous; stdev=0 with value==baseline → OK edge case preserved |
| AnomalyDetector NOT thread-safe (10-01) | Per-agent state is in-process dict; single-worker enforcement required when anomaly gate enabled (REST sidecar constraint) |
| Phase 10-anomaly-detection P02 | 274 | 2 tasks | 4 files |
| Gate 1.75 pre-computes anomaly before Gate 1.5 HITL (10-02) | Single merged HITL prompt when both require_approval and escalate_z fire — avoids two separate prompts for same call |
| Gate 5.5 uses output replacement not exception on egress BLOCK (10-02) | post_tool_call contract always returns str; BLOCK replaces output with placeholder without raising |
| HITLGate anomaly-only escalation: gate fires when anomaly_context present even if needs_approval is False (10-02) | Anomaly escalation must reach human even for tools not in require_approval list |
| hitl_decision audit event only logged when needs_hitl True (10-02) | Anomaly-only HITL paths do not produce spurious hitl_decision entries |

## Session Continuity

Next action: Phase 10 complete — v0.4 anomaly detection enforcement done
Stopped at: Completed 10-02-PLAN.md
Roadmap: .planning/ROADMAP.md
Requirements: .planning/REQUIREMENTS.md

---
*State initialized: 2026-03-15*
*Milestone: v0.4*
*Last updated: 2026-04-08 after v0.4 roadmap creation*
