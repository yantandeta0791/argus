---
gsd_state_version: 1.0
milestone: v0.3
milestone_name: milestone
status: executing
stopped_at: Completed 04-01-PLAN.md — MCP adapter RED test suite
last_updated: "2026-03-23T00:34:20.878Z"
last_activity: 2026-03-23 — 03-03 AutoGen adapter implementation (wrap_tools with FunctionTool closure pattern)
progress:
  total_phases: 6
  completed_phases: 1
  total_plans: 5
  completed_plans: 4
  percent: 100
---

# State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-15)

**Core value:** Every tool call passes through deterministic enforcement code the LLM cannot influence.
**Current focus:** v0.3.0 — Phase 4: MCP Server Wrapper

## Current Position

Phase: 4 (MCP Server Wrapper)
Plan: 01 complete — 04-01 RED test suite done
Status: In progress
Last activity: 2026-03-23 — 04-01 MCP adapter RED test suite (stub fastmcp/mcp modules, gateway contract tests)

Progress: [████████░░] 80%

## Performance Metrics

- Phases complete: 1/6
- Plans complete: 4 (03-01, 03-02, 03-03, 04-01)
- Requirements shipped: 8/24 (ADPT-01, ADPT-02, ADPT-03, ADPT-04, ADPT-05, ADPT-06, ADPT-07, ADPT-08)

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

## Session Continuity

Next action: Execute plan 04-02 (MCP adapter implementation — GREEN step)
Stopped at: Completed 04-01-PLAN.md — MCP adapter RED test suite
Roadmap: .planning/ROADMAP.md
Requirements: .planning/REQUIREMENTS.md

---
*State initialized: 2026-03-15*
*Milestone: v0.3.0*
