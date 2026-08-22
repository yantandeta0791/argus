# Argus Architecture & Codebase Archaeology Assessment

**Assessment date:** 2026-08-22  
**Repository assessed:** `/Users/ytandeta/Projects/personal/enterprise/argus`  
**Baseline:** `master` at `761d997` (`docs(readme): refresh roadmap with shipped v0.2/v0.3/v0.4 milestones`)  
**Scope:** Evidence-first static assessment plus safe local validation. Product source was not edited.

## Executive summary

Argus is a Python 3.12+ library/CLI intended to enforce deterministic gates around AI-agent tool calls. It has a substantive, well-tested security *library*: a gateway composes RBAC, terminal HITL, prompt-injection scanning, redaction, audit logging, identity/delegation controls, and statistical anomaly checks. It also supplies adapters for LangChain, CrewAI, AutoGen, FastMCP, and a FastAPI sidecar.

The most important revival finding is a runtime integration gap: `argus run` builds a `StateMachine` without handlers, while every missing handler defaults to `_noop_handler` ([`argus/engine/machine.py:31-37`](../argus/engine/machine.py#L31-L37), [`argus/cli/run.py:100-111`](../argus/cli/run.py#L100-L111)). Therefore the advertised full runtime currently traverses five states but does not invoke the injected `LLMRouter`, a `ToolRunner`, or user-defined tools. It can report success without accomplishing its task. The repository’s own planning artifacts acknowledge adjacent v0.4 integration debt and have Phase 11/12 unstarted.

Quality signals are nonetheless strong for the implemented library surface: 402 non-integration tests passed locally in 4.31 seconds. The synthetic `argus demo` completed successfully and caught its four scripted violations. The most urgent work is not broad refactoring—it is to choose and implement a real execution contract and wire it to the existing gateway/tool seams, then close documented security-integration gaps before treating Argus as an enterprise enforcement runtime.

## Repository, release, and delivery map

| Area | Evidence | Finding |
|---|---|---|
| Packaging | [`pyproject.toml:5-57`](../pyproject.toml#L5-L57) | Hatchling package `argus`, declared version **0.2.0**, Python `>=3.12`, console script `argus = argus.cli.main:app`. The package version conflicts with Git tags/roadmap claiming v0.4/v0.5 planning. |
| Primary source | `argus/` | Python package organized as `security`, `engine`, `llm`, `memory`, `observability`, `skills`, `adapters`, and `cli`. |
| Tests | [`pyproject.toml:59-65`](../pyproject.toml#L59-L65), `tests/` | Pytest with async auto mode and a live-API `integration` marker. The assessed checkout contains 403 collected test items. |
| Configuration | [`argus.yaml:6-32`](../argus.yaml#L6-L32), [`argus/llm/config.py:49-70`](../argus/llm/config.py#L49-L70) | YAML controls models/spend and can also configure RBAC, secrets, egress, HITL, OTel, agents, and anomaly behavior. Parsing uses `yaml.safe_load`. |
| Documentation | [`README.md:97-109`](../README.md#L97-L109), `docs/configuration.md`, `docs/security-model.md`, `docs/skills.md` | Good architecture and user-facing documentation, but several claims overstate the runnable end-to-end behavior described below. |
| Container delivery | [`Dockerfile:2-33`](../Dockerfile#L2-L33), [`docker-compose.yml:1-9`](../docker-compose.yml#L1-L9) | Multi-stage Python image defaults to `argus demo`; Compose only runs the demo and mounts `./runs`. |
| CI | [`.github/workflows/ci.yml:9-46`](../.github/workflows/ci.yml#L9-L46) | CI tests Python 3.12 and 3.13 with all optional extras, plus Ruff formatting/lint. No build/image/security scanner/publish job. |

### Git archaeology

* History starts 2026-03-04 with package/security-core scaffolding and grows through engine, LLM, memory, skills, observability, CLI, adapters, policy, REST, multi-agent, and anomaly work.
* Tags are `v0.1.0`, `v0.2.0`, `v0.3`, and `v0.4`; recent history shows v0.4 feature commits and a v0.4 tag. Yet packaging still declares `0.2.0` ([`pyproject.toml:5-8`](../pyproject.toml#L5-L8)).
* The roadmap identifies v0.5 Phase 11 (integration-debt closure) and Phase 12 (provenance-aware execution) as incomplete ([`.planning/ROADMAP.md:42-75`](../.planning/ROADMAP.md#L42-L75)); state says 0/3 Phase-11 plans complete ([`.planning/STATE.md:25-34`](../.planning/STATE.md#L25-L34)).
* The checkout was already dirty before this assessment: modified `.planning` files, deleted historical planning summaries, and untracked `docs/pitch/`. These are pre-existing workspace state, not findings about committed product behavior.

## Implemented capabilities (with evidence)

### 1. Deterministic tool-call gateway

`SecurityGateway` is the primary enforcement module. Its pre-call interface accepts role, tool name, input, optional caller identity, and delegation depth ([`argus/security/gateway.py:145-160`](../argus/security/gateway.py#L145-L160)); post-call accepts returned text and an optional skill manifest ([`argus/security/gateway.py:339-350`](../argus/security/gateway.py#L339-L350)).

Implemented gates include:

1. **Identity and delegation depth**: ContextVar-derived caller identity is mapped to role; calls beyond configured depth raise a security error ([`gateway.py:162-191`](../argus/security/gateway.py#L162-L191), [`identity.py:26-60`](../argus/security/identity.py#L26-L60)).
2. **Permissions**: Casbin-backed role/tool allow rules, explicit deny precedence, wildcard allow handling, and a permissive mode when no policy exists ([`permission/enforcer.py:28-48`](../argus/security/permission/enforcer.py#L28-L48), [`permission/enforcer.py:95-137`](../argus/security/permission/enforcer.py#L95-L137)).
3. **HITL**: tool-configured or anomaly-driven terminal prompt, one retry for invalid input, timeout/denial fail-closed ([`hitl.py:39-77`](../argus/security/hitl.py#L39-L77), [`hitl.py:113-159`](../argus/security/hitl.py#L113-L159)).
4. **Frequency anomaly detection**: before a tool call, it can block, escalate to HITL, or write warning/block audit events ([`gateway.py:215-322`](../argus/security/gateway.py#L215-L322)).
5. **Prompt injection scan and secret/PII redaction**: post-call output is scanned then sanitized before downstream use ([`gateway.py:352-370`](../argus/security/gateway.py#L352-L370)).
6. **Egress volume anomaly handling**: output length drives a separate detector; block/denial replaces output with a suppression placeholder ([`gateway.py:372-450`](../argus/security/gateway.py#L372-L450)).
7. **Declared egress allowlist validation and audit event**: manifest-declared hostnames are checked, but the code documents this as log-only ([`gateway.py:452-469`](../argus/security/gateway.py#L452-L469)).
8. **Fail-closed audit availability**: pre/post events go through the logger; unreachable logger errors propagate (documented at [`gateway.py:154-160`](../argus/security/gateway.py#L154-L160)).

### 2. Tool contracts and resilience seam

`ToolRunner` is a useful deep seam around a single async tool: Pydantic validation, gateway pre-call, retry/circuit breaker execution, gateway post-call, and output validation are ordered in one implementation ([`argus/engine/tools.py:1-17`](../argus/engine/tools.py#L1-L17), [`argus/engine/tools.py:126-207`](../argus/engine/tools.py#L126-L207)). It explicitly avoids retrying ambiguous failures for non-idempotent tools ([`argus/engine/tools.py:35-42`](../argus/engine/tools.py#L35-L42), [`argus/engine/tools.py:221-239`](../argus/engine/tools.py#L221-L239)).

### 3. Audit process and tamper-evident chain

The runtime launches a separate audit subprocess over a Unix-domain socket ([`argus/security/audit/daemon.py:41-53`](../argus/security/audit/daemon.py#L41-L53)). The logger process hash-chains JSON lines and flushes each accepted event ([`log_process.py:16-27`](../argus/security/audit/log_process.py#L16-L27)). This is separation from the agent process, not a fully hardened integrity boundary (see risks).

### 4. Model routing, spend tracking, memory, and observability

* `LLMRouter` uses `litellm.acompletion`, selects task override > state model > default, records usage/cost, and redacts task input before provider submission ([`llm/router.py:64-111`](../argus/llm/router.py#L64-L111), [`llm/router.py:113-165`](../argus/llm/router.py#L113-L165)).
* Config parsers assemble gateway configuration from YAML sections ([`llm/config.py:297-325`](../argus/llm/config.py#L297-L325)) and expand `${ENV_VAR}` in OTel headers ([`llm/config.py:82-104`](../argus/llm/config.py#L82-L104)).
* The state machine provides a fixed PLAN → EXECUTE → VERIFY → REFLECT → COMMIT sequence, cost pre-check, snapshot rollback, and optional observability hooks ([`engine/machine.py:21-28`](../argus/engine/machine.py#L21-L28), [`engine/machine.py:81-147`](../argus/engine/machine.py#L81-L147)).
* File-based trace/security streams and OTLP support are present under `argus/observability/`; CLI wiring creates `trace.jsonl`, `security.jsonl`, audit JSONL, and SQLite memory DB ([`cli/run.py:55-105`](../argus/cli/run.py#L55-L105)).

### 5. Skills lifecycle and static controls

Skill manifests, source-content hashes, trust tiers, registry, and a seven-stage lifecycle are implemented. Lifecycle verifies source hash before execution and revokes registry state on failure ([`skills/lifecycle.py:81-100`](../argus/skills/lifecycle.py#L81-L100), [`skills/lifecycle.py:121-151`](../argus/skills/lifecycle.py#L121-L151)). Three bundled static capabilities are documented: security-audit, OWASP Agentic Top 10 checks, and credential scanning ([`README.md:338-344`](../README.md#L338-L344)).

### 6. Framework / network integration seams

* **LangChain** synchronously proxies `tool.invoke`, setting/resetting caller ContextVars and applying pre/post gates ([`adapters/langchain.py:47-77`](../argus/adapters/langchain.py#L47-L77)).
* **CrewAI and AutoGen** adapters are included under `argus/adapters/`; optional extras declare their dependencies ([`pyproject.toml:35-47`](../pyproject.toml#L35-L47)).
* **FastMCP** middleware intercepts every `call_tool`; pre-gate errors prevent execution, while post-gate errors occur after the tool has run ([`adapters/mcp.py:94-118`](../argus/adapters/mcp.py#L94-L118)).
* **REST sidecar** exposes health and `/tool-call`, accepts caller identity/hop depth, and converts `ArgusSecurityError` to a 403 JSON response ([`cli/serve.py:13-27`](../argus/cli/serve.py#L13-L27), [`cli/serve.py:39-112`](../argus/cli/serve.py#L39-L112)).
* **CLI** registers `run`, `scan`, `demo`, `audit`, and `serve` ([`cli/main.py:13-29`](../argus/cli/main.py#L13-L29)).

## Architecture map

### Modules and seams

```text
User / framework / REST client / MCP client
            |
            | adapter proxy, middleware, or POST /tool-call
            v
  SecurityGateway (primary enforcement interface)
    identity -> permission -> HITL/anomaly -> audit pre
            |                                 |
            v                                 v
   ToolRunner / framework-native tool      Unix socket
   schemas, retries, circuit breaker       AuditDaemon -> JSONL hash chain
            |
            v
  tool result -> injection scan -> redaction -> egress/anomaly -> audit post
            |
            +--> framework/client response or LLM context

CLI `run` additionally constructs:
  YAML config -> LLMRouter + SpendTracker + MemoryManager + ObservabilityManager
             -> StateMachine (but currently with no state handlers)
```

### Data/control flow

1. A framework adapter or REST endpoint receives role/tool/input and may bind caller identity through ContextVars.
2. `SecurityGateway.pre_tool_call` resolves identity, applies RBAC, optional anomaly/HITL checks, then writes audit pre-call. A gate exception stops the pre-execution path.
3. For native `ToolRunner`, Pydantic validates input, executes the async tool through retry/circuit logic, converts output to text/JSON, then calls `post_tool_call` and validates the clean result.
4. The post path scans text for injection, redacts secrets, optionally suppresses anomalous output, performs log-only declared-egress checking, and writes audit post-call.
5. The CLI `run` path constructs infrastructure but presently does not install task handlers that call its LLM router or tool runner.

### Trust boundaries

| Boundary | Intended control | Evidence / caveat |
|---|---|---|
| Untrusted tool input / agent request → tool execution | RBAC, identity depth, optional terminal approval, audit pre-call | [`gateway.py:162-337`](../argus/security/gateway.py#L162-L337). **Default is permissive** when RBAC config is absent ([`enforcer.py:31-45`](../argus/security/permission/enforcer.py#L31-L45)). |
| Tool output → LLM/framework context | prompt shield, redaction, egress/anomaly post gates | [`gateway.py:339-471`](../argus/security/gateway.py#L339-L471). This relies on callers using the adapter/ToolRunner seam; arbitrary direct tool calls bypass it. |
| Agent process → audit log | Unix socket to separate subprocess; chained entries | [`audit/log_process.py:16-47`](../argus/security/audit/log_process.py#L16-L47). Same user/filesystem permissions and no signing/remote append-only store limit tamper resistance. |
| Skill source → execution | manifest validation/content hash, stripped subprocess environment | [`lifecycle.py:171-200`](../argus/skills/lifecycle.py#L171-L200), [`sandbox/isolator.py:30-54`](../argus/security/sandbox/isolator.py#L30-L54). The “sandbox” is environment stripping, explicitly not syscall/container isolation. |
| REST client → gateway | FastAPI Pydantic request model and exception mapping | [`serve.py:13-27`](../argus/cli/serve.py#L13-L27), [`serve.py:95-110`](../argus/cli/serve.py#L95-L110). No authentication, authorization of callers, TLS termination, rate limits, or request-size controls are in this module. |
| YAML configuration → runtime | `safe_load`, Pydantic regex validation | [`config.py:49-70`](../argus/llm/config.py#L49-L70), [`config.py:132-190`](../argus/llm/config.py#L132-L190). Configuration governance and secure defaults remain operational responsibilities. |

## Quality signals

* **Local non-live suite:** 402 passed, 1 deselected in 4.31s (command/result recorded below). Coverage spans adapters, CLI, engine, configuration, memory, observability, security, and skills.
* **CI intent:** a two-version 3.12/3.13 matrix installs every optional integration and runs tests; a separate job checks Ruff formatting and linting ([`.github/workflows/ci.yml:10-46`](../.github/workflows/ci.yml#L10-L46)).
* **Runnable no-key smoke path:** `argus demo` completed and reported all four synthetic violations caught.
* **Docs/planning maturity:** architecture/config/security/skills docs and phased plans exist. The plans explicitly list known integration debt rather than hiding it.
* **Negative local signal:** the checked-in `.venv` could run tests and CLI but did not have `ruff` installed, so this assessment could not execute the CI lint commands locally. This is an environment/dependency parity issue, not evidence that lint fails.

## Unimplemented, stub, dead, or misleading paths

1. **Critical: default runtime has no execution semantics.** `_noop_handler` is `pass` ([`engine/machine.py:31-37`](../argus/engine/machine.py#L31-L37)); missing handlers are assigned for all five states ([`engine/machine.py:75-79`](../argus/engine/machine.py#L75-L79)). `argus run` passes no `handlers` ([`cli/run.py:100-111`](../argus/cli/run.py#L100-L111)). Thus injected router, gateway, store, and observability mostly sit idle apart from state-transition/run-complete events. The CLI can claim success after five no-ops.
2. **HITL is terminal-only.** The REST sidecar returns 503 only when a tool is directly HITL-configured ([`serve.py:47-67`](../argus/cli/serve.py#L47-L67)). The roadmap identifies the missing anomaly-only escalation handling, which otherwise can reach stdin ([`.planning/STATE.md:49-57`](../.planning/STATE.md#L49-L57)).
3. **Known audit identity parity debt.** Roadmap success criterion says anomaly audit events lack `hop_depth` in five paths ([`.planning/ROADMAP.md:53-58`](../.planning/ROADMAP.md#L53-L58)); inspection corroborates anomaly payloads at [`gateway.py:227-236`](../argus/security/gateway.py#L227-L236), [`gateway.py:312-321`](../argus/security/gateway.py#L312-L321), and [`gateway.py:383-449`](../argus/security/gateway.py#L383-L449). Some SecurityEvent identity fields are likewise planned for correction.
4. **Egress “control” is not network enforcement.** It validates declared manifest hostnames after tool output, not actual socket/HTTP egress; code and README call it log-only ([`gateway.py:452-458`](../argus/security/gateway.py#L452-L458), [`README.md:270-273`](../README.md#L270-L273)).
5. **Skill sandbox is not a sandbox in the security-isolation sense.** It runs a local subprocess with a narrow environment but no container, filesystem restriction, syscall policy, UID separation, or outbound networking enforcement ([`sandbox/isolator.py:6-13`](../argus/security/sandbox/isolator.py#L6-L13)).
6. **Audit daemon silently discards malformed/unwritable events.** `handle_client` catches all exceptions and does nothing ([`audit/log_process.py:16-33`](../argus/security/audit/log_process.py#L16-L33)); client success only proves socket delivery, not durable acceptance. This weakens the claimed fail-closed audit property for malformed events or log-write failure.
7. **Interface documentation drift.** The repository/roadmap says v0.4 shipped while `pyproject.toml` remains 0.2.0. README says “206 passing tests” ([`README.md:479-495`](../README.md#L479-L495)); local current count is 402 selected tests. The docs should distinguish validated library behavior from full autonomous-agent behavior.

## Technical risks

| Priority | Risk | Why it matters | Evidence |
|---|---|---|---|
| P0 | Success-without-work `argus run` | A security product’s flagship execution command can return success without an LLM call or tool invocation, misleading operators and integration tests. | [`machine.py:31-37`](../argus/engine/machine.py#L31-L37), [`machine.py:75-79`](../argus/engine/machine.py#L75-L79), [`run.py:100-122`](../argus/cli/run.py#L100-L122) |
| P0 | Gateway bypass by integration choice | Gateway enforcement is library-mediated, not process-wide. New adapters or direct tool calls can escape gates unless every invocation uses a wrapper. | `ToolRunner` and individual adapters own the calls; no global interception exists. |
| P0 | Unsafe default authorization posture | Absent/empty RBAC config permits every call; the supplied `argus.yaml` has no RBAC section. | [`enforcer.py:31-45`](../argus/security/permission/enforcer.py#L31-L45), [`argus.yaml:1-46`](../argus.yaml#L1-L46) |
| P1 | REST sidecar deployment exposure | Endpoint accepts claimed `agent_role`/`caller_id` without auth, runs no TLS/auth/rate/request limits, and can be made public via `--host`. | [`serve.py:13-20`](../argus/cli/serve.py#L13-L20), [`serve.py:115-184`](../argus/cli/serve.py#L115-L184) |
| P1 | Terminal HITL blocks noninteractive workloads | Direct and anomaly-triggered paths use stdin; REST anomaly-only escalation is documented as open debt. | [`hitl.py:161-200`](../argus/security/hitl.py#L161-L200), [`.planning/STATE.md:51-54`](../.planning/STATE.md#L51-L54) |
| P1 | Audit durability/tamper-evidence overclaim | Hash chaining detects modifications only if logs are retained; same-host agent-capable users may alter/delete logs, and daemon drops errors silently. | [`log_process.py:16-47`](../argus/security/audit/log_process.py#L16-L47) |
| P1 | “Sandbox” overclaim | Environment stripping does not contain malicious skill code, file access, processes, or networking. | [`isolator.py:6-13`](../argus/security/sandbox/isolator.py#L6-L13) |
| P2 | Output schema breakage after redaction | ToolRunner serializes outputs to JSON, redacts the string, then reparses/validates it. A redaction can make structured output invalid or collapse it to `{result: ...}`. | [`tools.py:180-193`](../argus/engine/tools.py#L180-L193) |
| P2 | Module-global circuit breaker state | Registry is keyed only by `tool_name`, crossing runners/tests/configurations and ignoring later threshold/recovery configuration for the same name. | [`tools.py:39-64`](../argus/engine/tools.py#L39-L64), [`tools.py:117-124`](../argus/engine/tools.py#L117-L124) |
| P2 | Anomaly detector scope | In-memory detector state is process-local; roadmap notes REST needs single-worker enforcement when anomaly detection is enabled. Horizontal replicas have divergent baselines. | [`.planning/STATE.md:42-44`](../.planning/STATE.md#L42-L44) |

## Strengths and constraints

### Pros

* Clear primary seam: a single `SecurityGateway` composes gate ordering and makes adapter integration understandable.
* Well-factored submodules for permissions, audit, prompt shielding, redaction, identity, HITL, and anomaly detection.
* Strong unit/integration-style test breadth for current library behavior; optional dependency imports are intentionally lazy in adapters.
* Deterministic state sequence and direct proxy/MCP middleware choices reduce LLM-controlled transition or callback bypass risks.
* Practical local operability: installable CLI, demo with no API key, JSONL output, SQLite memory, Docker demo, and testable `build_app(gateway)` REST seam.
* Planning materials name outstanding gaps precisely, providing a credible recovery starting point.

### Cons / limitations

* No actual default agent/task executor binds user task → LLM output → tools → artifacts, making the `run` path incomplete.
* Security guarantee is conditional on correct adoption of wrappers and secure configuration, notably explicit RBAC.
* “Egress control,” “sandbox,” and “tamper-evident audit” are narrower mechanisms than enterprise readers may infer.
* REST is a gateway adapter, not an operationally hardened service.
* Version/docs/test-count drift and dirty planning state reduce release confidence.

## Prioritized engineering gaps and revival sequence

1. **P0 — Define and implement a minimal real execution module behind `argus run`.** Give the state machine explicit handlers that invoke the router where intended, select/execute registered `ToolRunner`s, persist artifacts, and fail if no executor is configured. Add end-to-end tests proving actual provider-call mocks and tool calls occur; do not report “Run complete” for no-op states.
2. **P0 — Establish explicit secure-default policy behavior.** For CLI/REST production modes, reject missing RBAC unless an explicit development/permissive flag is supplied; surface current policy mode in startup/audit output.
3. **P0 — Complete Phase 11 before extending security features.** Fix all anomaly audit identity payloads, SecurityEvent identity fields, REST anomaly escalation behavior, and their regressions exactly as documented in the committed planning artifacts.
4. **P1 — Specify the supported deployment/security model.** Add REST authentication/authorization, TLS/proxy guidance, request bounds, rate limiting, and safe host defaults. State that client-provided identity is untrusted until authenticated/mapped.
5. **P1 — Replace terminal-only HITL with an asynchronous approver interface.** Define a narrow approval seam with terminal and webhook/queue adapters, correlation IDs, expiry, and auditable decision identity. The REST sidecar should never read stdin.
6. **P1 — Make audit integrity durable.** Make logger write/parse failures observable and fail client calls when durability cannot be confirmed; add file permissions/ownership, signed checkpoints or remote append-only sink, rotation, verification, and recovery rules.
7. **P1 — Either contain skills or narrow the claim.** Introduce container/OS isolation with filesystem/network policy for untrusted skills, or accurately describe the current subprocess environment scrub as non-isolating.
8. **P2 — Harden structured output and resilience semantics.** Redact structured values before serialization/schema validation, preserve JSON validity, scope circuit breakers by manifest/config/runtime, and document reset behavior.
9. **P2 — Align packaging, release, docs, and CI.** Bump package version to the intended release, generate version/changelog from tags, update test claims, ensure dev extras in the reproducible local environment, and add build/image/audit verification gates.
10. **P2 — Add a deployment-safe anomaly backend.** Decide whether anomaly detection is single-process only or persist/share baseline state and implement replica-aware behavior.

## Validation performed

All commands were run from `/Users/ytandeta/Projects/personal/enterprise/argus`. The pytest command disables bytecode and pytest cache writes. Commands that produce normal runtime output (`demo`, `scan`) did not alter product source.

| Command | Exact result |
|---|---|
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/ -m 'not integration' -p no:cacheprovider --tb=short` | **402 passed, 1 deselected in 4.31s** (403 collected; one live integration test deselected). |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/argus --help` | Exit 0; listed `run`, `scan`, `demo`, `audit`, `serve`. |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/argus demo` | Exit 0; output reported “4 violations injected • 4 caught” and “All violations caught.” |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/argus scan argus/skills/security_audit --format json` | Exit 0; JSON output had `findings: []` and `passed: true`. |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/argus run --task 'smoke'` | Application exit **2**; correctly failed preflight with `Error: ANTHROPIC_API_KEY environment variable is not set.` No live provider call was attempted. |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/argus serve --help` and `... argus audit --help` | Exit 0; both command interfaces rendered. |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m ruff format --check . && ... ruff check .` | Exit **1** before checks: `.venv/bin/python: No module named ruff`. CI declares Ruff as a dev dependency, but this local virtual environment lacks it. |

## Assessment limits

This is a static/read-only assessment plus local non-live validation. It did not call a real LLM provider, start a long-lived REST server, run Docker, execute arbitrary third-party skill code, or test external OTel/SIEM destinations. Passing tests demonstrate the current tested behavior, not independent proof of production security properties.
