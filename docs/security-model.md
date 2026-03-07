# Security Model

## The Deterministic Guarantee

Argus's core claim is that the security layer is inviolable: no LLM output, no adversarial prompt, and no agent configuration can bypass it. This guarantee holds because the security components are not part of the LLM's execution — they are gates that the runtime executes before and after every tool call in deterministic Python code.

The execution path through a tool call is:

```
agent requests tool call
    |
    v
SecurityGateway.pre_tool_call(agent_role, tool_name, tool_input)
    |-- Gate 1: PermissionEnforcer.enforce(role, tool_name)  [hard stop]
    |-- Gate 2: AuditLogger.send(pre_call event)            [hard stop, fail-closed]
    v
tool executes
    |
    v
SecurityGateway.post_tool_call(tool_output, skill_manifest)
    |-- Gate 3: PromptShield.scan(tool_output)              [hard stop]
    |-- Gate 4: SecretRedactor.redact(tool_output)          [soft block, run continues]
    |-- Gate 5: EgressChecker.check(...)                    [log-only in v1]
    |-- Gate 6: AuditLogger.send(post_call event)           [hard stop, fail-closed]
    v
clean output enters LLM context
```

The LLM receives the output only after it has passed Gates 3 and 4. It cannot influence what patterns Gate 3 scans for, because those are compiled at gateway startup. It cannot change the permission rules enforced by Gate 1, because those are loaded from config before the run starts. It cannot write to the audit log directly, because the log process communicates over a Unix domain socket that the agent process does not own.

The state machine reinforces this guarantee at the execution level: `TRANSITION_SEQUENCE` in `machine.py` is a Python list constant. No LLM output drives a state transition. The machine advances by index through the fixed sequence; any deviation (including cost abort) is triggered by deterministic code, not by parsing model output.

## Permission Enforcement (SEC-01)

### PolicyConfig and PolicyRule

Permissions are declared as a list of `PolicyRule` objects:

```python
from argus.security.permission.policy import PolicyConfig, PolicyRule

policy = PolicyConfig(rules=[
    PolicyRule(role="analyst",    tool="read_file",  effect="allow"),
    PolicyRule(role="analyst",    tool="search",     effect="allow"),
    PolicyRule(role="supervisor", tool="write_file", effect="allow"),
])
```

Or as a plain dict (coerced to `PolicyConfig` internally):

```python
from argus.security.gateway import GatewayConfig

config = GatewayConfig(permissions={
    "rules": [
        {"role": "analyst", "tool": "read_file", "effect": "allow"},
    ]
})
```

### Casbin RBAC Model

The enforcer uses Casbin with an in-memory RBAC model:

```
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = r.sub == p.sub && r.obj == p.obj && r.act == p.act
```

The policy effect `some(where (p.eft == allow))` means: a request is allowed only if at least one matching allow rule exists. There is no default-allow fallback. A role with no rules denies all tool calls.

The `act` field is always `"call"` — Argus only models the action of calling a tool. Write rules using `role` (subject), `tool` (object), and `"allow"` (effect).

### PolicyConfig Conversion

`PolicyConfig.to_casbin_csv()` converts rules to Casbin CSV format:

```python
policy = PolicyConfig(rules=[
    PolicyRule(role="analyst", tool="read_file", effect="allow"),
    PolicyRule(role="analyst", tool="search",    effect="allow"),
])
csv = policy.to_casbin_csv()
# "p, analyst, read_file, call\np, analyst, search, call"
```

Deny rules (`effect="deny"`) are currently ignored in the CSV conversion — the effect `some(where (p.eft == allow))` already denies by default. Explicit deny rules are reserved for future ABAC refinement.

### PermissionDeniedError

When `enforce()` blocks a call, it raises `PermissionDeniedError`:

```python
from argus.security.exceptions import PermissionDeniedError

try:
    gateway.pre_tool_call("analyst", "delete_file", {})
except PermissionDeniedError as e:
    print(e.gate)     # "permission"
    print(e.blocked)  # "delete_file"
    print(e.rule)     # "role=analyst tool=delete_file"
```

The exception propagates up through `StateMachine.run()`, which catches it, rolls back `context.artifacts` to the pre-run snapshot, and returns a `RunResult` with `success=False`.

### Permissive Mode

If `GatewayConfig.permissions` is `None` or the rules list is empty, the enforcer operates in permissive mode — all tool calls are allowed. Useful for development when permission enforcement is not yet configured.

## Prompt Injection Detection (SEC-05)

### Pattern Library

