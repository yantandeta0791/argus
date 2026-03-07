# Configuration Reference

Argus is configured through a single `argus.yaml` file at the project root. The file controls model selection, spend caps, and (programmatically) the security gateway. API keys are never stored in `argus.yaml` — they must come from environment variables.

## argus.yaml Structure

```yaml
models:
  default: "anthropic/claude-sonnet-4-6"
  states:
    PLAN:    "anthropic/claude-opus-4-6"
    EXECUTE: "anthropic/claude-sonnet-4-6"
    VERIFY:  "anthropic/claude-sonnet-4-6"
    REFLECT: "anthropic/claude-opus-4-6"
    COMMIT:  null
  tasks: {}

spend:
  per_task_usd:    null
  per_session_usd: null
  per_day_usd:     null
```

The file is loaded with `yaml.safe_load` — no arbitrary Python execution from YAML.

```python
from argus.llm.config import load_config

config = load_config("argus.yaml")   # or load_config(Path("/abs/path/argus.yaml"))
# Returns a fresh ModelConfig on every call — no singleton caching
```

## ModelConfig

`ModelConfig` is a dataclass with three fields plus an embedded `SpendConfig`.

```python
@dataclass
class ModelConfig:
    default: str = "anthropic/claude-sonnet-4-6"
    states:  dict[str, str | None] = field(default_factory=dict)
    tasks:   dict[str, str]        = field(default_factory=dict)
    spend:   SpendConfig           = field(default_factory=SpendConfig)
```

### `default`

The fallback model string used when no state or task override matches. Any LiteLLM-compatible model string is valid. Provider is encoded in the prefix:

```yaml
# Anthropic (default)
default: "anthropic/claude-sonnet-4-6"

# OpenAI
default: "openai/gpt-4o"

# Azure OpenAI
default: "azure/my-deployment-name"

# OpenAI-compatible (custom base URL, set via OPENAI_API_BASE env var)
default: "openai/my-local-model"
```

### `states`

Per-state model selection. Maps `TaskState` name to a model string or `null`.

Valid keys: `PLAN`, `EXECUTE`, `VERIFY`, `REFLECT`, `COMMIT`.

`null` means no LLM call for that state — the state handler executes without invoking the router. Use this for deterministic states like `COMMIT`.

```yaml
states:
  PLAN:    "anthropic/claude-opus-4-6"    # reasoning-heavy, use Opus
  EXECUTE: "anthropic/claude-sonnet-4-6"  # implementation, Sonnet is sufficient
  VERIFY:  "anthropic/claude-sonnet-4-6"  # checking, Sonnet is sufficient
  REFLECT: "anthropic/claude-opus-4-6"    # synthesis, use Opus
  COMMIT:  null                            # deterministic code only, no LLM call
```

### `tasks`

Per-task model overrides. Maps `RunContext.task_id` to a model string. Has the highest resolution priority.

```yaml
tasks:
  summarize:       "anthropic/claude-haiku-3-5"  # fast + cheap for summaries
  code_generation: "anthropic/claude-opus-4-6"   # best model for code
  triage:          "anthropic/claude-haiku-3-5"
```

### Model Resolution Priority

For any given LLM call, the model is resolved in this order:

1. `tasks[context.task_id]` — per-task override (highest priority)
2. `states[str(context.current_state)]` — per-state config (may be `null`)
3. `default` — fallback

When the resolved model is `None` (explicit `null` in states), the router returns `{}` immediately without making an API call.

## SpendConfig

`SpendConfig` declares hard spend caps. When any cap is exceeded, `SpendTracker.over_budget()` returns `True` and the state machine fires a deterministic `ABORT` transition.

```python
@dataclass
class SpendConfig:
    per_task_usd:    float | None = None
    per_session_usd: float | None = None
    per_day_usd:     float | None = None
```

`None` means no cap for that dimension.

### Cap Semantics

All caps are hard stops — the state machine calls `cost_hook()` before every state transition. When `over_budget()` returns `True`, the machine immediately returns a `RunResult` with `final_state=ABORT` and `success=False`. The cap is checked before the state's handler runs, so a state that would exceed the cap is never started.

| Cap | Scope | Reset |
|-----|-------|-------|
| `per_task_usd` | Single `StateMachine.run()` call | Per run |
| `per_session_usd` | Single `SpendTracker` instance | Per run (fresh tracker per run) |
| `per_day_usd` | Rolling daily total | Loaded from SQLite at startup |

The `per_day_usd` cap requires the memory subsystem. The CLI loads the day's cumulative spend from SQLite before constructing `SpendTracker`:

```python
tracker = SpendTracker(model_config.spend, daily_spend_usd=loaded_from_sqlite)
```

Cost is tracked in USD using LiteLLM's `response._hidden_params["response_cost"]`.

### SpendConfig in argus.yaml

```yaml
spend:
  per_task_usd:    0.50    # halt after $0.50 per task
  per_session_usd: 5.00    # halt after $5.00 per session
  per_day_usd:     20.00   # halt after $20.00 across all runs today
```

## GatewayConfig

`GatewayConfig` is constructed in code (not read from `argus.yaml`). Pass it to `SecurityGateway` at startup.

```python
from argus.security.gateway import SecurityGateway, GatewayConfig

@dataclass
class GatewayConfig:
    permissions:             Optional[PolicyConfig] = None
    prompt_shield_patterns:  list[str]              = field(default_factory=list)
    egress_allowlist:        list[str]              = field(default_factory=list)
```

### `permissions`

A `PolicyConfig` dict or object declaring RBAC rules. `None` or an empty rules list puts the enforcer in permissive mode — all tool calls are allowed.

