# v0.8 Policy Shadow Mode & Decision Explanations Implementation Plan

> **For Hermes:** Implement task-by-task with TDD. Do not merge shadow mode into
> enforcement until all decision/audit semantics and rollout tests pass.

**Goal:** Let enterprises evaluate a new Argus policy safely in production without blocking work, then provide a durable, explainable audit record of every would-block and enforced decision.

**Architecture:** Keep `SecurityGateway` as the deep enforcement module. Add one small, explicit policy-operation configuration object (`enforce | shadow`) and one normalized `PolicyDecision` record created at gateway gate boundaries. In **enforce** mode existing exceptions and behavior remain unchanged. In **shadow** mode selected eligible gates record a `would_block` decision and continue execution. Audit events receive a stable `decision_id`, policy metadata/hash, gate, rule, reason, and mode. `argus audit --shadow` filters and renders these decisions.

**Tech Stack:** Python 3.12; existing dataclasses/Pydantic, JSONL audit chain, Rich CLI, pytest/pytest-asyncio. No new third-party dependency.

---

## Scope and non-goals

### In scope

1. `policy.mode: enforce | shadow` in `argus.yaml`; default `enforce`.
2. Shadow evaluation for deterministic *pre-call policy gates*: Gate 0.75 provenance and Gate 1 permission.
3. Structured, queryable `policy_decision` audit events including policy config hash and decision ID.
4. CLI filter/rendering: `argus audit --shadow`.
5. A comparison utility that summarizes would-block decisions by tool/gate/rule from JSONL.
6. Documentation: rollout guide, event contract, limitations, migration steps.

### Explicitly not in scope

- Shadowing Gate 2/6 audit availability: audit failure must always stop; there is no trustworthy shadow run without audit.
- Shadowing identity/delegation depth: allowing unknown or too-deep agent chains is unsafe and changes attribution semantics.
- Shadowing prompt injection/redaction/egress post-call gates: tool output has already occurred and handling is semantically different; defer until a post-call shadow contract is designed.
- Auto-promoting shadow policy to enforce; operator must make the change in git and redeploy.
- OPA/Rego adapter; it is v0.9 after the local decision contract is stable.

## Decision model

```python
@dataclass(frozen=True)
class PolicyDecision:
    decision_id: str              # uuid4, one per gate evaluation
    mode: Literal["enforce", "shadow"]
    outcome: Literal["allow", "block", "would_block"]
    gate: str                     # "provenance" | "permission"
    tool_name: str
    agent_role: str
    rule: str | None
    reason: str                   # human-readable, stable enough for operator use
    caller_id: str | None
    hop_depth: int
    provenance: str
    policy_metadata: dict[str, Any]  # policy_hash + policy_name/version if configured
```

`PolicyDecision` is an internal deep module: callers cross one seam (`_record_policy_decision`) and never construct differently shaped audit dictionaries themselves. It is serialized into a JSONL event:

```json
{
  "event_type": "policy_decision",
  "decision_id": "…",
  "mode": "shadow",
  "outcome": "would_block",
  "gate": "provenance",
  "tool_name": "export_data",
  "rule": "provenance_required=user_originated but active=untrusted_retrieval",
  "reason": "Tool requires user-originated instruction",
  "policy_hash": "…"
}
```

### Semantics

| Gate result | Enforce mode | Shadow mode |
|---|---|---|
| provenance requirement matches | `allow` event; continue | `allow` event; continue |
| provenance requirement mismatches | record `block`; raise `ProvenanceViolationError` | record `would_block`; continue to permission |
| permission allows | `allow`; continue | `allow`; continue |
| permission denies | record `block`; raise existing exception | record `would_block`; continue to HITL/audit/tool |

A shadow run is an observation tool, **not** a security boundary. Documentation must make this unavoidable.

---

## Task 1: Define policy mode and normalized decision record

**Objective:** Add a small configuration/interface layer without changing existing gateway behavior.

**Files:**
- Create: `argus/security/policy_decision.py`
- Modify: `argus/security/gateway.py`
- Modify: `argus/llm/config.py`
- Test: `tests/security/test_policy_decision.py`

**Step 1 — RED tests**

