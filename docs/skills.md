# Skill Development Guide

Skills are the unit of capability in Argus. A skill is a Python package that ships with a `skill.yaml` manifest declaring exactly what it is allowed to do. Argus enforces the manifest through a seven-stage lifecycle; skills that do not pass verification are never executed.

## What is a Skill Manifest?

Every skill directory must contain a `skill.yaml` file. Argus loads this file at install time, validates it with Pydantic, and uses it to enforce permissions and isolation throughout the skill's execution.

### skill.yaml Fields

```yaml
# Required fields
name: my-scanner              # Unique skill identifier (string)
version: "1.0.0"              # Semantic version (string)
description: "..."            # Human-readable description (string)
trust_tier: community         # builtin | verified | community | untrusted
permissions: ["read_file"]    # List of tool names this skill may call
content_hash: "sha256:<64 hex chars>"  # SHA-256 hash of skill source files

# Optional fields (defaults shown)
blast_radius: local           # none | local | network | system (default: none)
data_access: []               # List of data source labels (default: [])
egress_allowlist: []          # Hostnames skill may contact (default: [])
timeout_s: 30.0               # Execution timeout in seconds (default: 30.0)
idempotent: true              # Whether repeated execution is safe (default: true)
```

### Field Reference

**`name`** (required, string)

Unique identifier for the skill. Used as the registry key. Must be unique across all installed skills.

**`version`** (required, string)

Semantic version string. Informational in v1; used for dependency resolution in future versions.

**`description`** (required, string)

Human-readable description of the skill's purpose.

**`trust_tier`** (required, `TrustTier` enum)

