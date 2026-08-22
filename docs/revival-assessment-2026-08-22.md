# Argus — Revival Assessment (2026-08-22)

Consolidated evidence-based review of the repository state at HEAD `761d997` (last commit 2026-05-08).
Companion documents: `docs/market-analysis-2026.md` (competitive landscape), `.planning/` (GSD planning state).

## 1. Executive summary

Argus is a **dormant but healthy** Python 3.12 runtime security library for AI agents. It is not abandoned
mid-refactor: HEAD is green (402 tests passing in 4.45s, ruff clean, demo benchmark passes), documented,
and mid-way through a planned v0.5 milestone ("Provenance-Aware Execution + v0.4 Stabilization") that was
fully scoped and planned on 2026-05-15/16 but never started. The revival path is: commit or discard the
pending planning-file changes, execute Phase 11 (debt closure), Phase 12 (provenance), then shift from
"library breadth" to the market-recommended "deployable enforcement plane with evidence" positioning.

## 2. What exists (verified)

**Validation run 2026-08-22:**
- `pytest -m "not integration"` → **402 passed, 1 deselected** in 4.45s
- `argus demo` → 4/4 violations caught, exit 0
- `uv run ruff check .` / `ruff format --check .` → clean (141 files)
- Size: 6,670 LOC in `argus/` (71 files), 7,827 LOC in `tests/` (70 files)

**Shipped milestones (git + `.planning/PROJECT.md` evidence):**
| Milestone | Date | Content |
|---|---|---|
| v0.1/v0.2 | 2026-03-08 | Security foundation (Casbin RBAC/ABAC, PromptShield, SecretRedactor, EgressChecker, hash-chained audit via out-of-process AuditDaemon), 5-state engine, LiteLLM router, spend caps, memory, skill architecture, CLI, LangChain adapter, Docker, CI |
| v0.3 | 2026-03-28 | CrewAI/AutoGen/MCP adapters, HITL gates (Gate 1.5), policy-as-code (`argus.yaml`), `argus audit`, OTel export, REST sidecar (`argus serve`) — 24/24 requirements |
| v0.4 | 2026-04-20 | Multi-agent identity (ContextVars, AgentRegistry, Gate 0.5, delegation depth), per-agent EWMA/z-score anomaly detection (Gates 1.75/5.5, graduated response) — 13/13 requirements, 4 with declared integration debt |

## 3. Architecture map

Four layers, dependencies point downward:

```
CLI / Demo (argus run|scan|demo|audit|serve)
Observability  (ObservabilityManager → trace.jsonl, security.jsonl, OTel spans)
Intelligence   (LLMRouter via LiteLLM, SpendTracker, MemoryManager/SQLite)
Execution      (StateMachine: PLAN→EXECUTE→VERIFY→REFLECT→COMMIT, fixed TRANSITION_SEQUENCE)
Security       (SecurityGateway — the core seam)
```

**The seam:** `SecurityGateway.pre_tool_call / post_tool_call` (`argus/security/gateway.py`).
Gate order: 0.5 Identity → 1 Permission → 1.75 anomaly pre-compute → 1.5 HITL → 2 Audit pre →
[execute] → 3 Injection → 4 Redaction → 5.5 Egress anomaly → 5 Egress allowlist → 6 Audit post.
All gates are deterministic Python; LLM output only ever enters as `tool_output` at Gate 3.
Adapters (LangChain proxy, CrewAI, AutoGen, MCP middleware, REST sidecar) all cross this one seam —
a deep module by design: small interface, all enforcement behind it.
Trust boundaries: audit daemon runs out-of-process over a Unix socket (compromised agent can't silence
the log); skills run in subprocess with stripped env; egress is **log-only** (no network enforcement yet).

## 4. Pros

- **Real, tested enforcement** — 402 tests, fail-closed semantics, deterministic guarantee is architecturally honest (verified in `gateway.py`, `docs/security-model.md`)
- **Excellent engineering hygiene** — GSD planning artifacts with requirement IDs, traceability tables, decision logs, TDD RED/GREEN commit discipline
- **Broad framework coverage** for a solo project: 4 adapters + REST sidecar for non-Python agents
- **Differentiated control point** (per market analysis): deterministic action authorization + tamper-evident evidence, which hyperscaler guardrails explicitly do not cover (AWS documents tool traffic its filters don't assess)
- **Clean optional-extra packaging**; adapters importable without frameworks installed

## 5. Cons / risks

- **Dormant 3.5 months** with uncommitted planning churn in the worktree (3 modified planning files, 20 deleted SUMMARY/PLAN files, untracked pitch PDF) — first action is to resolve this
- **v0.4 known debt** (CLEAN-01..07): `hop_depth` missing at 5 anomaly audit sites, REST sidecar can hang a worker on anomaly-only ESCALATE (stdin HITL), `SecurityEvent` identity fields unpopulated at 2 sites — all planned, none executed
- **Egress is log-only** — weakens the "hard control plane" claim against enterprise buyers
- **Regex-only injection detection** — fine as a deterministic baseline, not a defense; must not be marketed as such
- **Single-maintainer bus factor of 1**; version still says `0.2.0` in `pyproject.toml` despite v0.4 shipped
- **No policy lifecycle** (versioning/signing/simulation) — enterprise-operability gap
- **Identity model is framework-local** (`caller_id` strings), not workload/human identity

## 6. Delivery plan

**Phase 0 — Rehydrate (half a day)**
1. Review and commit (or revert) the pending `.planning/` changes; add the pitch PDF to git or gitignore
2. Bump `pyproject.toml` version to 0.4.0; tag releases v0.2.0/v0.3.0/v0.4.0 retroactively
3. Verify CI green on GitHub; confirm PyPI/install path works

**Phase 11 — v0.4 debt closure (1–2 days; plans already written in `.planning/phases/11-*/`)**
- Execute 11-01 (hop_depth at 5 audit sites, `SecurityEvent.from_context()`, Gate 5.5 `max_depth`), 11-02 (REST `AnomalyEscalateError` → 503 + regression tests), 11-03 (validation sign-off, frontmatter)
- Acceptance: all CLEAN-01..07 criteria in `.planning/REQUIREMENTS.md` verifiably true; suite green

**Phase 12 — Provenance-aware execution (3–5 days; PROV-01..07 fully specified)**
- Gate 0.75 provenance enforcement (`untrusted_retrieval | user_originated | system`), ContextVar set at adapter boundaries, `provenance_required` in argus.yaml, audit/OTel/HITL/REST propagation
- This is a genuine market differentiator (confused-deputy / indirect-injection mitigation) — ship it and blog it

**v0.6 — Enterprise credibility (2–4 weeks, informed by market analysis)**
- Enforceable egress (container/network enforcement mode with documented fail-closed semantics)
- Adversarial regression suite (direct/indirect injection, tool-description injection, confused-deputy, exfiltration) with published results
- Policy lifecycle: versioned argus.yaml bundles, dry-run/shadow mode, decision explanations
- SIEM/webhook export connectors; OpenTelemetry evidence export hardening
- Webhook HITL (HITL-06) to unblock REST-side approvals
- LlamaIndex adapter; OpenTelemetry GenAI semantic-convention alignment

**Positioning (from `docs/market-analysis-2026.md`):** *deterministic agent action security control plane* —
"enforces what an agent may **do**, not what it may say." Complement (don't compete with) Prisma AIRS /
Lakera / Bedrock Guardrails classifiers; integrate with them as pluggable detection providers.

## 7. Immediate next action

Say the word and I start Phase 0 + Phase 11 (the debt-closure plans are already written and testable).