Test the public configuration seam:

```python
def test_load_gateway_config_defaults_policy_mode_to_enforce():
    assert load_gateway_config({}).policy_mode == "enforce"

def test_load_gateway_config_accepts_shadow_mode():
    cfg = load_gateway_config({"policy": {"mode": "shadow"}})
    assert cfg.policy_mode == "shadow"

def test_load_gateway_config_rejects_unknown_policy_mode():
    with pytest.raises(ConfigValidationError, match="policy.mode"):
        load_gateway_config({"policy": {"mode": "observe"}})
```

Test `PolicyDecision.to_audit_event()` returns a known literal dictionary with no timestamp/hash-chain fields (those belong to `AuditLogger`).

**Step 2 — confirm RED**

```bash
.venv/bin/pytest tests/security/test_policy_decision.py -q
```

Expected: failure because `PolicyDecision` and `GatewayConfig.policy_mode` do not exist.

**Step 3 — GREEN implementation**

- Add `PolicyMode(StrEnum)` (`ENFORCE`, `SHADOW`) and frozen `PolicyDecision` with `to_audit_event()` in `argus/security/policy_decision.py`.
- Add `policy_mode: str = "enforce"` to `GatewayConfig`.
- Extend `load_policy_metadata()` / `load_gateway_config()` to validate `policy.mode`; do **not** copy `mode` into audit metadata as `policy_mode` is a first-class event field.
- Keep an absent `policy:` section fully backward compatible.

**Step 4 — GREEN verification**

```bash
.venv/bin/pytest tests/security/test_policy_decision.py -q
uv run ruff check argus/security/policy_decision.py argus/security/gateway.py argus/llm/config.py
```

**Step 5 — commit**

```bash
git add argus/security/policy_decision.py argus/security/gateway.py argus/llm/config.py tests/security/test_policy_decision.py
git commit -m "feat(policy): add enforce/shadow mode and decision record"
```

---

## Task 2: Shadow the provenance gate (Gate 0.75)

**Objective:** In shadow mode, provenance mismatch records a would-block decision and proceeds to Gate 1; enforce mode remains byte-for-byte compatible in outcome.

**Files:**
- Modify: `argus/security/gateway.py:212-239` (current Gate 0.75 block)
- Test: `tests/security/test_policy_shadow.py`

**Step 1 — RED tests at the public gateway seam**

```python
def test_shadow_provenance_mismatch_records_would_block_and_allows():
    gateway = make_gateway(
        policy_mode="shadow",
        provenance_required={"export_data": "user_originated"},
    )
    with provenance("untrusted_retrieval"):
        gateway.pre_tool_call("agent", "export_data", {})
    event = last_policy_decision(gateway.audit)
    assert event["outcome"] == "would_block"
    assert event["gate"] == "provenance"

def test_enforce_provenance_mismatch_still_raises():
    gateway = make_gateway(policy_mode="enforce", ...)
    with provenance("untrusted_retrieval"):
        with pytest.raises(ProvenanceViolationError):
            gateway.pre_tool_call("agent", "export_data", {})
```

Also assert the shadow event includes `policy_hash`, `decision_id`, caller identity/hop depth, and provenance.

**Step 2 — RED command**

```bash
.venv/bin/pytest tests/security/test_policy_shadow.py -k provenance -q
```

**Step 3 — GREEN implementation**

- Add `_record_policy_decision(...)` private helper to `SecurityGateway`; it creates a `PolicyDecision`, calls `_audit.send`, and returns it.
- At Gate 0.75 mismatch: if `policy_mode == "shadow"`, call helper with `outcome="would_block"`, do not invoke `_emit_violation`, and continue. Otherwise retain existing exception path.
- Record an `allow` decision only for gates configured by policy. Do not add noisy policy events for unconfigured tools.

**Step 4 — verify**

```bash
.venv/bin/pytest tests/security/test_policy_shadow.py -k provenance -q
.venv/bin/pytest tests/security/test_provenance_gate.py -q
```

**Step 5 — commit**

```bash
git add argus/security/gateway.py tests/security/test_policy_shadow.py
git commit -m "feat(policy): shadow provenance gate decisions"
```

