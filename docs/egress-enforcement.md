# Egress Enforcement (v0.6)

Argus v0.6 adds an enforcement mode to the egress allowlist. In v0.x the
checker was log-only: out-of-allowlist hostnames produced a `SecurityEvent`
but the call continued. That was honest but weak — a "hard control plane"
that only wrote log lines.

## Two modes

| Mode | Config | Violation behavior |
|---|---|---|
| `log_only` (default) | `egress.enforce: false` or absent | `SecurityEvent` emitted, call continues (v0.x behavior, unchanged) |
| `enforce` | `egress.enforce: true` | `SecurityEvent` emitted **and** `EgressViolationError` raised — the tool call fails closed |

## Configuration

```yaml
egress:
  enforce: true
  allowlist:
    - api.anthropic.com
    - api.openai.com
    - internal-api.corp.local
```

## What is enforced — and what is not

Enforcement is **application-level at the tool boundary**: when a skill or
tool declares egress targets (via `skill.yaml` `egress_allowlist`) and a
target is not on the gateway allowlist, the post-call gate raises and the
output is discarded.

This is not network-layer isolation. A tool that ignores Argus and opens its
own sockets is outside this control. For defense in depth:

- run agents in containers with network policies (Kubernetes `NetworkPolicy`,
  Docker `--network`), or a proxy that enforces the same allowlist
- treat Argus egress enforcement as the policy decision point, and the
  container/netns layer as the enforcement point

The two layers should share the same allowlist source of truth (the
`argus.yaml` `egress:` section) — generate network policy from it so drift
is impossible.

## Semantics

- The violation event carries `"mode": "enforce" | "log_only"` in metadata,
  so SIEM queries can distinguish recorded-but-allowed from blocked.
- `EgressViolationError` propagates through `StateMachine.run()` → artifact
  rollback, `RunResult.success=False` — identical to other hard-stop gates.
- Allowlisted hostnames never emit events.

## Migration

v0.x deployments see zero behavior change (default is `log_only`). To adopt
enforcement: set `enforce: true`, then watch `argus audit` for
`egress` violations in `log_only` mode for a week before flipping — anything
that fires is a tool that will start failing.
