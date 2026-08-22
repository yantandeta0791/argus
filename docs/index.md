# Argus Documentation

| Document | Contents |
|---|---|
| [security-model.md](security-model.md) | The deterministic guarantee, gate order, exception hierarchy, trust boundaries |
| [configuration.md](configuration.md) | Full `argus.yaml` field reference: models, spend caps, gateway config |
| [provenance.md](provenance.md) | **v0.5** — instruction provenance, Gate 0.75, adapter tagging, REST API |
| [egress-enforcement.md](egress-enforcement.md) | **v0.6** — enforce vs log-only egress modes, network-layer defense in depth |
| [adversarial-testing.md](adversarial-testing.md) | **v0.6** — the attack corpus, how to run it, published detection scope |
| [policy-lifecycle.md](policy-lifecycle.md) | **v0.6** — policy metadata stamp, config hashing, operational lifecycle |
| [webhook-hitl.md](webhook-hitl.md) | **v0.7** — signed operator approval over HTTP, request/response contract, failure semantics |
| [skills.md](skills.md) | Skill manifests, trust tiers, lifecycle stages |

## Gate order (complete)

```
PRE-CALL                              POST-CALL
0.5  Identity (caller_id, hop depth)   3    Injection scan (hard stop)
0.75 Provenance requirement check      4    Secret/PII redaction (soft block)
1    Permission (RBAC, hard stop)      5.5  Egress volume anomaly
1.5  HITL approval (merged banner)     5    Egress allowlist (log-only or enforce)
1.75 Frequency anomaly pre-compute     6    Audit post-call (hard stop)
2    Audit pre-call (hard stop)
         [ tool executes ]
```

All gates are deterministic Python. LLM output enters only as `tool_output`
at Gate 3 and can never influence gate logic.
