"""
argus.llm — LiteLLM-backed LLM integration layer.

Public API:
    LLMRouter    — implements LLMCallable Protocol; inject into StateMachine
    ModelConfig  — per-state and per-task model selection config
    SpendConfig  — spend cap configuration (per-task, per-session)
    SpendTracker — in-memory cost accumulator; provides cost_hook for StateMachine
    StateCostEntry — per-state cost record stored in RunResult.cost_breakdown
    load_config  — reads argus.yaml and returns ModelConfig
"""

from argus.llm.config import ModelConfig, SpendConfig, load_config
from argus.llm.tracker import SpendTracker, StateCostEntry
from argus.llm.router import LLMRouter

__all__ = [
    "LLMRouter",
    "ModelConfig",
    "SpendConfig",
    "SpendTracker",
    "StateCostEntry",
    "load_config",
]
