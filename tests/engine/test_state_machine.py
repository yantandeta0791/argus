"""State machine tests -- STM-01, STM-02, STM-03, STM-04."""


async def test_full_five_state_run(mock_gateway, stub_llm_callable, stub_cost_hook_ok):
    """STM-01: task runs through all 5 states in order; final_state is COMMIT."""
    from argus.engine.states import TaskState, RunContext
    from argus.engine.machine import StateMachine
    ctx = RunContext(task_id="t1", task_input={"goal": "test"})
    sm = StateMachine(gateway=mock_gateway, cost_hook=stub_cost_hook_ok)
    result = await sm.run(ctx)
    assert result.success is True
    assert result.final_state == TaskState.COMMIT


async def test_transition_is_deterministic(mock_gateway, stub_cost_hook_ok):
    """STM-02: state sequence is always PLAN->EXECUTE->VERIFY->REFLECT->COMMIT regardless of handler output."""
    from argus.engine.states import TaskState, RunContext
    from argus.engine.machine import StateMachine
    observed_states = []
    async def recording_handler(context, llm, *, store=None):
        observed_states.append(context.current_state)
    handlers = {s: recording_handler for s in [
        TaskState.PLAN, TaskState.EXECUTE, TaskState.VERIFY, TaskState.REFLECT, TaskState.COMMIT
    ]}
    sm = StateMachine(gateway=mock_gateway, cost_hook=stub_cost_hook_ok, handlers=handlers)
    ctx = RunContext(task_id="t2", task_input={})
    await sm.run(ctx)
    assert observed_states == [
        TaskState.PLAN, TaskState.EXECUTE, TaskState.VERIFY, TaskState.REFLECT, TaskState.COMMIT
    ]


async def test_failure_triggers_rollback(mock_gateway, stub_cost_hook_ok):
    """STM-03: exception in a state handler triggers rollback; run ends in structured error result."""
    from argus.engine.states import TaskState, RunContext
    from argus.engine.machine import StateMachine
    async def good_plan(context, llm, *, store=None):
        context.artifacts["plan"] = "done"
    async def bad_execute(context, llm, *, store=None):
        raise RuntimeError("simulated failure")
    async def noop(context, llm, *, store=None):
        pass
    handlers = {
        TaskState.PLAN: good_plan,
        TaskState.EXECUTE: bad_execute,
        TaskState.VERIFY: noop,
        TaskState.REFLECT: noop,
        TaskState.COMMIT: noop,
    }
    sm = StateMachine(gateway=mock_gateway, cost_hook=stub_cost_hook_ok, handlers=handlers)
    ctx = RunContext(task_id="t3", task_input={})
    result = await sm.run(ctx)
    assert result.success is False
    assert result.error is not None
    # Artifacts rolled back to pre-run state (empty dict)
    assert result.artifacts == {}


async def test_cost_abort_fires_deterministically(mock_gateway, stub_cost_hook_over):
    """STM-04: cost hook returning True triggers ABORT before any state handler runs."""
    from argus.engine.states import TaskState, RunContext
    from argus.engine.machine import StateMachine
    handler_called = {"called": False}
    async def should_not_run(context, llm, *, store=None):
        handler_called["called"] = True
    handlers = {s: should_not_run for s in [
        TaskState.PLAN, TaskState.EXECUTE, TaskState.VERIFY, TaskState.REFLECT, TaskState.COMMIT
    ]}
    sm = StateMachine(gateway=mock_gateway, cost_hook=stub_cost_hook_over, handlers=handlers)
    ctx = RunContext(task_id="t4", task_input={})
    result = await sm.run(ctx)
    assert result.final_state == TaskState.ABORT
    assert result.success is False
    assert handler_called["called"] is False
