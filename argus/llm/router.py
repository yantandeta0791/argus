"""
LLMRouter -- LiteLLM-backed implementation of the LLMCallable Protocol.

Resolves model per-task > per-state > default (COST-01, COST-02).
Calls litellm.acompletion() -- never the direct Anthropic SDK (LLM-01, LLM-03).
Records StateCostEntry in SpendTracker after every successful call (COST-04).
Short-circuits to {} when state model is None (e.g., COMMIT -- no LLM call).

Input redaction: RunContext.task_input is serialized to str and passed through
SecretRedactor if one is injected. Redaction happens BEFORE acompletion() (SEC-03).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import litellm

from argus.engine.states import RunContext, TaskState
from argus.llm.config import ModelConfig
from argus.llm.tracker import SpendTracker, StateCostEntry

logger = logging.getLogger(__name__)

# LiteLLM call defaults
_DEFAULT_TEMPERATURE = 0.2
_DEFAULT_MAX_TOKENS = 2048


class LLMRouter:
    """Implements LLMCallable Protocol using LiteLLM as the provider abstraction.

    Usage:
        config = load_config("argus.yaml")
        tracker = SpendTracker(config.spend)
        router = LLMRouter(config=config, tracker=tracker)
        machine = StateMachine(..., cost_hook=tracker.over_budget, llm_callable=router)
    """

    def __init__(
        self,
        config: ModelConfig,
        tracker: SpendTracker,
        redactor: Any | None = None,
        obs: Any = None,
    ) -> None:
        """
        Args:
            config:   ModelConfig from load_config() -- model strings and spend caps.
            tracker:  SpendTracker for this run -- records cost per state call.
            redactor: Optional SecretRedactor from argus.security -- redacts secrets
                      from RunContext.task_input before sending to LLM (SEC-03).
                      If None, no redaction is applied (safe for unit tests with dummy data).
            obs:      Optional ObservabilityManager -- records LLM call telemetry (OBS-02).
                      If None, no observability data is emitted.
        """
        self._config = config
        self._tracker = tracker
        self._redactor = redactor
        self._obs = obs

    async def __call__(self, context: RunContext) -> dict[str, Any]:
        """Select model, call LiteLLM, record cost, return response dict.

        Returns {} immediately if the resolved model is None (e.g., COMMIT state).
        Raises on LiteLLM API failures -- StateMachine.run() catches and rolls back.
        """
        model = self._resolve_model(context)
        if model is None:
            logger.debug(
                "State %s has no model configured -- skipping LLM call",
                context.current_state,
            )
            return {}

        messages = self._build_messages(context)
        logger.debug(
            "LLMRouter calling %s for state %s / task %s",
            model,
            context.current_state,
            context.task_id,
        )

        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=_DEFAULT_TEMPERATURE,
            max_tokens=_DEFAULT_MAX_TOKENS,
        )

        entry = StateCostEntry(
            state=str(context.current_state),
            model=model,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            cost_usd=response._hidden_params.get("response_cost", 0.0),
        )
        self._tracker.record(entry)

        if self._obs:
            self._obs.on_llm_call(
                model=model,
                state=str(context.current_state),
                usage={"input": entry.input_tokens, "output": entry.output_tokens},
                cost_usd=entry.cost_usd,
                duration_ms=0.0,
            )

        return {"response": response.choices[0].message.content}

    def _resolve_model(self, context: RunContext) -> str | None:
        """Resolve model with priority: per-task > per-state > default.

        Returns None when the state explicitly has no model (e.g., COMMIT: null).
        """
        # 1. Per-task override (COST-02)
        task_model = self._config.tasks.get(context.task_id)
        if task_model:
            return task_model

        # 2. Per-state config (COST-01) -- None is a valid explicit value (no LLM call)
        state_key = str(context.current_state)
        if state_key in self._config.states:
            return self._config.states[state_key]  # may be None

        # 3. Default fallback
        return self._config.default

    def _build_messages(self, context: RunContext) -> list[dict[str, str]]:
        """Construct LiteLLM messages list from RunContext.

        System prompt: state + task_id for deterministic framing.
        User content: task_input dict serialized to JSON; include artifacts for
        VERIFY and REFLECT states where prior work context matters.
        Redaction applied to user content before sending (SEC-03).
        """
        system = (
            f"You are an Argus agent executing state {context.current_state} "
            f"for task '{context.task_id}'. Be concise and deterministic. "
            f"Do not suggest state transitions -- transitions are managed externally."
        )

        user_parts = [f"Task input: {json.dumps(context.task_input, default=str)}"]

        # Include artifacts for states that benefit from prior work context
        if (
            context.current_state in (TaskState.VERIFY, TaskState.REFLECT)
            and context.artifacts
        ):
            user_parts.append(
                f"Prior artifacts: {json.dumps(context.artifacts, default=str)}"
            )

        user_content = "\n\n".join(user_parts)

        # Redact secrets from user content before sending to LLM (SEC-03)
        if self._redactor is not None:
            user_content = self._redactor.redact(user_content)

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]
