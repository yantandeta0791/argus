"""
Integration tests — StateMachine + LLMRouter + SpendTracker wired together.

Mocked tests (always run): verify the full wiring without live API calls.
Real API test (pytest.mark.integration): verifies Anthropic call completes;
    skipped unless ANTHROPIC_API_KEY is set.
"""
from __future__ import annotations

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from argus.engine.machine import StateMachine
from argus.engine.states import RunContext, TaskState, RunResult
from argus.llm import LLMRouter, ModelConfig, SpendConfig, SpendTracker, load_config
from argus.llm.tracker import StateCostEntry


def _make_mock_response(cost: float = 0.001) -> MagicMock:
    """Build a controlled LiteLLM response mock with real-looking usage fields."""
    resp = MagicMock()
    resp.usage.prompt_tokens = 50
    resp.usage.completion_tokens = 100
    resp._hidden_params = {"response_cost": cost}
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = "agent response"
    return resp


async def test_state_machine_wired_with_llm_router():
    """Full pipeline: StateMachine runs 5 states; LLMRouter called for 4 (not COMMIT)."""
    config = ModelConfig(
        default="anthropic/claude-sonnet-4-6",
        states={
            "PLAN": "anthropic/claude-opus-4-6",
            "EXECUTE": "anthropic/claude-sonnet-4-6",
            "VERIFY": "anthropic/claude-sonnet-4-6",
            "REFLECT": "anthropic/claude-opus-4-6",
            "COMMIT": None,
        },
        spend=SpendConfig(),
    )
    tracker = SpendTracker(config.spend)
    router = LLMRouter(config=config, tracker=tracker)

    # Handlers that exercise the llm callable (as real state handlers would)
    async def llm_handler(context: RunContext, llm, *, store=None) -> None:
        if llm:
            result = await llm(context)
            context.artifacts[str(context.current_state)] = result

    # COMMIT handler does not call llm (model is None -- router returns {})
    async def commit_handler(context: RunContext, llm, *, store=None) -> None:
        context.artifacts["committed"] = True

    handlers = {
        TaskState.PLAN: llm_handler,
        TaskState.EXECUTE: llm_handler,
        TaskState.VERIFY: llm_handler,
        TaskState.REFLECT: llm_handler,
        TaskState.COMMIT: commit_handler,
    }

    gateway = MagicMock()
    machine = StateMachine(gateway=gateway, cost_hook=tracker.over_budget, handlers=handlers, llm_callable=router)
    context = RunContext(task_id="integration-01", task_input={"goal": "test wiring"})

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = _make_mock_response(cost=0.001)
        result: RunResult = await machine.run(context)

    assert result.success is True
    assert result.final_state == TaskState.COMMIT
    # 4 LLM calls: PLAN, EXECUTE, VERIFY, REFLECT (COMMIT model is None)
    assert mock_call.await_count == 4
    # cost_breakdown must be populated from tracker entries
    entries = tracker.entries()
    assert len(entries) == 4
    states_called = [e.state for e in entries]
    assert "PLAN" in states_called
    assert "COMMIT" not in states_called
    # RunResult can be extended with cost_breakdown by caller
    result.cost_breakdown = entries
    assert len(result.cost_breakdown) == 4


async def test_cost_hook_aborts_when_cap_exceeded():
    """COST-03: SpendTracker.over_budget() causes StateMachine to ABORT."""
    # Cap so tight that one call (0.001 USD) exceeds it
    config = ModelConfig(
        default="anthropic/claude-sonnet-4-6",
        spend=SpendConfig(per_task_usd=0.0001),  # $0.0001 — one call costs $0.001
    )
    tracker = SpendTracker(config.spend)
    router = LLMRouter(config=config, tracker=tracker)

    call_count = 0

    async def counting_handler(context: RunContext, llm, *, store=None) -> None:
        nonlocal call_count
        call_count += 1
        if llm:
            await llm(context)

    handlers = {state: counting_handler for state in TaskState if state != TaskState.ABORT}

    gateway = MagicMock()
    machine = StateMachine(gateway=gateway, cost_hook=tracker.over_budget, handlers=handlers, llm_callable=router)
    context = RunContext(task_id="cap-test", task_input={})

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = _make_mock_response(cost=0.001)  # 10x the cap
        result: RunResult = await machine.run(context)

    # First state fires, records cost, exceeds cap.
    # Cost check fires BEFORE each state — so second state never runs.
    assert result.success is False
    assert result.final_state == TaskState.ABORT
    assert "Cost budget exceeded" in (result.error or "")
    # Exactly 1 LLM call completed before ABORT
    assert mock_call.await_count == 1


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set — skip live API call",
)
async def test_real_anthropic_call_completes():
    """LLM-01 + LLM-02: Real Anthropic call via LiteLLM returns response and cost > 0."""
    from argus.llm.config import load_config
    config = load_config("argus.yaml")
    tracker = SpendTracker(config.spend)
    router = LLMRouter(config=config, tracker=tracker)
    ctx = RunContext(task_id="integration-llm-01", task_input={"goal": "say hello in one word"})
    ctx.current_state = TaskState.EXECUTE
    result = await router(ctx)
    assert "response" in result
    assert isinstance(result["response"], str)
    entries = tracker.entries()
    assert len(entries) == 1
    assert entries[0].cost_usd > 0
    assert entries[0].input_tokens > 0
    assert entries[0].model == "anthropic/claude-sonnet-4-6"
