"""Integration tests -- StateMachine + SessionStore wiring.

Proves the full memory hierarchy works end-to-end:
- MEM-01: working memory isolation per run
- MEM-02: session facts persist across runs, session isolation enforced
- MEM-03: global facts visible across sessions
- Handler receives store parameter from StateMachine
"""


async def test_handler_receives_store():
    """MEM-02 wiring: state handler called with store parameter."""
    from argus.engine.states import RunContext, TaskState
    from argus.engine.machine import StateMachine
    from unittest.mock import MagicMock

    captured_store = []

    async def capturing_handler(context, llm, *, store=None):
        captured_store.append(store)

    handlers = {s: capturing_handler for s in [
        TaskState.PLAN, TaskState.EXECUTE, TaskState.VERIFY,
        TaskState.REFLECT, TaskState.COMMIT,
    ]}
    mock_store = MagicMock()
    gw = MagicMock()
    sm = StateMachine(
        gateway=gw, cost_hook=lambda: False,
        handlers=handlers, store=mock_store,
    )
    ctx = RunContext(task_id="t1", task_input={})
    await sm.run(ctx)
    assert len(captured_store) == 5
    assert all(s is mock_store for s in captured_store)


async def test_session_fact_persists_across_runs(tmp_db_path):
    """MEM-02: write fact in run 1, read it in run 2 (same session)."""
    from argus.engine.states import RunContext, TaskState
    from argus.engine.machine import StateMachine
    from argus.memory.manager import MemoryManager, MemoryConfig
    from unittest.mock import MagicMock

    mgr = MemoryManager(MemoryConfig(db_path=tmp_db_path))
    await mgr.connect()
    store = mgr.session("session-A")

    async def writer(context, llm, *, store=None):
        if store and context.current_state == TaskState.PLAN:
            await store.put("step", context.task_input.get("step"))

    async def reader(context, llm, *, store=None):
        if store and context.current_state == TaskState.PLAN:
            val = await store.get("step")
            context.artifacts["read_step"] = val

    gw = MagicMock()
    sm1 = StateMachine(gateway=gw, cost_hook=lambda: False,
                       handlers={TaskState.PLAN: writer}, store=store)
    ctx1 = RunContext(task_id="run1", task_input={"step": "first"})
    await sm1.run(ctx1)

    sm2 = StateMachine(gateway=gw, cost_hook=lambda: False,
                       handlers={TaskState.PLAN: reader}, store=store)
    ctx2 = RunContext(task_id="run2", task_input={"step": "second"})
    r2 = await sm2.run(ctx2)

    assert r2.artifacts["read_step"] == "first"
    await mgr.close()


async def test_working_memory_isolation(tmp_db_path):
    """MEM-01: two runs in same session have independent RunContext.artifacts.

    This test passes immediately because Phase 2 deepcopy already isolates
    RunContext.artifacts per run. Kept here as an explicit MEM-01 proof.
    """
    from argus.engine.states import RunContext, TaskState
    from argus.engine.machine import StateMachine
    from unittest.mock import MagicMock

    async def marker_handler(context, llm, *, store=None):
        context.artifacts["marker"] = context.task_id

    handlers = {s: marker_handler for s in [
        TaskState.PLAN, TaskState.EXECUTE, TaskState.VERIFY,
        TaskState.REFLECT, TaskState.COMMIT,
    ]}
    gw = MagicMock()
    sm = StateMachine(gateway=gw, cost_hook=lambda: False, handlers=handlers)
    r1 = await sm.run(RunContext(task_id="run-1", task_input={}))
    r2 = await sm.run(RunContext(task_id="run-2", task_input={}))
    assert r1.artifacts["marker"] == "run-1"
    assert r2.artifacts["marker"] == "run-2"


async def test_session_isolation_across_sessions(tmp_db_path):
    """MEM-02: session A facts are not visible in session B."""
    from argus.memory.manager import MemoryManager, MemoryConfig

    mgr = MemoryManager(MemoryConfig(db_path=tmp_db_path))
    await mgr.connect()
    store_a = mgr.session("session-A")
    store_b = mgr.session("session-B")

    await store_a.put("secret", "alpha")
    assert await store_b.get("secret") is None
    assert await store_a.get("secret") == "alpha"
    await mgr.close()


async def test_global_fact_visible_across_sessions(tmp_db_path):
    """MEM-03: global fact written in session A is queryable in session B."""
    from argus.memory.manager import MemoryManager, MemoryConfig

    mgr = MemoryManager(MemoryConfig(db_path=tmp_db_path))
    await mgr.connect()
    store_a = mgr.session("session-A")
    store_b = mgr.session("session-B")

    await store_a.put("config_key", {"version": 1}, global_=True)
    result = await store_b.get("config_key", global_=True)
    assert result == {"version": 1}
    await mgr.close()
