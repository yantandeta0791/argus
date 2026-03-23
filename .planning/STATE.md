---
gsd_state_version: 1.0
milestone: v0.3
milestone_name: milestone
status: executing
stopped_at: Completed 05-02-PLAN.md
last_updated: "2026-03-23T20:35:16.294Z"
last_activity: 2026-03-23 — 05-01 HITL RED test suite (HITLGate, load_hitl_config, gateway sequencing, adapter propagation)
progress:
  total_phases: 6
  completed_phases: 3
  total_plans: 7
  completed_plans: 7
  percent: 86
---

# State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-15)

**Core value:** Every tool call passes through deterministic enforcement code the LLM cannot influence.
**Current focus:** v0.3.0 — Phase 5: Human-in-the-Loop Gates

## Current Position

Phase: 5 (Human-in-the-Loop Gates)
Plan: 02 complete — HITL gate implementation (HITLGate, ApprovalDeniedError, gateway Gate 1.5)
Status: Phase 5 complete
Last activity: 2026-03-23 — 05-02 HITL gate implementation (HITLGate, HITLConfig, ApprovalDeniedError, load_hitl_config, gateway Gate 1.5)

Progress: [██████████] 100%

## Performance Metrics

- Phases complete: 3/6
- Plans complete: 7 (03-01, 03-02, 03-03, 04-01, 04-02, 05-01, 05-02)
- Requirements shipped: 15/24 (ADPT-01 through ADPT-08 shipped in phase 3-4; HITL-01 through HITL-05 shipped in 05-02)

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

## Session Continuity

Next action: Execute Phase 6 (policy-as-code) — Phase 5 complete
Stopped at: Completed 05-02-PLAN.md
Roadmap: .planning/ROADMAP.md
Requirements: .planning/REQUIREMENTS.md

---
*State initialized: 2026-03-15*
*Milestone: v0.3.0*
