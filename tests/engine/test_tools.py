"""Tool contract tests — TOOL-01, TOOL-02, TOOL-03, TOOL-04."""

import pytest
from pydantic import BaseModel


class _ReadInput(BaseModel):
    path: str


class _ReadOutput(BaseModel):
    result: str
    bytes_read: int


async def test_input_validation_rejects(mock_gateway):
    """TOOL-01: invalid input (missing required field) raises ValidationError before tool executes."""
    from pydantic import ValidationError
    from argus.engine.tools import ToolManifest, ToolRunner

    manifest = ToolManifest(
        name="read_file", input_schema=_ReadInput, output_schema=_ReadOutput
    )
    executed = {"called": False}

    async def tool_fn(inp):
        executed["called"] = True
        return {"result": "ok", "bytes_read": 3}

    runner = ToolRunner(manifest=manifest, tool_fn=tool_fn, gateway=mock_gateway)
    with pytest.raises(ValidationError):
        await runner.call(agent_role="reader", raw_input={"wrong_field": "oops"})
    assert executed["called"] is False


async def test_output_validation_rejects(mock_gateway):
    """TOOL-01: invalid output (missing required field) raises ValidationError before entering context."""
    from pydantic import ValidationError
    from argus.engine.tools import ToolManifest, ToolRunner

    manifest = ToolManifest(
        name="read_file", input_schema=_ReadInput, output_schema=_ReadOutput
    )

    async def bad_tool_fn(inp):
        return {"wrong_key": "bad"}  # missing 'result' and 'bytes_read'

    runner = ToolRunner(manifest=manifest, tool_fn=bad_tool_fn, gateway=mock_gateway)
    with pytest.raises(ValidationError):
        await runner.call(agent_role="reader", raw_input={"path": "/tmp/x"})


async def test_retry_exponential_backoff(mock_gateway):
    """TOOL-02: flaky tool retries up to max_attempts with exponential backoff; succeeds on final attempt."""
    from argus.engine.tools import ToolManifest, ToolRunner

    manifest = ToolManifest(
        name="read_file",
        input_schema=_ReadInput,
        output_schema=_ReadOutput,
        idempotent=True,
        max_attempts=3,
        backoff_base=0.01,  # fast backoff for tests
    )
    call_count = {"n": 0}

    async def flaky_fn(inp):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise RuntimeError("transient")
        return {"result": "ok", "bytes_read": 3}

    runner = ToolRunner(manifest=manifest, tool_fn=flaky_fn, gateway=mock_gateway)
    result = await runner.call(agent_role="reader", raw_input={"path": "/tmp/x"})
    assert result.result == "ok"
    assert call_count["n"] == 3


async def test_circuit_breaker_opens(mock_gateway):
    """TOOL-03: after failure_threshold consecutive failures, subsequent calls fail fast with CircuitBreakerError."""
    from circuitbreaker import CircuitBreakerError
    from argus.engine.tools import ToolManifest, ToolRunner

    manifest = ToolManifest(
        name="flaky_write",
        input_schema=_ReadInput,
        output_schema=_ReadOutput,
        idempotent=True,
        max_attempts=1,
        failure_threshold=3,
        recovery_timeout=60,
    )

    async def always_fails(inp):
        raise RuntimeError("always fails")

    runner = ToolRunner(manifest=manifest, tool_fn=always_fails, gateway=mock_gateway)
    # Exhaust failure threshold
    for _ in range(manifest.failure_threshold):
        with pytest.raises(Exception):
            await runner.call(agent_role="writer", raw_input={"path": "/tmp/x"})
    # Next call must fail fast with CircuitBreakerError (not RuntimeError)
    with pytest.raises(CircuitBreakerError):
        await runner.call(agent_role="writer", raw_input={"path": "/tmp/x"})


async def test_non_idempotent_no_retry_on_ambiguous(mock_gateway):
    """TOOL-04: non-idempotent tool does not retry on ambiguous failure (TimeoutError, ConnectionError)."""
    from argus.engine.tools import ToolManifest, ToolRunner

    manifest = ToolManifest(
        name="write_file",
        input_schema=_ReadInput,
        output_schema=_ReadOutput,
        idempotent=False,
        max_attempts=3,
        backoff_base=0.01,
    )
    call_count = {"n": 0}

    async def ambiguous_fn(inp):
        call_count["n"] += 1
        raise TimeoutError("network timeout — may have succeeded")

    runner = ToolRunner(manifest=manifest, tool_fn=ambiguous_fn, gateway=mock_gateway)
    with pytest.raises(TimeoutError):
        await runner.call(agent_role="writer", raw_input={"path": "/tmp/x"})
    # Must have called exactly once — no retry on ambiguous failure
    assert call_count["n"] == 1