`PromptShield` ships with 14 OWASP LLM01:2025-aligned patterns compiled at startup:

```python
BUILTIN_PATTERNS = [
    r'ignore\s+(?:all\s+)?previous\s+instructions?',       # 1
    r'you\s+are\s+now\s+(?:in\s+)?developer\s+mode',       # 2
    r'system\s+override',                                   # 3
    r'reveal\s+(?:your\s+)?prompt',                        # 4
    r'disregard\s+(?:all\s+)?instructions?',               # 5
    r'forget\s+(?:all\s+)?previous\s+(?:instructions?|context)', # 6
    r'you\s+are\s+now\s+(?:free|allowed|permitted)\s+to',  # 7
    r'print\s+your\s+(?:system\s+)?instructions?',         # 8
    r'output\s+your\s+(?:full\s+)?(?:system\s+)?prompt',   # 9
    r'---BEGIN\s+(?:SYSTEM|INSTRUCTION)',                   # 10 - jailbreak markers
    r'SYSTEM\s*:\s*You\s+are',                             # 11 - system prompt leakage
    r'<\s*(?:system|instruction)\s*>',                     # 12 - XML/HTML tags
    r'\[SYSTEM\].*(?:ignore|override|bypass)',              # 13 - bracket-based tags
]
```

All patterns are compiled with `re.IGNORECASE | re.MULTILINE` and applied to normalized text.

### Unicode Normalization

Before pattern matching, the scanner strips zero-width Unicode obfuscation characters and collapses whitespace:

```python
def _normalize(self, text: str) -> str:
    # Strip zero-width spaces, joiners, non-joiners, BOM
    text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
```

This defeats common obfuscation techniques that insert invisible Unicode characters between letters of a trigger phrase.

### Custom Patterns

Add patterns via `GatewayConfig.prompt_shield_patterns`:

```python
gateway = SecurityGateway(
    config=GatewayConfig(prompt_shield_patterns=[
        r'exfiltrate\s+(?:all\s+)?data',
        r'send\s+(?:this\s+)?to\s+\S+\.com',
    ]),
    audit_logger=audit_logger,
)
```

Or instantiate `PromptShield` directly:

```python
from argus.security.prompt_shield.shield import PromptShield

shield = PromptShield(extra_patterns=[r'my_custom_pattern'])
shield.scan(tool_output)  # raises InjectionDetectedError if matched
```

### Handling InjectionDetectedError

When `post_tool_call` raises `InjectionDetectedError`, callers must substitute the placeholder before passing the output to the LLM:

```python
from argus.security.exceptions import InjectionDetectedError
from argus.security.prompt_shield.shield import PromptShield

try:
    clean_output = gateway.post_tool_call(tool_output)
except InjectionDetectedError:
    clean_output = PromptShield.PLACEHOLDER  # "[BLOCKED: injection detected]"
# pass clean_output to LLM context
```

The `StateMachine` catches this exception at the run level and triggers rollback. Tool-level handlers that catch it should use the placeholder.

## Secret Redaction (SEC-03)

### Pattern Coverage

`SecretRedactor` applies seven patterns in specificity order:

| Pattern ID | Pattern | Matches |
|------------|---------|---------|
| `openai_key` | `sk-(?:proj-)?[A-Za-z0-9\-_]{20,}` | OpenAI API keys |
| `github_token` | `gh[pousp]_[A-Za-z0-9]{32,}` | GitHub tokens (ghp_, ghs_, gho_, ghu_, ghs_) |
| `github_pat` | `github_pat_[A-Za-z0-9_]{36,}` | GitHub fine-grained PATs |
| `aws_access_key` | `AKIA[0-9A-Z]{16}` | AWS IAM Access Keys |
| `generic_api_key` | `(?i)(?:api[_-]?key\|secret[_-]?key\|...) =: \S{8,}` | Generic key=value pairs |
| `bearer_token` | `(?i)Bearer\s+[A-Za-z0-9\-._~+/]{20,}` | Authorization header tokens |
| `email` | `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` | Email addresses (PII) |

All matches are replaced with `[REDACTED]`. The original value is never stored; only the first 50 characters of the first match are recorded in the `SecurityEvent.blocked_value` for audit purposes.

### Soft Block Semantics

Redaction never raises. The run continues with sanitized text. This is by design: a secret leaking into a tool output should not crash the agent — it should be silently scrubbed and the incident logged.

