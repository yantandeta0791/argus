---
gsd_state_version: 1.0
milestone: v0.3
milestone_name: milestone
status: completed
stopped_at: Completed 08-02-PLAN.md
last_updated: "2026-03-27T20:47:37.868Z"
last_activity: 2026-03-27 — 07-03 OtelConfig, load_otel_config, emit_security_violation, SecurityGateway OTel wiring
progress:
  total_phases: 6
  completed_phases: 6
  total_plans: 15
  completed_plans: 15
  percent: 100
---

# State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-15)

**Core value:** Every tool call passes through deterministic enforcement code the LLM cannot influence.
**Current focus:** v0.3.0 — Phase 6: Policy-as-Code (complete)

## Current Position

Phase: 8 (REST API Sidecar) — COMPLETE
Plan: 02 complete — Full REST sidecar, /tool-call endpoint, HITL guard, argus serve CLI (OPS-05, OPS-06 GREEN)
Status: Phase 8 fully complete — all 15 plans complete, all requirements shipped
Last activity: 2026-03-27 — 08-02 FastAPI sidecar, build_app() testable seam, serve_command, 10 tests GREEN

Progress: [██████████] 100%

## Performance Metrics

- Phases complete: 7/7 (all phases 1-7 complete)
- Plans complete: 13 (03-01, 03-02, 03-03, 04-01, 04-02, 05-01, 05-02, 06-01, 06-02, 06-03, 07-01, 07-02, 07-03)
- Requirements shipped: 24/24 (OPS-03 and OPS-04 shipped in 07-03 — all requirements complete)

## Accumulated Context

- v0.1.0 + v0.2.0 shipped successfully (phases 1–2)
- LangChain adapter (proxy pattern, fail-closed) is the established pattern for all new adapters
- CrewAI and AutoGen are the highest-demand framework targets
- MCP server wrapper follows adapter pattern — treat MCP server as a tool host
- HITL gates operate at the argus.yaml + terminal level — no GUI, no webhook in v0.3.0
- Policy-as-code goal: zero Python Casbin config required for standard RBAC setups
- `argus audit` must be fast on large JSONL files — streaming read, not load-all
- REST sidecar enables non-Python agents (JS, Go, etc.) to use Argus without binding

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Phase 3 before Phase 4 | CrewAI/AutoGen adapters establish adapter pattern; MCP wrapper can reuse it |
| Phase 5 after Phase 3 | HITL gates need at least one adapter working to be testable end-to-end |
| Phase 6 after Phase 5 | Policy-as-code subsumes HITL config — better to have HITL working first |
| Phase 7 after Phase 6 | OTel export config lives in argus.yaml — POLC must land first |
| Phase 8 last | REST sidecar wraps the full stack — needs everything else stable |
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

## Session Continuity

Next action: Execute Phase 7 Plan 03 — OTel config loading, violation spans, gateway wiring (OPS-03, OPS-04 GREEN)
Stopped at: Completed 08-02-PLAN.md
Roadmap: .planning/ROADMAP.md
Requirements: .planning/REQUIREMENTS.md

---
*State initialized: 2026-03-15*
*Milestone: v0.3.0*