```python
GatewayConfig(permissions={
    "rules": [
        {"role": "analyst",    "tool": "read_file",   "effect": "allow"},
        {"role": "analyst",    "tool": "search",      "effect": "allow"},
        {"role": "supervisor", "tool": "write_file",  "effect": "allow"},
        {"role": "supervisor", "tool": "delete_file", "effect": "allow"},
    ]
})
```

The `PolicyConfig` model:

```python
class PolicyRule(BaseModel):
    role:   str
    tool:   str
    effect: Literal["allow", "deny"] = "allow"

class PolicyConfig(BaseModel):
    rules: list[PolicyRule] = []
```

Rules are enforced with Casbin RBAC. The enforcer uses `some(where (p.eft == allow))` policy effect, meaning a tool call is allowed only if an explicit allow rule exists for the role. No allow rule means deny — there is no default-allow fallback.

### `prompt_shield_patterns`

A list of additional regex patterns to add to the PromptShield battery. These are compiled once at `SecurityGateway` construction time with `re.IGNORECASE | re.MULTILINE`.

```python
GatewayConfig(prompt_shield_patterns=[
    r'exfiltrate\s+data',
    r'send\s+to\s+external\s+server',
])
```

### `egress_allowlist`

A list of hostnames that skills are allowed to contact. Used by `EgressChecker.check()`. In v1, violations are logged but not blocked at the network level.

```python
GatewayConfig(egress_allowlist=[
    "api.anthropic.com",
    "api.openai.com",
])
```

## ObsConfig

`ObsConfig` is passed to `ObservabilityManager`. All paths default to `None`; a `None` path disables that sink.

```python
@dataclass
class ObsConfig:
    trace_path:           Path | None = None   # JSONL execution trace
    security_stream_path: Path | None = None   # JSONL security event stream
    otel_spans_path:      Path | None = None   # JSONL OTel spans
    service_name:         str        = "argus"
    enabled:              bool       = True
```

`enabled=False` is a complete no-op: no files are created, no I/O occurs. The manager still accepts `on_*` calls without error — useful for test environments that do not want trace output.

```python
from argus.observability.manager import ObservabilityManager, ObsConfig
from pathlib import Path

# Production: write all sinks
obs = ObservabilityManager(ObsConfig(
    trace_path=Path("./runs/trace.jsonl"),
    security_stream_path=Path("./runs/security.jsonl"),
    otel_spans_path=Path("./runs/spans.jsonl"),
    service_name="my-agent",
    enabled=True,
))

# Test: no-op
obs = ObservabilityManager(ObsConfig(enabled=False))
```

## MemoryConfig

`MemoryConfig` is passed to `MemoryManager`. The `db_path` field defaults to `~/.argus/state.db`.

```python
@dataclass
class MemoryConfig:
    db_path: Path | None = None

    def resolved_path(self) -> Path:
        # Priority: explicit db_path > $XDG_DATA_HOME/argus/state.db > ~/.argus/state.db
        ...
```

The `argus run` CLI scopes `db_path` to the `--trace-dir` to keep runs hermetic:

```python
memory = MemoryManager(MemoryConfig(db_path=trace_dir / "memory.db"))
```

## Example Configurations

### Development

Cheap models, no spend caps, observability disabled to avoid trace noise:

```yaml
models:
  default: "anthropic/claude-haiku-3-5"
  states:
    PLAN:    "anthropic/claude-haiku-3-5"
    EXECUTE: "anthropic/claude-haiku-3-5"
    VERIFY:  "anthropic/claude-haiku-3-5"
    REFLECT: "anthropic/claude-haiku-3-5"
    COMMIT:  null
  tasks: {}

spend:
  per_task_usd:    null
  per_session_usd: null
  per_day_usd:     null
```

In code, disable observability:

```python
obs = ObservabilityManager(ObsConfig(enabled=False))
```

### Production

Best-available models for reasoning states, enforced spend caps, full observability:

```yaml
models:
  default: "anthropic/claude-sonnet-4-6"
  states:
    PLAN:    "anthropic/claude-opus-4-6"
    EXECUTE: "anthropic/claude-sonnet-4-6"
    VERIFY:  "anthropic/claude-sonnet-4-6"
    REFLECT: "anthropic/claude-opus-4-6"
    COMMIT:  null
  tasks:
    triage:    "anthropic/claude-haiku-3-5"
    summarize: "anthropic/claude-haiku-3-5"

spend:
  per_task_usd:    1.00
  per_session_usd: 10.00
  per_day_usd:     50.00
```

### Cost-Constrained

All states use Haiku, tight per-task cap, daily rollup enforced:

```yaml
models:
  default: "anthropic/claude-haiku-3-5"
  states:
    PLAN:    "anthropic/claude-haiku-3-5"
    EXECUTE: "anthropic/claude-haiku-3-5"
    VERIFY:  "anthropic/claude-haiku-3-5"
    REFLECT: "anthropic/claude-haiku-3-5"
    COMMIT:  null
  tasks: {}

spend:
  per_task_usd:    0.05
  per_session_usd: 0.50
  per_day_usd:     2.00
```

### OpenAI Provider

Provider swap requires only changing model string prefixes:

```yaml
models:
  default: "openai/gpt-4o-mini"
  states:
    PLAN:    "openai/gpt-4o"
    EXECUTE: "openai/gpt-4o-mini"
    VERIFY:  "openai/gpt-4o-mini"
    REFLECT: "openai/gpt-4o"
    COMMIT:  null
  tasks: {}

spend:
  per_task_usd: 0.50
```

Set `OPENAI_API_KEY` in the environment instead of `ANTHROPIC_API_KEY`.