```python
from argus.security.redactor.redactor import SecretRedactor

redactor = SecretRedactor()
clean = redactor.redact("key=AKIAIOSFODNN7EXAMPLE12345678 and sk-proj-abc123xyz789...")
# Returns: "key=[REDACTED] and [REDACTED]"
```

### Redaction in LLMRouter

`LLMRouter` applies redaction to `RunContext.task_input` before sending it to the LLM (SEC-03). Inject a `SecretRedactor` at construction:

```python
from argus.security.redactor.redactor import SecretRedactor

router = LLMRouter(
    config=model_config,
    tracker=tracker,
    redactor=SecretRedactor(),  # redacts task_input before every LLM call
)
```

If `redactor=None`, no redaction is applied — safe for unit tests with dummy data.

## Process-Level Skill Isolation (SEC-04)

### SkillIsolator

`SkillIsolator` runs skills in a subprocess with a stripped environment. The allowed environment keys are:

```python
ALLOWED_ENV_KEYS = {"PATH", "HOME", "PYTHONPATH", "PYTHONDONTWRITEBYTECODE"}
```

The subprocess receives a minimal environment:

```python
minimal_env = {
    "PATH": "/usr/bin:/bin",
    "HOME": "/tmp",
    "PYTHONPATH": skill_package_path,
    "PYTHONDONTWRITEBYTECODE": "1",
}
```

All other environment variables — including `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `AWS_SECRET_ACCESS_KEY`, and any other credentials — are stripped from the subprocess environment. A skill running through `SkillIsolator` cannot access parent-process secrets.

### v1.1 Upgrade Path

The v1 isolator provides env isolation, not syscall isolation. The interface is designed for a drop-in replacement:

```python
# v1: subprocess with stripped env
result = subprocess.run([sys.executable] + skill_cmd, env=minimal_env, ...)

# v1.1: Docker container (same SkillIsolator interface)
# subprocess.run(["docker", "run", "--rm", image_name] + skill_cmd, ...)
```

The `SkillLifecycleManager` accepts an injectable `SkillIsolator` instance, so upgrading to Docker isolation requires only swapping the isolator at construction time.

## Egress Control (SEC-06)

### Allowlist Enforcement

Skills declare `egress_allowlist` in their `skill.yaml`. The `EgressChecker` compares hostnames against this list and emits a `SecurityEvent` on violations.

```yaml
# skill.yaml
egress_allowlist:
  - "api.anthropic.com"
  - "api.openai.com"
```

The checker is called by `SecurityGateway.post_tool_call` for each declared hostname in the skill manifest:

```python
for hostname in skill_manifest.egress_allowlist:
    self._egress.check(hostname=hostname, skill_name=skill_name)
```

### v1 Log-Only Behavior

In v1, egress violations are logged but not blocked at the network layer. The `EgressViolationError` exception class exists in the hierarchy but is never raised by `EgressChecker.check()`.

The violation event is emitted to the security stream via the `event_sink` callback:

```python
SecurityEvent(
    gate=GateType.EGRESS,
    outcome="violation",
    tool_name=skill_name,
    blocked_value=hostname[:200],
    rule_triggered=f"not in allowlist: {sorted(self._allowlist)}",
    metadata={"allowlist": sorted(self._allowlist), "attempted_host": hostname},
)
```

### v1.1 Enforcement Path

When Docker container isolation is added (SBX-02), the egress checker will be updated to raise `EgressViolationError` and the container will enforce network policy at the OS level. The code is already structured for this transition:

```python
# v1:
# violations logged, no raise

# v1.1 (planned):
# raise EgressViolationError(gate="egress", blocked=hostname, rule="allowlist")
```

## Hash-Chained Audit Log (SEC-02)

### Chain Structure

Every audit log entry is a JSON object with a `prev_hash` field. The hash of entry N is computed over the canonical JSON (sorted keys, no whitespace) of the entire entry including its `prev_hash`. This forms a chain: modifying any entry invalidates all subsequent entries.

```python
# Each entry looks like:
{
    "event_type": "tool_call_pre",
    "agent_role": "analyst",
    "tool_name": "read_file",
    "prev_hash": "a3f2..."   # SHA-256 of the previous entry
}

# The hash stored for this entry (used as prev_hash in the next entry):
canonical = json.dumps(entry, sort_keys=True, separators=(",", ":"))
entry_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

