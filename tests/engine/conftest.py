"""Shared fixtures for argus.engine tests."""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_gateway():
    """SecurityGateway mock: pre_tool_call and post_tool_call pass through."""
    gw = MagicMock()
    gw.pre_tool_call.return_value = {}
    gw.post_tool_call.side_effect = lambda output, **kw: output
    return gw


@pytest.fixture
def stub_llm_callable():
    """Stub LLM callable: returns a fixed dict. Phase 3 replaces with real router."""

    async def _stub(context):
        return {"response": "stub-llm-output"}

    return _stub


@pytest.fixture
def stub_cost_hook_ok():
    """Cost hook that always reports under budget (returns False)."""
    return lambda: False


@pytest.fixture
def stub_cost_hook_over():
    """Cost hook that always reports over budget (returns True — triggers ABORT)."""
    return lambda: True


@pytest.fixture
def fake_tool_fn():
    """Async tool function that succeeds and returns a dict."""

    async def _tool(validated_input):
        return {"result": "ok", "bytes_read": 3}

    return _tool


@pytest.fixture
def flaky_tool_fn():
    """Async tool function that raises RuntimeError on first N calls, then succeeds."""
    call_count = {"n": 0}

    async def _tool(validated_input):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise RuntimeError("transient failure")
        return {"result": "ok", "bytes_read": 3}

    return _tool
