"""Tests for default state handlers (Phase 11.5)."""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

from argus.engine.handlers import ToolRegistry, default_handlers
from argus.engine.machine import StateMachine
from argus.engine.states import RunContext, TaskState
from argus.engine.tools import ToolManifest


class EchoInput(BaseModel):
    text: str


class EchoOutput(BaseModel):
    result: str


async def _echo_tool(validated: EchoInput) -> dict:
    return {"result": validated.text}


def _echo_manifest() -> ToolManifest:
    return ToolManifest(name="echo", input_schema=EchoInput, output_schema=EchoOutput)


class FakeRouter:
    """LLMCallable stub returning a scripted response per state."""

    def __init__(self, responses: dict[str, str]):
        self.responses = responses
        self.calls: list[str] = []

    async def __call__(self, context: RunContext) -> dict:
        state = str(context.current_state)
        self.calls.append(state)
        return {"response": self.responses.get(state, "ok")}


class AllowGateway:
    def pre_tool_call(self, role, tool, tool_input, **kw):
        return tool_input

    def post_tool_call(self, tool_output, skill_manifest=None):
        return tool_output


def _ctx() -> RunContext:
    return RunContext(task_id="t1", task_input={"goal": "demo"})


@pytest.mark.asyncio
async def test_commit_handler_never_calls_llm_and_finalizes():
    router = FakeRouter({})
    handlers = default_handlers(gateway=AllowGateway())
    ctx = _ctx()
    await handlers[TaskState.COMMIT](ctx, router)
    assert router.calls == []  # no LLM call in COMMIT
    assert ctx.artifacts["committed"] is True


@pytest.mark.asyncio
async def test_execute_handler_runs_tool_through_gateway():
    registry = ToolRegistry()
    registry.register(_echo_manifest(), _echo_tool)
    handlers = default_handlers(registry=registry, gateway=AllowGateway())
    router = FakeRouter(
        {
            "EXECUTE": json.dumps({"tool": "echo", "input": {"text": "hi"}}),
        }
    )
    ctx = _ctx()
    ctx.current_state = (
        TaskState.EXECUTE
    )  # normally set by StateMachine before dispatch
    await handlers[TaskState.EXECUTE](ctx, router)
    assert len(ctx.artifacts["tool_calls"]) == 1
    assert ctx.artifacts["tool_calls"][0]["tool"] == "echo"
    assert ctx.artifacts["tool_calls"][0]["output"]["result"] == "hi"


@pytest.mark.asyncio
async def test_unknown_tool_fails_closed_not_executed():
    registry = ToolRegistry()
    handlers = default_handlers(registry=registry, gateway=AllowGateway())
    router = FakeRouter(
        {
            "EXECUTE": json.dumps({"tool": "delete_everything", "input": {}}),
        }
    )
    ctx = _ctx()
    ctx.current_state = TaskState.EXECUTE
    await handlers[TaskState.EXECUTE](ctx, router)
    assert "delete_everything" in ctx.artifacts["blocked_tools"]
    assert ctx.artifacts.get("tool_calls") is None


@pytest.mark.asyncio
async def test_no_gateway_fails_closed():
    registry = ToolRegistry()
    registry.register(_echo_manifest(), _echo_tool)
    handlers = default_handlers(registry=registry, gateway=None)
    router = FakeRouter(
        {
            "EXECUTE": json.dumps({"tool": "echo", "input": {"text": "hi"}}),
        }
    )
    ctx = _ctx()
    ctx.current_state = TaskState.EXECUTE
    await handlers[TaskState.EXECUTE](ctx, router)
    assert "echo" in ctx.artifacts["blocked_tools"]


@pytest.mark.asyncio
async def test_full_run_through_state_machine_with_handlers():
    registry = ToolRegistry()
    registry.register(_echo_manifest(), _echo_tool)

    router = FakeRouter(
        {
            "PLAN": "plan text",
            "EXECUTE": json.dumps({"tool": "echo", "input": {"text": "work"}}),
            "VERIFY": "verified",
            "REFLECT": "reflected",
            "COMMIT": "",
        }
    )

    sm = StateMachine(
        gateway=AllowGateway(),
        cost_hook=lambda: False,
        handlers=default_handlers(registry=registry, gateway=AllowGateway()),
        llm_callable=router,
    )
    ctx = _ctx()
    result = await sm.run(ctx)

    assert result.success is True, result.error
    assert result.final_state == TaskState.COMMIT
    assert ctx.artifacts["committed"] is True
    # LLM called for PLAN/EXECUTE/VERIFY/REFLECT but NOT COMMIT
    assert router.calls.count("COMMIT") == 0
    assert set(router.calls) >= {"PLAN", "EXECUTE", "VERIFY", "REFLECT"}
    assert ctx.artifacts["tool_calls"][0]["output"]["result"] == "work"


@pytest.mark.asyncio
async def test_security_violation_rolls_back_run():
    from argus.security.exceptions import PermissionDeniedError

    class DenyGateway:
        def pre_tool_call(self, role, tool, tool_input, **kw):
            raise PermissionDeniedError(gate="permission", blocked=tool, rule="denied")

        def post_tool_call(self, tool_output, skill_manifest=None):
            return tool_output

    registry = ToolRegistry()
    registry.register(_echo_manifest(), _echo_tool)
    router = FakeRouter(
        {
            "PLAN": "plan text",
            "EXECUTE": json.dumps({"tool": "echo", "input": {"text": "work"}}),
        }
    )
    sm = StateMachine(
        gateway=DenyGateway(),
        cost_hook=lambda: False,
        handlers=default_handlers(registry=registry, gateway=DenyGateway()),
        llm_callable=router,
    )
    ctx = _ctx()
    result = await sm.run(ctx)
    assert result.success is False
    assert result.final_state == TaskState.EXECUTE  # failed where it happened
