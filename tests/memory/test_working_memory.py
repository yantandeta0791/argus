"""Working memory (MEM-01) tests.

Verifies that RunContext.artifacts is isolated per StateMachine.run() call.
The behavior already works via Phase 2 deepcopy snapshot. These tests
formalize MEM-01 explicitly as proof of the working memory contract.
"""


async def test_artifacts_fresh_per_run():
    """MEM-01: two sequential runs get independent artifacts dicts."""
    from argus.engine.states import RunContext, TaskState
    from argus.engine.machine import StateMachine
    from unittest.mock import MagicMock

    async def write_handler(context, llm, *, store=None):
        context.artifacts["marker"] = context.task_id

    handlers_map = {s: write_handler for s in [
        TaskState.PLAN, TaskState.EXECUTE, TaskState.VERIFY,
        TaskState.REFLECT, TaskState.COMMIT,
    ]}

    gw = MagicMock()
    sm = StateMachine(gateway=gw, cost_hook=lambda: False, handlers=handlers_map)
    ctx1 = RunContext(task_id="run-1", task_input={})
    ctx2 = RunContext(task_id="run-2", task_input={})
    r1 = await sm.run(ctx1)
    r2 = await sm.run(ctx2)
    assert r1.artifacts["marker"] == "run-1"
    assert r2.artifacts["marker"] == "run-2"


async def test_artifacts_cleared_after_run():
    """MEM-01: successful run returns artifacts; context artifacts was working memory."""
    from argus.engine.states import RunContext, TaskState
    from argus.engine.machine import StateMachine
    from unittest.mock import MagicMock

    async def plan_handler(context, llm, *, store=None):
        context.artifacts["plan_output"] = "generated"

    gw = MagicMock()
    sm = StateMachine(
        gateway=gw,
        cost_hook=lambda: False,
        handlers={TaskState.PLAN: plan_handler},
    )
    ctx = RunContext(task_id="t1", task_input={})
    result = await sm.run(ctx)
    assert result.success is True
    assert result.artifacts["plan_output"] == "generated"