---

## Task 3: Shadow the permission gate (Gate 1)

**Objective:** In shadow mode, Casbin denials are observable but do not stop execution.

**Files:**
- Modify: `argus/security/gateway.py:241-263` (current permission try/except)
- Test: `tests/security/test_policy_shadow.py`

**Step 1 — RED tests**

```python
def test_shadow_permission_denial_records_would_block_and_allows():
    gateway = make_gateway(policy_mode="shadow", permissions=deny_export)
    gateway.pre_tool_call("analyst", "export_data", {})
    event = last_policy_decision(gateway.audit)
    assert event["outcome"] == "would_block"
    assert event["gate"] == "permission"

def test_enforce_permission_denial_still_raises():
    gateway = make_gateway(policy_mode="enforce", permissions=deny_export)
    with pytest.raises(PermissionDeniedError):
        gateway.pre_tool_call("analyst", "export_data", {})
```

Test a provenance mismatch + permission denial emits **two** decisions in shadow mode, in gate order: provenance then permission.

**Step 2 — RED command**

```bash
.venv/bin/pytest tests/security/test_policy_shadow.py -k permission -q
```

**Step 3 — GREEN implementation**

- Catch `ArgusSecurityError` in permission path as it does today.
- In shadow mode: create `would_block` permission decision; do not emit violation span or SecurityEvent blocked event; continue to Gate 1.5.
- In enforce mode: record a `block` decision first, then preserve existing `SecurityEvent`, OTel, and raise behavior.

**Step 4 — verify**

```bash
.venv/bin/pytest tests/security/test_policy_shadow.py -q
.venv/bin/pytest tests/security/test_gateway.py -q
```

**Step 5 — commit**

```bash
git add argus/security/gateway.py tests/security/test_policy_shadow.py
git commit -m "feat(policy): shadow permission gate decisions"
```

---

## Task 4: Explain and query policy decisions in `argus audit`

**Objective:** Give operators a direct answer to “what would this policy block, and why?” without parsing raw JSON.

**Files:**
- Modify: `argus/cli/audit.py`
- Test: `tests/cli/test_audit.py`

**Step 1 — RED tests**

Test the CLI public seam via Typer runner or the existing audit test helpers:

```python
def test_normalize_policy_decision_for_shadow_filter(tmp_path): ...
def test_audit_shadow_filter_shows_only_would_block_events(tmp_path): ...
def test_render_policy_decision_includes_mode_rule_policy_hash(capsys): ...
```

**Step 2 — RED command**

```bash
.venv/bin/pytest tests/cli/test_audit.py -k shadow -q
```

**Step 3 — GREEN implementation**

- Add `--shadow` boolean option to `audit_command`.
- If `--shadow`: retain only normalized events whose `outcome == "would_block"` or whose `event_type == "policy_decision"` and `mode == "shadow"`.
- Extend `_render_event` with conditional fields:
  - `mode: shadow`
  - `decision: would_block`
  - `reason: ...`
  - `policy: <name>@<version>` if present
  - abbreviated `policy_hash: <first 12>`
- Add `would_block: orange` to `_OUTCOME_BORDER_COLORS`.

**Step 4 — verify**

```bash
.venv/bin/pytest tests/cli/test_audit.py -q
.venv/bin/argus audit --help
```

**Step 5 — commit**

```bash
git add argus/cli/audit.py tests/cli/test_audit.py
git commit -m "feat(audit): render and filter shadow policy decisions"
```

---

## Task 5: Add a decision-summary API/CLI report

**Objective:** Aggregate a JSONL stream into a rollout decision report without external services.

**Files:**
- Create: `argus/policy/report.py`
- Modify: `argus/cli/audit.py` (or new `argus/cli/policy.py` registered in `argus/cli/main.py`)
- Test: `tests/policy/test_report.py`, `tests/cli/test_audit.py`

**Design:** `summarize_decisions(events: Iterable[dict]) -> PolicyDecisionSummary` is the deep module. It aggregates only `policy_decision` events by `(gate, tool_name, rule)`, returns total decisions, total would-blocks, and policy hashes observed. CLI offers:

```bash
argus audit --shadow --summary ./runs/audit.jsonl
```

