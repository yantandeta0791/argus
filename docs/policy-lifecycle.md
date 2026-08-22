# Policy Lifecycle (v0.6)

Every Argus security decision is now traceable to the exact policy that
produced it. This page describes the policy metadata stamp, its audit
semantics, and the recommended operational lifecycle.

## The stamp

Declare a policy identity in `argus.yaml`:

```yaml
policy:
  name: prod-baseline
  version: "1.2.0"
  approved_by: security-team
  change_ticket: CHG-4821
```

The gateway computes a **sha256 hash of the entire effective config** and
stamps every `tool_call_pre` audit event with:

```json
{
  "policy_name": "prod-baseline",
  "policy_version": "1.2.0",
  "policy_approved_by": "security-team",
  "policy_change_ticket": "CHG-4821",
  "policy_hash": "b64c455f6937…"
}
```

The `policy_hash` covers *everything* — rules, egress lists, provenance
requirements, spend caps — not just the declared name/version. Two configs
that differ in any enforced behavior produce different hashes, even when
their version strings match. That makes the hash the authoritative identity;
the human-readable fields are for people.

No `policy:` section → no stamp → audit events look exactly like v0.5.

## Why this matters

Combined with the hash-chained audit log, you can now answer, with evidence:

- *Which policy version blocked this call?* — read it off the event.
- *Was this run governed by the approved config?* — compare `policy_hash`
  against the hash recorded at deploy time.
- *Did someone change the policy mid-stream?* — hashes change; the chain
  shows exactly where.

## Recommended lifecycle

1. **Author** policy changes in git (`argus.yaml` is code — review it like code).
2. **Record** the expected `policy_hash` at deploy time (CI prints it; store it).
3. **Verify** in production: sample audit events, confirm the running hash
   matches the deployed artifact.
4. **Rollback** = redeploy the previous config file; the hash change is
   self-documenting in every subsequent audit line.

Shadow/dry-run mode (run new policy, log would-be decisions without
enforcing) remains future work — tracked for v0.7 alongside OPA bundle
interoperability.
