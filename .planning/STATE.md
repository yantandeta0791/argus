---
gsd_state_version: 1.0
milestone: v0.3
milestone_name: milestone
status: completed
stopped_at: Completed 05-01-PLAN.md
last_updated: "2026-03-23T20:28:21.914Z"
last_activity: 2026-03-23 — 04-02 MCP adapter implementation (ArgusMCPMiddleware, wrap_mcp_server, fastmcp optional dep)
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 7
  completed_plans: 6
  percent: 100
---

# State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-15)

**Core value:** Every tool call passes through deterministic enforcement code the LLM cannot influence.
**Current focus:** v0.3.0 — Phase 5: Human-in-the-Loop Gates

## Current Position

Phase: 5 (Human-in-the-Loop Gates)
Plan: 01 complete — 05-01 HITL RED test suite written
Status: Phase 5 in progress
Last activity: 2026-03-23 — 05-01 HITL RED test suite (HITLGate, load_hitl_config, gateway sequencing, adapter propagation)

Progress: [█████████░] 86%

## Performance Metrics

- Phases complete: 2/6
- Plans complete: 6 (03-01, 03-02, 03-03, 04-01, 04-02, 05-01)
- Requirements shipped: 10/24 (ADPT-01 through ADPT-08 + ADPT-05, ADPT-06 confirmed shipped in 04-02; HITL-01 through HITL-05 RED tests written in 05-01)

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

## Session Continuity

Next action: Execute Phase 5 (HITL gates) — Phase 4 complete
Stopped at: Completed 05-01-PLAN.md
Roadmap: .planning/ROADMAP.md
Requirements: .planning/REQUIREMENTS.md

---
*State initialized: 2026-03-15*
*Milestone: v0.3.0*
