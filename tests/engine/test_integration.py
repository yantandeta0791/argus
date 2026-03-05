"""
Integration tests for argus.engine — StateMachine + ToolRunner + SecurityGateway.

These tests prove the two subsystems compose correctly:
  - ToolRunner.call() inside a state handler flows to RunResult.artifacts
  - ArgusSecurityError from gateway inside a tool call triggers StateMachine rollback
"""
import pytest
from unittest.mock import MagicMock
from pydantic import BaseModel

from argus.engine import StateMachine, ToolManifest, ToolRunner, TaskState, RunContext


class _Input(BaseModel):
    value: str


class _Output(BaseModel):
    result: str
    bytes_read: int


async def test_tool_runner_inside_state_handler(mock_gateway):
    """End-to-end: ToolRunner.call() inside EXECUTE handler; result appears in artifacts; COMMIT."""
    async def real_tool(inp: _Input):
        return {"result": f"processed:{inp.value}", "bytes_read": len(inp.value)}

    manifest = ToolManifest(
        name="integration_read_v2",
        input_schema=_Input,
        output_schema=_Output,
        idempotent=True,
        max_attempts=1,
    )
    runner = ToolRunner(manifest=manifest, tool_fn=real_tool, gateway=mock_gateway)

    async def execute_handler(context: RunContext, llm) -> None:
        output = await runner.call(agent_role="executor", raw_input={"value": "hello"})
        context.artifacts["tool_result"] = output.result

    async def noop(c, l):
        pass

    handlers = {
        TaskState.PLAN: noop,
        TaskState.EXECUTE: execute_handler,
        TaskState.VERIFY: noop,
        TaskState.REFLECT: noop,
        TaskState.COMMIT: noop,
    }

    sm = StateMachine(gateway=mock_gateway, cost_hook=lambda: False, handlers=handlers)
    ctx = RunContext(task_id="integration-01", task_input={"goal": "process hello"})
    result = await sm.run(ctx)

    assert result.success is True
    assert result.final_state == TaskState.COMMIT
    assert result.artifacts.get("tool_result") == "processed:hello"


async def test_security_violation_inside_tool_triggers_rollback():
    """Security gate violation inside tool call triggers StateMachine rollback; artifacts cleared."""
    from argus.security.exceptions import PermissionDeniedError

    blocking_gateway = MagicMock()
    blocking_gateway.pre_tool_call.side_effect = PermissionDeniedError(
        gate="permission", blocked="write_file", rule="role=executor tool=write_file"
    )
    blocking_gateway.post_tool_call.side_effect = lambda output, **kw: output

    manifest = ToolManifest(
        name="write_file_blocked",
        input_schema=_Input,
        output_schema=_Output,
        idempotent=True,
        max_attempts=1,
    )

    async def never_reaches_here(inp):
        return {"result": "should not run", "bytes_read": 0}

    runner = ToolRunner(manifest=manifest, tool_fn=never_reaches_here, gateway=blocking_gateway)

    async def execute_handler(context: RunContext, llm) -> None:
        context.artifacts["partial"] = "written before tool call"
        await runner.call(agent_role="executor", raw_input={"value": "secret"})

    async def noop(c, l):
        pass

    handlers = {
        TaskState.PLAN: noop,
        TaskState.EXECUTE: execute_handler,
        TaskState.VERIFY: noop,
        TaskState.REFLECT: noop,
        TaskState.COMMIT: noop,
    }

    sm = StateMachine(gateway=blocking_gateway, cost_hook=lambda: False, handlers=handlers)
    ctx = RunContext(task_id="integration-02", task_input={"goal": "write blocked"})
    result = await sm.run(ctx)

    assert result.success is False
    assert result.final_state == TaskState.EXECUTE
    assert result.error is not None
    # Artifacts rolled back to pre-run state (empty dict)
    assert result.artifacts == {}