The genesis hash (first entry's `prev_hash`) is 64 zero characters.

### Tamper Detection

Verify chain integrity with `verify_chain`:

```python
from argus.security.audit.chain import verify_chain

broken_lines = verify_chain("/path/to/audit.jsonl")
if broken_lines:
    print(f"Chain broken at lines: {broken_lines}")
else:
    print("Chain intact")
```

`verify_chain` reads the file line by line, re-derives each entry's hash, and checks it against the next entry's `prev_hash`. Any modification to any entry — including changing the `prev_hash` itself — will break the chain at that point.

### Separate Process Rationale

The audit logger runs as a separate process that listens on a Unix domain socket. The agent process sends log events over the socket; it does not have write access to the log file.

This separation matters because:
- A compromised agent process cannot delete or modify audit entries
- The agent cannot forge audit entries (it can only send to the socket; the log process controls what gets written)
- The audit chain is owned by a process with a separate UID in production

In v1, the CLI uses `MagicMock(spec=AuditLogger)` to satisfy the `SecurityGateway` contract without starting the daemon. v1.1 will auto-start the daemon as a subprocess of `argus run`.

To start the audit logger daemon manually:

```bash
python -m argus.security.audit.log_process /tmp/argus_audit.sock /var/log/argus/audit.jsonl
```

The agent then connects with:

```python
from argus.security.audit.logger import AuditLogger

audit = AuditLogger("/tmp/argus_audit.sock")
# The SecurityGateway uses audit.send({...}) for every pre/post tool call event
```

## Security Event Stream (OBS-04)

### Independence from Execution Trace

The security event stream is written to a separate JSONL file (`security.jsonl`) by `SecurityEventWriter`. It is completely independent of the execution trace — consuming the security stream does not require parsing the main trace.

Every gate that fires emits a `SecurityEvent`:

```python
class SecurityEvent(BaseModel):
    event_id:       str                # uuid4
    timestamp:      datetime           # UTC
    gate:           GateType           # permission | audit | redaction | sandbox | prompt_shield | egress | skill_lifecycle
    outcome:        str                # "blocked" | "allowed" | "redacted" | "violation"
    agent_role:     str | None = None
    tool_name:      str | None = None
    rule_triggered: str | None = None
    blocked_value:  str | None = None  # first 50 chars, never full secret
    metadata:       dict[str, Any]     # forward-compatible escape hatch
```

### GateType Values

| GateType | Emitted by | Outcomes |
|----------|------------|---------|
| `permission` | `PermissionEnforcer` | `blocked` |
| `audit` | `AuditLogger` | (internal) |
| `redaction` | `SecretRedactor` | `redacted` |
| `sandbox` | `SkillIsolator` | (planned) |
| `prompt_shield` | `PromptShield` | `blocked` |
| `egress` | `EgressChecker` | `violation` |
| `skill_lifecycle` | `SkillLifecycleManager` | `pending` \| `completed` \| `blocked` |

### Consuming the Security Stream

The security stream is valid JSONL — one `SecurityEvent` JSON per line. It can be tailed, ingested by a SIEM, or parsed with any JSON library:

```python
import json

with open("./runs/security.jsonl") as f:
    for line in f:
        event = json.loads(line)
        if event["gate"] == "permission" and event["outcome"] == "blocked":
            print(f"Blocked: {event['tool_name']} by {event['agent_role']}")
```

### SecurityEventWriter

`SecurityEventWriter` accepts `path=None` for a no-op mode:

```python
from argus.observability.security_stream import SecurityEventWriter

writer = SecurityEventWriter(Path("./runs/security.jsonl"))  # writes to file
writer = SecurityEventWriter(None)                           # no-op
```

When wired through `ObservabilityManager`, all security events from all gates are forwarded to the writer via `obs.on_security_event(event)`.

## Exception Hierarchy

All security exceptions inherit from `ArgusSecurityError`:

```
ArgusSecurityError(gate, blocked, rule)
├── PermissionDeniedError     — Gate 1: tool call denied by policy
├── InjectionDetectedError    — Gate 3: prompt injection pattern matched
├── EgressViolationError      — Gate 5: egress violation (raised in v1.1)
├── SkillIntegrityError       — Skill: SHA-256 hash mismatch
└── AuditUnavailableError     — Gate 2/6: audit socket unreachable (fail-closed)
```

`PermissionDeniedError`, `InjectionDetectedError`, and `SkillIntegrityError` are hard stops: they propagate to `StateMachine.run()`, which triggers rollback and returns `RunResult(success=False)`.

`AuditUnavailableError` is also a hard stop by design. Argus fails closed: if the audit log is unavailable, the agent stops. This prevents unaudited execution.

`EgressViolationError` exists in the hierarchy but is not raised in v1. It will be raised in v1.1 when network enforcement is added.
