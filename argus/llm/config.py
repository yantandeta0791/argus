"""
LLM config layer: ModelConfig, SpendConfig dataclasses and load_config().
Reads argus.yaml and provides model selection and spend cap configuration.
Implemented in Plan 03-02.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SpendConfig:
    per_task_usd: float | None = None
    per_session_usd: float | None = None
    per_day_usd: float | None = None


@dataclass
class ModelConfig:
    default: str = "anthropic/claude-sonnet-4-6"
    states: dict = field(default_factory=dict)
    tasks: dict = field(default_factory=dict)
    spend: SpendConfig = field(default_factory=SpendConfig)


def load_config(path: "Path | str" = "argus.yaml") -> ModelConfig:
    raise NotImplementedError("Plan 03-02 implements load_config")