Example output:

```
Shadow policy summary: prod-baseline@1.3.0 (hash abc…)
43 would-block decisions / 1,209 evaluated calls

Gate        Tool          Rule                                      Count
provenance  export_data   requires user_originated; got retrieval   31
permission  deploy_prod   role=analyst tool=deploy_prod             12
```

**TDD verification:** known literal JSONL fixture → exact aggregate result; empty input → zero-valued summary; mixed policy hashes → warning field, never merge silently.

**Commit:**

```bash
git commit -m "feat(policy): add shadow decision rollout summary"
```

---

## Task 6: Documentation and threat model

**Objective:** Make shadow mode deployable without accidentally treating it as enforcement.

**Files:**
- Create: `docs/policy-shadow-mode.md`
- Modify: `docs/policy-lifecycle.md`
- Modify: `docs/index.md`
- Modify: `README.md`
- Modify: `docs/configuration.md`

**Required documentation sections:**

1. Exact config examples for `enforce` and `shadow`.
2. Strong warning: shadow mode never blocks; it is unsuitable for secrets, production destructive tools, or compliance controls until promoted.
3. Event schema + `decision_id` correlation story.
4. Rollout procedure:
   - validate in CI
   - deploy shadow mode
   - collect one representative business cycle
   - run `argus audit --shadow --summary`
   - remediate policy false positives / permissions
   - review the policy hash and approve a git PR
   - deploy `enforce`
5. Limitations and deferred gates.
6. A threat model table: spoofing/tampering/replay of audit records; policy config drift; audit volume DoS; dangerous shadow-mode misuse, and mitigations.

Add docs tests only for code examples that can be executed cheaply; manually review all YAML/CLI snippets against the implementation.

**Commit:**

```bash
git add docs README.md
git commit -m "docs(policy): add shadow rollout and decision evidence guide"
```

---

## Task 7: Release verification and v0.8.0 tag

**Objective:** Prove new behavior and preserve v0.7 behavior before release.

**Commands:**

```bash
.venv/bin/pytest -m 'not integration' -q
uv run ruff check .
uv run ruff format --check .
.venv/bin/argus demo
```

**Acceptance criteria:**

- Enforce mode still blocks provenance and permission denial exactly as v0.7.
- Shadow mode never raises for configured provenance/permission denials and records deterministic `would_block` events.
- Every shadow decision has `decision_id`, `policy_hash`, `mode`, `outcome`, `gate`, `rule`, identity and provenance.
- `argus audit --shadow` returns only would-block decisions and renders explanation/policy fields.
- Summary never combines events from different policy hashes silently.
- Existing full suite green plus all new tests.
- README/docs describe shadow mode’s non-enforcement limitation prominently.

**Release steps:**

```bash
# After all tests pass and docs are reviewed:
# bump pyproject.toml to 0.8.0
git commit -m "chore(release): v0.8.0"
git push origin master
git tag -a v0.8.0 -m "v0.8.0 — Policy Shadow Mode and Decision Evidence"
git push origin v0.8.0
```

---

## Risks and design tradeoffs

| Risk / tradeoff | Decision |
|---|---|
| Shadow mode could be mistaken for protection | Explicit config mode, prominent docs warning, audit event says `would_block`; never shadow audit/identity/post-call controls. |
| Event volume grows | Emit allow decisions only for tools with explicit policy configuration; summary works streaming JSONL. |
| A mode toggle could bypass security | `policy.mode` is config-hashed and stamped in every event; changing it is visible in audit chain and requires a deployment. |
| Permission shadow behavior can expose tools | Correct by definition of shadow mode; never use it for high-risk production actions until the policy is promoted. |
| Decision schema locks future OPA integration | Keep it minimal, action-level, provider-neutral; v0.9 OPA adapter returns the same normalized decision record. |
| Multiple policy hashes in a report | Do not merge; summary emits a warning and groups by policy hash. |

## Approval request

Approve this v0.8 scope if you want Argus to prioritize safe enterprise rollout and explainability. On approval, implementation order is exactly Tasks 1–7. OPA/Rego integration remains v0.9, after this local decision contract is stable.
