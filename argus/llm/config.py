"""
LLM config layer for Argus.

ModelConfig   -- per-state and per-task model selection (COST-01, COST-02)
SpendConfig   -- per-task / per-session / per-day spend caps (COST-03)
load_config() -- reads argus.yaml using yaml.safe_load (PyYAML, already in deps)

Design: fresh ModelConfig per call -- no singleton caching. Simple and testable.
API keys never stored here -- must come from environment variables (ANTHROPIC_API_KEY).
"""
from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from pathlib import Path


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