Determines the permission ceiling and sandbox strictness. See [Trust Tiers](#trust-tiers) below.

**`permissions`** (required, `list[str]`)

Explicit list of tool names this skill may invoke. Wildcard `"*"` is rejected by Security Audit rule SA-004. An empty list means the skill calls no tools directly.

**`content_hash`** (required, string)

SHA-256 hash of the skill's source files, prefixed with `"sha256:"`. Must be exactly `"sha256:"` followed by 64 lowercase hex characters. The `skill.yaml` file itself is excluded from the hash (chicken-and-egg: the manifest declares the hash but cannot be part of what is hashed).

Compute the hash with:

```python
from pathlib import Path
from argus.skills.hasher import compute_content_hash

hash_value = compute_content_hash(Path("./my_skill"))
# Returns: "sha256:a3f2c1..."
```

**`blast_radius`** (optional, `BlastRadius` enum, default: `none`)

Maximum impact scope of the skill:

| Value | Meaning |
|-------|---------|
| `none` | Read-only, no external effects |
| `local` | Modifies local filesystem only |
| `network` | Makes network calls |
| `system` | May affect system-level resources |

Security Audit rule SA-003 raises a WARNING if `blast_radius` is `network` or `system` but `egress_allowlist` is empty.

**`data_access`** (optional, `list[str]`, default: `[]`)

Descriptive labels for data sources the skill accesses (e.g., `"filesystem"`, `"database"`, `"environment"`). Informational in v1; used for audit reporting.

**`egress_allowlist`** (optional, `list[str]`, default: `[]`)

Hostnames the skill is allowed to contact. The `EgressChecker` logs violations against this list. In v1, violations are log-only. In v1.1, violations will raise `EgressViolationError`.

**`timeout_s`** (optional, float, default: `30.0`)

Execution timeout in seconds. `SkillIsolator` passes this to `subprocess.run(timeout=...)`. Security Audit rule SA-007 warns if this exceeds 300 seconds.

**`idempotent`** (optional, bool, default: `true`)

Whether repeated execution produces the same result. `ToolRunner` does not retry non-idempotent tools on ambiguous failures (TOOL-04). Security Audit rule SA-006 warns if `idempotent=false` combined with `blast_radius=network`.

## Trust Tiers

Trust tier determines the permission ceiling enforced by Argus.

### `builtin`

Reserved for skills that ship inside the `argus/skills/` source tree. Only code in the official Argus package may declare this tier. If a skill outside `argus/skills/` declares `trust_tier: builtin`, `SkillIntegrityError` is raised at install time and the skill is rejected.

The three built-in skills (`security-audit`, `owasp-top10`, `credential-scanner`) all use this tier.

### `verified`

For third-party skills that have undergone manual review. The verification process is defined outside Argus in v1. This tier signals elevated trust and reduced sandbox strictness (full enforcement in v1.1 when Docker isolation is added).

### `community`

The default tier for open-source community skills. Standard trust; all lifecycle enforcement applies. Use this for skills you ship publicly but have not put through a formal review process.

### `untrusted`

For unknown or unreviewed skills. Maximum sandbox strictness. Use this tier when loading skills from untrusted sources.

### Tier Enforcement

Trust tier is validated by `validate_trust_tier` at install time:

```python
from pathlib import Path
from argus.skills.manifest import load_manifest, validate_trust_tier

manifest = load_manifest(Path("./my_skill"))
validate_trust_tier(manifest, Path("./my_skill"))
# Raises SkillIntegrityError if trust_tier=builtin and skill is outside argus/skills/
```

## Blast Radius Levels

Blast radius declares the maximum impact scope. It is used by the security audit scanner and informs sandbox configuration.

| Level | Description | Security Audit Rule |
|-------|-------------|---------------------|
| `none` | No side effects; read-only access | No additional checks |
| `local` | Modifies local files or state | No additional checks |
| `network` | Makes outbound network calls | SA-003: requires egress_allowlist |
| `system` | Affects system-level resources (processes, kernel state) | SA-003: requires egress_allowlist |

Skills with `blast_radius: system` will be subject to the strictest sandbox settings in v1.1 (gVisor isolation).

## Writing a New Skill

This walkthrough creates a `file-scanner` skill that scans a directory for world-writable files.

### Step 1: Create the skill directory

```
my_skills/
└── file_scanner/
    ├── __init__.py
    └── skill.yaml
```

### Step 2: Write the skill code

```python
# my_skills/file_scanner/__init__.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ScanResult:
    world_writable: list[str] = field(default_factory=list)
    scanned_count: int = 0


def run(target_dir: str) -> ScanResult:
    """Scan target_dir for world-writable files."""
    result = ScanResult()
    for path in Path(target_dir).rglob("*"):
        if path.is_file():
            result.scanned_count += 1
            mode = path.stat().st_mode
            if mode & 0o002:  # world-writable bit
                result.world_writable.append(str(path))
    return result
```

### Step 3: Compute the content hash

```python
from pathlib import Path
from argus.skills.hasher import compute_content_hash

hash_value = compute_content_hash(Path("./my_skills/file_scanner"))
print(hash_value)
# sha256:a3f2c1d4e5...
```

### Step 4: Write skill.yaml

```yaml
name: file-scanner
version: "1.0.0"
description: "Scans a directory for world-writable files"
trust_tier: community
permissions: []
blast_radius: local
data_access: ["filesystem"]
egress_allowlist: []
timeout_s: 30.0
idempotent: true
content_hash: "sha256:a3f2c1d4e5..."  # from step 3
```

### Step 5: Verify the manifest

```bash
argus scan ./my_skills/file_scanner
# No issues found.
```

### Step 6: Run the skill through the lifecycle

```python
from pathlib import Path
from argus.skills.lifecycle import SkillLifecycleManager

manager = SkillLifecycleManager()
result = manager.run_lifecycle(Path("./my_skills/file_scanner"))
print(result["success"])        # True
print(result["trust_tier"])     # "community"
print(result["stages_completed"])  # ["install", "verify", "sandbox", "execute", "monitor", "report", "revoke"]
```

### Step 7: Update the hash after code changes

Any time the skill source changes, recompute and update `content_hash` in `skill.yaml`. If the hash does not match, `SkillLifecycleManager` raises `SkillIntegrityError` at the VERIFY stage.

```python
from pathlib import Path
from argus.skills.hasher import compute_content_hash

new_hash = compute_content_hash(Path("./my_skills/file_scanner"))
# Update skill.yaml:content_hash to new_hash
```

## Using the Built-in Skills

### Security Audit Skill

Scans a skill directory for manifest misconfigurations. Implements rules SA-001 through SA-007.

```python
from pathlib import Path
from argus.skills.security_audit import run as audit_run
from argus.skills.security_audit.findings import AuditReport, Finding, Severity

report: AuditReport = audit_run(Path("./my_skill"))

print(report.target)       # "./my_skill"
print(report.passed)       # True if no ERROR or CRITICAL findings
print(report.scanned_at)   # ISO 8601 timestamp

for finding in report.findings:
    print(finding.rule_id)      # "SA-001" through "SA-007"
    print(finding.severity)     # Severity.INFO | WARNING | ERROR | CRITICAL
    print(finding.message)      # human-readable description
    print(finding.location)     # "skill.yaml:field_name"
    print(finding.remediation)  # how to fix it
```

**Rules:**

| Rule | Severity | Condition |
|------|----------|-----------|
| SA-001 | ERROR | `skill.yaml` missing or fails Pydantic validation |
| SA-002 | ERROR | `trust_tier=builtin` but skill is outside `argus/skills/` |
| SA-003 | WARNING | `blast_radius` is `network` or `system` but `egress_allowlist` is empty |
| SA-004 | ERROR | `"*"` in `permissions` list |
| SA-005 | ERROR | `content_hash` format invalid (triggered via SA-001 path) |
| SA-006 | WARNING | `idempotent=false` with `blast_radius=network` |
| SA-007 | WARNING | `timeout_s > 300` |

SA-001 short-circuits: if the manifest cannot be loaded, no further rules run.

The `argus scan` CLI delegates to this skill and renders findings as a Rich table:

```bash
argus scan ./my_skill            # text output
argus scan ./my_skill --format json  # JSON output
```

### OWASP Agentic Top 10 Skill

Tests an agent configuration dict against all 10 OWASP Agentic Security Initiative categories (ASI01–ASI10).

```python
from argus.skills.owasp_top10 import run as owasp_run
from argus.skills.owasp_top10.report import OwaspReport, CategoryResult

agent_config = {
    "permissions": ["read_file", "search"],
    "spend_cap": 5.00,
    "audit_logging": True,
    "tool_validation": True,
}

report: OwaspReport = owasp_run(agent_config)

print(report.passed_count)   # number of categories passing
print(report.failed_count)   # number of categories failing
print(report.coverage_pct)   # percentage passing (0.0–100.0)
print(report.generated_at)   # ISO 8601 timestamp

for category in report.categories:
    print(category.category_id)  # "ASI01" through "ASI10"
    print(category.name)         # category name
    print(category.passed)       # True | False
    print(category.details)      # explanation
```

The skill checks are heuristic — they inspect the config dict for presence of security controls. A sparse or empty config dict will fail most checks. Checks use `.get()` with safe defaults, so partial configs are safe to pass.

**Categories:**

| ID | Name |
|----|------|
| ASI01 | Excessive Agency |
| ASI02 | Prompt Injection Exposure |
| ASI03 | Unbounded Resource Consumption |
| ASI04 | Tool Call Governance |
| ASI05 | Supply Chain Integrity |
| ASI06 | Sensitive Data Handling |
| ASI07 | Missing Cost Controls |
| ASI08 | Memory Poisoning |
| ASI09 | Identity Confusion |
| ASI10 | Inadequate Audit Logging |

The demo uses this skill to check for ASI07 (no cost cap configured):

```python
report = owasp_run({})  # empty config — no caps, no permissions
asi07 = next(c for c in report.categories if c.category_id == "ASI07")
print(asi07.passed)  # False — no cost cap declared
```

### Credential Scanner Skill

Detects exposed API keys, tokens, and secrets in any string or dict.

```python
from argus.skills.credential_scanner import run as scan_run
from argus.skills.credential_scanner.report import ScanReport, CredentialFinding

# Scan a string
report: ScanReport = scan_run("my_key = AKIAIOSFODNN7EXAMPLE12345678")

# Scan a dict (serialized to JSON first)
report = scan_run({"config": {"api_key": "sk-proj-abc123xyz789..."}})

print(report.clean)          # False if any CRITICAL or HIGH findings
print(report.scanned_chars)  # number of characters scanned
print(report.scanned_at)     # ISO 8601 timestamp

for finding in report.findings:
    print(finding.credential_type)  # "aws_access_key", "openai_key", etc.
    print(finding.severity)         # "CRITICAL" | "HIGH" | "WARNING"
    print(finding.match)            # redacted: "AKIA****"
    print(finding.location)         # "line 1"
    print(finding.pattern_id)       # "CS-001" through "CS-007"
```

**Pattern IDs:**

| ID | Type | Example Match |
|----|------|---------------|
| CS-001 | OpenAI API key | `sk-proj-...` |
| CS-002 | Anthropic API key | `sk-ant-...` |
| CS-003 | AWS Access Key | `AKIA...` |
| CS-004 | GCP credential | service account JSON patterns |
| CS-005 | GitHub token | `ghp_...`, `ghs_...`, etc. |
| CS-006 | Slack token | `xoxb-...`, `xoxp-...` |
| CS-007 | Generic Bearer token | `Bearer <20+ chars>` |

`report.clean` is `True` only if all findings have severity `"WARNING"`. Any `"CRITICAL"` or `"HIGH"` finding sets `clean=False`.

## Skill Lifecycle Stages

Every skill passes through seven deterministic stages:

```
Install → Verify → Sandbox → Execute → Monitor → Report → Revoke
```

### Stage Descriptions

**Install**: Load and validate `skill.yaml` with Pydantic. Validate trust tier. Register skill in `SkillRegistry`.

**Verify**: Compute SHA-256 hash of skill source files and compare against `content_hash` in the manifest. Raises `SkillIntegrityError` on mismatch. This is the integrity gate — no tampered skill proceeds past this stage.

**Sandbox**: Configure isolation parameters based on trust tier and blast radius. In v1, logs the configuration. In v1.1, this stage will apply Docker container constraints.

**Execute**: Run the skill via `SkillIsolator` (subprocess with stripped environment). Captures stdout. Raises `RuntimeError` on non-zero exit code.

**Monitor**: Collect metadata: skill name, trust tier, timestamp, execution result. Passively logs; does not interfere with execution.

**Report**: Produce structured result dict with `skill_name`, `success`, `trust_tier`, `stages_completed`, and `metrics`.

**Revoke**: Remove the skill from `SkillRegistry`. Always runs — either as the normal final stage or as cleanup on failure. Guarantees no partial installs are left behind.

### Cleanup Guarantee

If any stage fails, `Revoke` runs automatically:

```python
try:
    manager.run_lifecycle(skill_dir)
except SkillIntegrityError as e:
    # Revoke already ran — registry is clean
    print(f"Skill rejected at VERIFY: {e.blocked}")
```

### Security Events per Stage

Every stage transition emits a `SecurityEvent` with `gate=GateType.SKILL_LIFECYCLE`. The `metadata` dict includes the `stage` name and `trust_tier`:

```json
{
  "gate": "skill_lifecycle",
  "outcome": "completed",
  "tool_name": "my-scanner",
  "metadata": {
    "stage": "verify",
    "trust_tier": "community"
  }
}
```

A `blocked` outcome at the VERIFY stage indicates a hash mismatch and is always logged to the security stream.

### Injecting Custom Lifecycle Dependencies

`SkillLifecycleManager` accepts injectable dependencies for testing and extension:

```python
from argus.skills.lifecycle import SkillLifecycleManager
from argus.skills.registry import SkillRegistry
from argus.security.sandbox.isolator import SkillIsolator
from argus.security.events import SecurityEvent

events: list[SecurityEvent] = []

manager = SkillLifecycleManager(
    isolator=SkillIsolator(),              # default: SkillIsolator()
    registry=SkillRegistry(),             # default: SkillRegistry()
    event_sink=lambda e: events.append(e), # optional: collect events
)
result = manager.run_lifecycle(Path("./my_skill"))
print(len(events))  # number of lifecycle events emitted
```

## SkillRegistry

`SkillRegistry` is an in-memory dict of installed skills. It is populated by the `Install` stage and cleared by the `Revoke` stage.

```python
from argus.skills.registry import SkillRegistry
from argus.skills.manifest import SkillManifest

registry = SkillRegistry()
registry.install(manifest)           # add skill to registry
manifests = registry.list()          # returns list copy (safe iteration)
registry.revoke("my-scanner")        # remove by name
```

The registry uses a list-copy return pattern for `list()` to prevent concurrent modification during iteration.

## Hasher

The `SkillHasher` module provides two functions for content hash management:

```python
from pathlib import Path
from argus.skills.hasher import compute_content_hash, verify_content_hash

# Compute hash of all Python source files in a directory
# (skill.yaml is excluded from the hash)
hash_str = compute_content_hash(Path("./my_skill"))
# Returns: "sha256:a3f2c1..."

# Verify a stored hash against the current directory contents
matches = verify_content_hash(Path("./my_skill"), "sha256:a3f2c1...")
# Returns: True if current hash matches, False if files have changed
```

Both functions exclude `skill.yaml` from the hash computation. The hash is stable across platforms as long as file contents are identical; file permissions and timestamps do not affect it.
