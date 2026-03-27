"""
LLM config layer for Argus.

ModelConfig   -- per-state and per-task model selection (COST-01, COST-02)
SpendConfig   -- per-task / per-session / per-day spend caps (COST-03)
load_config() -- reads argus.yaml using yaml.safe_load (PyYAML, already in deps)

Design: fresh ModelConfig per call -- no singleton caching. Simple and testable.
API keys never stored here -- must come from environment variables (ANTHROPIC_API_KEY).
"""

from __future__ import annotations

import os
import re
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from pydantic import BaseModel, field_validator, ValidationError


@dataclass
class SpendConfig:
    """Hard spend caps. None means no cap for that dimension."""

    per_task_usd: float | None = None
    per_session_usd: float | None = None
    per_day_usd: float | None = None


@dataclass
class ModelConfig:
    """Model selection configuration.

    Resolution priority (COST-01, COST-02):
      1. tasks[task_id]  -- per-task override (highest priority)
      2. states[state]   -- per-state config
      3. default         -- fallback

    None as a state value means no LLM call for that state (e.g., COMMIT).
    """

    default: str = "anthropic/claude-sonnet-4-6"
    states: dict[str, str | None] = field(default_factory=dict)
    tasks: dict[str, str] = field(default_factory=dict)
    spend: SpendConfig = field(default_factory=SpendConfig)


def load_config(path: Path | str = "argus.yaml") -> ModelConfig:
    """Read argus.yaml and return a ModelConfig instance.

    Uses yaml.safe_load -- never executes arbitrary Python from YAML.
    Returns fresh ModelConfig per call (no singleton).
    """
    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    models_raw = raw.get("models", {}) or {}
    spend_raw = raw.get("spend", {}) or {}

    # Build SpendConfig -- skip None values so dataclass defaults apply
    spend_kwargs = {k: v for k, v in spend_raw.items() if v is not None}
    spend = SpendConfig(**spend_kwargs)

    return ModelConfig(
        default=models_raw.get("default", "anthropic/claude-sonnet-4-6"),
        states=models_raw.get("states", {}) or {},
        tasks=models_raw.get("tasks", {}) or {},
        spend=spend,
    )


def load_hitl_config(raw: dict):
    """Parse tools: and hitl: YAML sections into HITLConfig.

    Accepts the raw dict from yaml.safe_load(argus.yaml).
    Returns HITLConfig if any tools require approval or a timeout is set.
    Returns None if neither section is present with relevant keys.

    HITLConfig is imported lazily to avoid circular imports between argus.llm
    and argus.security.
    """
    tools_raw = raw.get("tools", {}) or {}
    hitl_raw = raw.get("hitl", {}) or {}
    require_approval = {
        name: True
        for name, cfg in tools_raw.items()
        if (cfg or {}).get("require_approval")
    }
    timeout = hitl_raw.get("timeout_seconds", None)
    if not require_approval and timeout is None:
        return None
    from argus.security.hitl import HITLConfig  # lazy import — avoids circular dep
    return HITLConfig(require_approval=require_approval, timeout_seconds=timeout)


class SecretsConfig(BaseModel):
    """Validated secrets detection patterns.

    Each pattern must be a valid Python regex — invalid patterns raise
    ConfigValidationError at construction time (POLC-05).
    """

    patterns: list[str] = []

    @field_validator("patterns", mode="before")
    @classmethod
    def validate_regex_patterns(cls, v):
        for pattern in (v or []):
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f"Invalid regex pattern {pattern!r}: {exc}") from exc
        return v


def load_rbac_config(raw: dict):
    """Parse rbac: YAML section into PolicyConfig.

    Returns None when the section is absent or the roles dict is empty.
    Lazy-imports PolicyConfig/PolicyRule to avoid circular imports.

    POLC-01: role-centric YAML → flat PolicyRule list with allow/deny effects.
    """
    rbac_raw = raw.get("rbac", {}) or {}
    roles_raw = (rbac_raw.get("roles") or {})
    if not roles_raw:
        return None
    from argus.security.permission.policy import PolicyConfig, PolicyRule  # lazy import
    rules = []
    for role_name, role_cfg in roles_raw.items():
        role_cfg = role_cfg or {}
        for tool in (role_cfg.get("allow") or []):
            rules.append(PolicyRule(role=role_name, tool=tool, effect="allow"))
        for tool in (role_cfg.get("deny") or []):
            rules.append(PolicyRule(role=role_name, tool=tool, effect="deny"))
    return PolicyConfig(rules=rules)


def load_secrets_config(raw: dict) -> SecretsConfig:
    """Parse secrets: YAML section into SecretsConfig.

    Returns SecretsConfig(patterns=[]) when the section is absent.
    Raises ConfigValidationError if any pattern is not a valid regex (POLC-05).
    """
    secrets_raw = raw.get("secrets", {}) or {}
    try:
        return SecretsConfig(patterns=secrets_raw.get("patterns") or [])
    except ValidationError as exc:
        from argus.security.exceptions import ConfigValidationError  # lazy import
        raise ConfigValidationError(f"Invalid secrets config in argus.yaml:\n{exc}") from exc


def load_egress_config(raw: dict) -> list[str]:
    """Parse egress: YAML section into an allowlist of hostnames/URLs.

    Returns [] when the section is absent.

    POLC-03: egress.allowlist → list[str].
    """
    egress_raw = raw.get("egress", {}) or {}
    return list(egress_raw.get("allowlist") or [])


def load_spend_profiles(raw: dict, active_profile: str | None = None) -> SpendConfig:
    """Parse spend: YAML section, optionally selecting a named profile.

    Profile selection priority:
      1. active_profile argument (explicit, highest priority)
      2. ARGUS_SPEND_PROFILE environment variable
      3. Flat spend keys (backward-compatible, no profiles)

    Raises ConfigValidationError if the selected profile name is not found.

    POLC-04: spend.profiles.<name> → SpendConfig.
    """
    from argus.security.exceptions import ConfigValidationError  # lazy import
    spend_raw = raw.get("spend", {}) or {}
    profiles = spend_raw.get("profiles", {}) or {}
    profile_name = active_profile or os.environ.get("ARGUS_SPEND_PROFILE")
    if profile_name:
        if profile_name not in profiles:
            raise ConfigValidationError(
                f"ARGUS_SPEND_PROFILE={profile_name!r} not found in argus.yaml "
                f"spend.profiles. Available: {sorted(profiles)}"
            )
        profile_raw = profiles[profile_name]
    else:
        profile_raw = {k: v for k, v in spend_raw.items() if k != "profiles"}
    spend_kwargs = {k: v for k, v in (profile_raw or {}).items() if v is not None}
    return SpendConfig(**spend_kwargs)
