"""Integration test -- real Anthropic API call. Skipped without ANTHROPIC_API_KEY."""
import os
import pytest
from argus.engine.states import RunContext, TaskState


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set -- skip live API call",
)
@pytest.mark.xfail(raises=NotImplementedError, strict=True, reason="Plan 03-03")
async def test_real_anthropic_call_completes():
    """LLM-01 + LLM-02: Real Anthropic call via LiteLLM returns response and cost > 0."""
    from argus.llm.router import LLMRouter
    from argus.llm.config import load_config
    from argus.llm.tracker import SpendTracker
    config = load_config("argus.yaml")
    tracker = SpendTracker(config.spend)
    router = LLMRouter(config=config, tracker=tracker)
    ctx = RunContext(task_id="integration-llm-01", task_input={"goal": "say hello in one word"})
    ctx.current_state = TaskState.EXECUTE
    result = await router(ctx)
    assert "response" in result
    entries = tracker.entries()
    assert len(entries) == 1
    assert entries[0].cost_usd > 0
    assert entries[0].input_tokens > 0
