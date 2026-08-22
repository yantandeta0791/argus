# Policy Shadow Mode & Decision Evidence (v0.8)

> **Warning:** Shadow mode is an observation tool, **not a security control**.
> It intentionally lets configured provenance and permission denials proceed so
> operators can measure the effect of a policy. Do not use it to protect
> destructive production tools, secrets, regulated data, or compliance controls.

## Why shadow mode exists

Hard policy enforcement is valuable only after a team knows the policy reflects
real production behavior. Shadow mode evaluates the same deterministic policy
but records what it *would* have blocked instead of interrupting the tool call.
It is the bridge between policy authoring and safe enforcement.

```yaml
policy:
  name: prod-baseline
  version: "1.3.0"
  mode: shadow # enforce is the default
```

## What shadows

| Gate | In shadow mode |
|---|---|
| Gate 0.75 — provenance requirement | emits `would_block`, continues to permission |
| Gate 1 — RBAC permission | emits `would_block`, continues to HITL/audit/tool |
| Identity / delegation depth | **never shadowed** — still hard-blocks |
| Audit availability | **never shadowed** — no audit means no trusted shadow run |
| Injection, redaction, egress, anomaly | **not shadowed in v0.8** — post-call behavior needs a separate safety contract |

## Decision event contract

Every policy evaluation creates a normalized `policy_decision` record:

```json
{
  "event_type": "policy_decision",
  "decision_id": "uuid",
  "mode": "shadow",
  "outcome": "would_block",
  "gate": "provenance",
  "tool_name": "export_data",
  "agent_role": "analyst",
  "rule": "provenance_required=user_originated but active=untrusted_retrieval",
  "reason": "Tool requires user-originated instruction",
  "caller_id": "research-agent",
  "hop_depth": 1,
  "provenance": "untrusted_retrieval",
  "policy_hash": "..."
}
```

`decision_id` correlates operator reports to the immutable hash-chained audit
stream. `policy_hash` ties a decision to the exact effective configuration,
not merely its human-readable version.

## Operator workflow

1. **Author:** change `argus.yaml` in git, with `policy.name`, `policy.version`,
   and `policy.mode: shadow`.
2. **Validate:** run the full test suite and inspect the generated policy hash.
3. **Deploy shadow:** use a representative environment and business cycle.
4. **Review evidence:**

   ```bash
   argus audit --shadow --summary ./runs/audit.jsonl
   ```

5. **Resolve findings:** false positives indicate a rule/policy mismatch;
   true positives identify actions to restrict or route through HITL.
6. **Approve:** review the policy diff and policy hash in a change request.
7. **Promote:** switch only `policy.mode` to `enforce`; deploy the reviewed
   config. The audit chain makes that mode/hash transition visible.

## Example rollout output

```text
Shadow policy summary: prod-baseline@1.3.0 (hash 4f8b2d…)
43 would-block decisions / 1,209 evaluated calls

Gate        Tool          Rule                                      Count
provenance  export_data   requires user-originated; got retrieval   31
permission  deploy_prod   role=analyst tool=deploy_prod             12
```

Reports group by `policy_hash`. Argus does **not** silently combine data from
different policies: mixed hashes mean behavior changed mid-observation and must
be investigated separately.

## Threat model

| Threat | Risk | Mitigation |
|---|---|---|
| Shadow treated as enforcement | Dangerous tools execute during a supposed control rollout | Mode appears in every decision event; docs and CLI label `would_block`; only use in controlled observation environments |
| Policy drift | Operator reviews one config but runtime uses another | Every decision carries sha256 `policy_hash`; verify it at deployment and audit time |
| Audit tampering | Actor hides would-block evidence | Existing out-of-process hash-chained audit log; audit unavailability always blocks |
| Audit event volume | Broad shadow policies create large streams | Streaming JSONL summary; scope policies/tools deliberately; retain only required evidence |
| Replay / duplicate data | Summary inflates counts | `decision_id` is unique; downstream SIEM consumers should deduplicate by it |
| Mixed policy data | Results imply a policy result that never existed | Summary separates groups by policy hash and emits a mixed-hash warning |

## Limits and future work

- Shadow mode does not replace an approval workflow; pair high-impact actions
  with webhook HITL from v0.7.
- v0.8 is local policy evaluation. v0.9 will add OPA/Rego interoperability
  behind the same normalized `PolicyDecision` contract.
- Shadow evaluation for post-call controls will be designed separately; silently
  allowing injection/exfiltration to observe it would be unacceptable.
