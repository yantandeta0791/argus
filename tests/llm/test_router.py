"""Tests for LLMRouter -- LLM-01, LLM-02, LLM-03, COST-01, COST-02."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from argus.engine.states import RunContext, TaskState


@pytest.mark.xfail(raises=NotImplementedError, strict=True, reason="Plan 03-03")
async def test_router_calls_litellm_acompletion(mock_litellm_response, sample_config):
    """LLM-01: LLMRouter calls litellm.acompletion, not direct Anthropic SDK."""
    from argus.llm.router import LLMRouter
    from argus.llm.tracker import SpendTracker
    tracker = SpendTracker(sample_config.spend)
    router = LLMRouter(config=sample_config, tracker=tracker)
    ctx = RunContext(task_id="t1", task_input={"goal": "test"})
    ctx.current_state = TaskState.EXECUTE
    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_litellm_response
        result = await router(ctx)
        mock_call.assert_awaited_once()
    assert "response" in result


@pytest.mark.xfail(raises=NotImplementedError, strict=True, reason="Plan 03-03")
async def test_default_model_resolves_to_sonnet(mock_litellm_response, sample_config):
    """LLM-02: default model is anthropic/claude-sonnet-4-6."""
    from argus.llm.router import LLMRouter
    from argus.llm.tracker import SpendTracker
    from argus.llm.config import ModelConfig, SpendConfig
    config = ModelConfig(default="anthropic/claude-sonnet-4-6")
    tracker = SpendTracker(SpendConfig())
    router = LLMRouter(config=config, tracker=tracker)
    ctx = RunContext(task_id="t1", task_input={})
    ctx.current_state = TaskState.EXECUTE
    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_litellm_response
        await router(ctx)
        call_kwargs = mock_call.call_args
        assert "anthropic/claude-sonnet-4-6" in str(call_kwargs)


@pytest.mark.xfail(raises=NotImplementedError, strict=True, reason="Plan 03-03")
async def test_provider_swap_via_config(mock_litellm_response):
    """LLM-03: Swapping to openai/ provider requires only config change."""
    from argus.llm.router import LLMRouter
    from argus.llm.tracker import SpendTracker
    from argus.llm.config import ModelConfig, SpendConfig
    config = ModelConfig(default="openai/gpt-4o")
    tracker = SpendTracker(SpendConfig())
    router = LLMRouter(config=config, tracker=tracker)
    ctx = RunContext(task_id="t1", task_input={})
    ctx.current_state = TaskState.EXECUTE
    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_litellm_response
        await router(ctx)
        call_kwargs = mock_call.call_args
        assert "openai/gpt-4o" in str(call_kwargs)


@pytest.mark.xfail(raises=NotImplementedError, strict=True, reason="Plan 03-03")
async def test_per_state_model_selection(mock_litellm_response, sample_config):
    """COST-01: PLAN uses Opus, EXECUTE uses Sonnet, COMMIT makes no LLM call."""
    from argus.llm.router import LLMRouter
    from argus.llm.tracker import SpendTracker
    tracker = SpendTracker(sample_config.spend)
    router = LLMRouter(config=sample_config, tracker=tracker)

    # PLAN -> Opus
    ctx = RunContext(task_id="t1", task_input={})
    ctx.current_state = TaskState.PLAN
    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_litellm_response
        await router(ctx)
        assert "claude-opus-4-6" in str(mock_call.call_args)

    # COMMIT -> no LLM call (model is None)
    ctx.current_state = TaskState.COMMIT
    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_call:
        result = await router(ctx)
        mock_call.assert_not_awaited()
        assert result == {}


@pytest.mark.xfail(raises=NotImplementedError, strict=True, reason="Plan 03-03")
async def test_per_task_override_supersedes_state(mock_litellm_response, sample_config):
    """COST-02: Per-task override has highest priority over per-state config."""
    from argus.llm.router import LLMRouter
    from argus.llm.tracker import SpendTracker
    tracker = SpendTracker(sample_config.spend)
    router = LLMRouter(config=sample_config, tracker=tracker)
    ctx = RunContext(task_id="summarize", task_input={})
    ctx.current_state = TaskState.PLAN  # would normally use Opus
    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_litellm_response
        await router(ctx)
        # task override "summarize" -> haiku, not opus
        assert "claude-haiku-3-5" in str(mock_call.call_args)
