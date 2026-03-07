import pytest


def test_obs_config_defaults():
    """ObsConfig is a plain dataclass — constructable immediately, no stub boundary."""
    from argus.observability.manager import ObsConfig
    config = ObsConfig()
    assert config.enabled is True
    assert config.trace_path is None
    assert config.security_stream_path is None
    assert config.otel_spans_path is None
    assert config.service_name == "argus"


def test_manager_on_state_transition_writes_trace(tmp_path):
    from argus.observability.manager import ObservabilityManager, ObsConfig
    from argus.engine.states import RunContext, TaskState
    import json
    trace_path = tmp_path / "trace.jsonl"
    mgr = ObservabilityManager(ObsConfig(trace_path=trace_path))
    ctx = RunContext(task_id="t1", task_input={})
    ctx.current_state = TaskState.PLAN
    mgr.on_state_transition(
        from_state=TaskState.PLAN,
        to_state=TaskState.EXECUTE,
        context=ctx,
        duration_ms=10.5,
    )
    mgr.flush()
    lines = trace_path.read_text().strip().split("\n")
    data = json.loads(lines[0])
    assert data["event_type"] == "state_transition"
    assert data["payload"]["from"] == str(TaskState.PLAN)
    assert data["payload"]["duration_ms"] == 10.5


def test_manager_disabled_is_noop(tmp_path):
    from argus.observability.manager import ObservabilityManager, ObsConfig
    from argus.engine.states import RunContext, TaskState
    trace_path = tmp_path / "trace.jsonl"
    mgr = ObservabilityManager(ObsConfig(trace_path=trace_path, enabled=False))
    ctx = RunContext(task_id="t1", task_input={})
    mgr.on_state_transition(TaskState.PLAN, TaskState.EXECUTE, ctx, 5.0)
    mgr.flush()
    assert not trace_path.exists()


def test_manager_on_star_never_raises(tmp_path):
    """ObservabilityManager.on_* methods must never propagate exceptions."""
    from argus.observability.manager import ObservabilityManager, ObsConfig
    mgr = ObservabilityManager(ObsConfig(trace_path=tmp_path / "trace.jsonl"))
    # Simulate broken writer by passing invalid data — must not raise
    mgr.on_state_transition(None, None, None, float("nan"))
    mgr.on_llm_call(model="", state="", usage={}, cost_usd=0.0, duration_ms=0.0)
    mgr.on_security_event(None)


def test_manager_on_run_complete_embeds_cost(tmp_path):
    """OBS-03: run_complete payload includes cost_breakdown."""
    from argus.observability.manager import ObservabilityManager, ObsConfig
    from argus.engine.states import RunResult, TaskState
    import json
    trace_path = tmp_path / "trace.jsonl"
    mgr = ObservabilityManager(ObsConfig(trace_path=trace_path))
    result = RunResult(
        task_id="t1",
        final_state=TaskState.COMMIT,
        artifacts={},
        error=None,
        success=True,
        cost_breakdown=[
            {"state": "PLAN", "model": "claude-3-5-sonnet",
             "input_tokens": 100, "output_tokens": 50, "cost_usd": 0.001},
        ],
    )
    mgr.on_run_complete(result)
    mgr.flush()
    lines = trace_path.read_text().strip().split("\n")
    data = json.loads(lines[0])
    assert data["event_type"] == "run_complete"
    assert len(data["payload"]["cost_breakdown"]) == 1
