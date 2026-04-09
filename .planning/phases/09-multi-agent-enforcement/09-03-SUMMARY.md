---
phase: 09-multi-agent-enforcement
plan: 03
subsystem: adapters, rest-sidecar
tags: [multi-agent, contextvars, identity-propagation, langchain, crewai, rest]
dependency_graph:
  requires: ["09-02"]
  provides: ["ContextVar propagation in LangChain adapter", "ContextVar propagation in CrewAI adapter", "REST caller identity fields"]
  affects: ["argus/adapters/langchain.py", "argus/adapters/crewai.py", "argus/cli/serve.py"]
tech_stack:
  added: []
  patterns: ["ContextVar token-based reset in finally block", "lazy import at call boundary"]
key_files:
  created: []
  modified:
    - argus/adapters/langchain.py
    - argus/adapters/crewai.py
    - argus/cli/serve.py
    - tests/adapters/test_langchain.py
    - tests/adapters/test_crewai.py
    - tests/cli/test_serve.py
decisions:
  - "Lazy import of set_caller_context/reset_caller_context inside invoke()/run() avoids import-time dependency on identity module"
  - "tokens = None sentinel pattern: only call reset when set was actually called — prevents AttributeError on non-identity code paths"
  - "finally block wraps entire pre/execute/post sequence — even exceptions during pre_tool_call trigger reset"
metrics:
  duration: "~3 minutes"
  completed_date: "2026-04-09"
  tasks: 2
  files_modified: 6
---

# Phase 09 Plan 03: Multi-Agent Adapter Identity Propagation Summary

**One-liner:** ContextVar identity propagation (caller_id/hop_depth) wired into LangChain and CrewAI adapters via token-based finally reset, plus REST sidecar accepting identity fields forwarded to gateway.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add ContextVar propagation to LangChain and CrewAI adapters | bc62289 | argus/adapters/langchain.py, argus/adapters/crewai.py, tests/adapters/test_langchain.py, tests/adapters/test_crewai.py |
| 2 | Extend REST sidecar with caller_id and hop_depth | 5bea134 | argus/cli/serve.py, tests/cli/test_serve.py |

## What Was Built

### Task 1: ContextVar Propagation in Adapters

Both `ArgusToolWrapper` (LangChain) and `ArgusCrewAIToolWrapper` (CrewAI) now accept `caller_id: str | None = None` and `hop_depth: int = 0` params. These are stored as `self._caller_id` / `self._hop_depth` and passed through from `wrap_tools()`.

At each `invoke()` / `run()` boundary:
1. If `caller_id is not None`, call `set_caller_context(caller_id, hop_depth)` (lazy import from `argus.security.identity`), saving the returned tokens.
2. Wrap the entire pre/execute/post sequence in `try/finally`.
3. In the `finally` block: if tokens were saved, call `reset_caller_context(tokens)`.

This means ContextVars are always reset — even when `pre_tool_call` raises `PermissionDeniedError`, `DelegationDepthError`, or the tool itself raises. No identity leaks across calls.

When `caller_id=None` (default), ContextVars are never touched — zero overhead, zero risk of mutation for backward-compatible single-agent calls.

### Task 2: REST Sidecar Identity Fields

`ToolCallRequest` gains two optional fields:
- `caller_id: str | None = None`
- `hop_depth: int = 0`

The `/tool-call` endpoint now calls:
```python
gateway.pre_tool_call(
    req.agent_role, req.tool_name, req.tool_input,
    caller_id=req.caller_id,
    hop_depth=req.hop_depth,
)
```

`DelegationDepthError` (a subclass of `ArgusSecurityError`) is caught automatically by the existing exception handler — no new handler needed. Returns 403 with `violation: "identity"`.

Requests without identity fields remain fully backward-compatible (defaults to `caller_id=None, hop_depth=0`).

## Verification

All plan verification gates passed:

```
pytest tests/adapters/test_langchain.py tests/adapters/test_crewai.py -k "caller_id or contextvars"
  6 passed, 21 deselected

pytest tests/cli/test_serve.py -k "caller_id or delegation"
  2 passed, 11 deselected

pytest tests/  (full phase gate)
  351 passed, 1 skipped
```

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

All key files verified present. All commits verified in git log.
