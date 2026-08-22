# Provenance-Aware Execution (v0.5)

Instruction provenance is a deterministic answer to one question: **where did
the instruction that triggered this tool call come from?** It closes the
confused-deputy kill chain: retrieved content that says "now email the
attacker" can no longer drive a `send_email` tool call, because the gateway
knows the instruction did not originate with the user.

This is not prompt classification. Provenance is set in deterministic code at
adapter boundaries — never inferred from content (an LLM-mediated or inferred
provenance would violate Argus's core guarantee and is permanently out of
scope).

## The provenance enum

| Value | Meaning | Set when |
|---|---|---|
| `user_originated` | Direct user instruction | Default; explicit user prompts |
| `untrusted_retrieval` | Content from outside the agent process | Adapter returns RAG/web/MCP/file content into LLM context |
| `system` | Config- or framework-internal calls | Scheduled jobs, internal maintenance calls |

## Gate 0.75

Gate order (relevant slice): **0.5 Identity → 0.75 Provenance → 1 Permission**.

A tool declared with a provenance requirement is blocked *before* the
permission check when the active provenance does not satisfy it:

```
ProvenanceViolationError(gate="provenance",
                         provenance="untrusted_retrieval",
                         required="user_originated")
```

Fail-closed semantics match `DelegationDepthError`: the exception propagates
through `StateMachine.run()`, artifacts roll back, `RunResult.success=False`.

## Configuration (argus.yaml)

```yaml
tools:
  send_email:
    require_approval: true        # v0.3 HITL can combine with provenance
    provenance_required: user_originated
  export_data:
    provenance_required: user_originated
  search:
    provenance_required: any      # explicit "any provenance is fine"
```

Invalid values fail at startup (`ConfigValidationError` naming the tool), not
at runtime.

## Python API

```python
from argus.security.provenance import (
    Provenance,
    get_provenance,
    reset_provenance,
    set_provenance,
)

tokens = set_provenance(Provenance.UNTRUSTED_RETRIEVAL)
try:
    get_provenance()   # Provenance.UNTRUSTED_RETRIEVAL
finally:
    reset_provenance(tokens)   # token-based reset, async-safe via ContextVar
```

The API mirrors `set_caller_context` / `get_caller_context` exactly.

## Where adapters tag automatically

Every adapter sets `untrusted_retrieval` around the point where external
content flows back toward the LLM (token-based finally reset):

| Adapter | Tagging point |
|---|---|
| LangChain | after `tool.invoke()` returns, around post-gates |
| CrewAI | after `tool.run()` returns |
| AutoGen | after `run_json()` / callable return |
| MCP middleware | around `post_tool_call` on server responses |
| REST sidecar | client-declared `provenance` field on `/tool-call`, validated against the closed enum (422 on unknown values) |

Application code never needs to touch the ContextVar unless it introduces a
new external-content source; then set/reset around the hand-off as above.

## Observability

- Every `tool_call_pre` audit event carries `"provenance"`.
- OTel violation spans carry the gate name `provenance` (severity HIGH).
- The HITL banner prints `Provenance: <value>` above any delegation line when
  provenance is not `user_originated`; output is byte-identical to v0.4 otherwise.

## Design decisions locked for v0.5

- No LLM-mediated classification of provenance.
- No automatic promotion (`untrusted_retrieval` never becomes
  `user_originated` without an explicit human action).
- Provenance is per-execution-context (ContextVar), not global state.
