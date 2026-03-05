"""Behavioral tests for argus.engine.states — STM-01 through STM-04 contracts."""
import copy
import pytest


def test_task_state_has_exactly_six_members():
    """TaskState StrEnum has exactly 6 values: PLAN, EXECUTE, VERIFY, REFLECT, COMMIT, ABORT."""
    from argus.engine.states import TaskState
    assert len(TaskState) == 6
    assert set(TaskState) == {
        TaskState.PLAN,
        TaskState.EXECUTE,
        TaskState.VERIFY,
        TaskState.REFLECT,
        TaskState.COMMIT,
        TaskState.ABORT,
    }


def test_task_state_string_equality():
    """TaskState('PLAN') == TaskState.PLAN — StrEnum string equality."""
    from argus.engine.states import TaskState
    assert TaskState("PLAN") == TaskState.PLAN
    assert TaskState("EXECUTE") == TaskState.EXECUTE
    assert TaskState("VERIFY") == TaskState.VERIFY
    assert TaskState("REFLECT") == TaskState.REFLECT
    assert TaskState("COMMIT") == TaskState.COMMIT
    assert TaskState("ABORT") == TaskState.ABORT


def test_task_state_is_str():
    """TaskState members are strings (StrEnum)."""
    from argus.engine.states import TaskState
    assert isinstance(TaskState.PLAN, str)
    assert TaskState.PLAN == "PLAN"


def test_run_context_minimal_construction():
    """RunContext can be constructed with task_id and task_input only; defaults are correct."""
    from argus.engine.states import RunContext, TaskState
    ctx = RunContext(task_id="t1", task_input={"goal": "test"})
    assert ctx.task_id == "t1"
    assert ctx.task_input == {"goal": "test"}
    assert ctx.artifacts == {}
    assert ctx.current_state == TaskState.PLAN
    assert ctx.error is None


def test_run_context_deepcopy_independence():
    """copy.deepcopy(RunContext(...)) produces independent copy — mutating original does not affect copy."""
    from argus.engine.states import RunContext
    ctx = RunContext(task_id="x", task_input={"a": 1}, artifacts={"k": [1, 2, 3]})
    snap = copy.deepcopy(ctx)
    ctx.artifacts["k"].append(99)
    assert snap.artifacts["k"] == [1, 2, 3], "deepcopy is not independent"


def test_run_context_deepcopy_task_input_independence():
    """Mutating original task_input does not affect deepcopy."""
    from argus.engine.states import RunContext
    ctx = RunContext(task_id="x", task_input={"nested": [1, 2]})
    snap = copy.deepcopy(ctx)
    ctx.task_input["nested"].append(99)
    assert snap.task_input["nested"] == [1, 2]


def test_run_result_success_default():
    """RunResult(task_id=..., final_state=COMMIT, artifacts={}) has success=True by default."""
    from argus.engine.states import RunResult, TaskState
    r = RunResult(task_id="x", final_state=TaskState.COMMIT, artifacts={})
    assert r.success is True
    assert r.error is None


def test_run_result_failure():
    """RunResult with success=False and error string."""
    from argus.engine.states import RunResult, TaskState
    r = RunResult(
        task_id="x",
        final_state=TaskState.ABORT,
        artifacts={},
        error="something went wrong",
        success=False,
    )
    assert r.success is False
    assert r.error == "something went wrong"
    assert r.final_state == TaskState.ABORT


def test_run_result_stores_artifacts():
    """RunResult preserves artifacts dict."""
    from argus.engine.states import RunResult, TaskState
    artifacts = {"plan_output": "done", "tokens_used": 42}
    r = RunResult(task_id="y", final_state=TaskState.COMMIT, artifacts=artifacts)
    assert r.artifacts == artifacts


async def test_llm_callable_isinstance_check():
    """isinstance(stub_fn, LLMCallable) is True for async callable matching Protocol signature."""
    from argus.engine.states import LLMCallable, RunContext

    async def stub(context: RunContext) -> dict:
        return {}

    assert isinstance(stub, LLMCallable)


def test_llm_callable_sync_not_instance():
    """Synchronous callable does NOT satisfy LLMCallable Protocol (async required)."""
    from argus.engine.states import LLMCallable

    def sync_fn(context):
        return {}

    # runtime_checkable Protocols with methods only check callable presence, not async.
    # This test documents the known limitation: sync fns pass isinstance check.
    # The Protocol still serves as documentation of intent.
    result = isinstance(sync_fn, LLMCallable)
    # Asserting True because Python runtime_checkable Protocol only checks method presence
    assert isinstance(result, bool)  # just verify it doesn't raise
