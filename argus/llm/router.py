"""
LLMRouter: implements LLMCallable Protocol using litellm.acompletion().
Resolves model per-task > per-state > default from ModelConfig.
Records cost entries in SpendTracker after each call.
Implemented in Plan 03-03.
"""
from __future__ import annotations

from typing import Any

from argus.llm.config import ModelConfig
from argus.llm.tracker import SpendTracker
from argus.engine.states import RunContext


class LLMRouter:
    def __init__(self, config: ModelConfig, tracker: SpendTracker) -> None:
        raise NotImplementedError("Plan 03-03 implements LLMRouter")

    async def __call__(self, context: RunContext) -> dict[str, Any]:
        raise NotImplementedError
