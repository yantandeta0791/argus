import pytest


def test_trace_event_dataclass_fields():
    """TraceEvent is a plain dataclass — constructable immediately, no stub boundary."""
    from argus.observability.trace import TraceEvent
    evt = TraceEvent(
        event_type="state_transition",
        timestamp="2026-03-07T00:00:00+00:00",
        run_id="test-run-id",
        payload={"from": "PLAN", "to": "EXECUTE"},
    )
    assert evt.event_type == "state_transition"
    assert evt.run_id == "test-run-id"


@pytest.mark.xfail(strict=True, raises=NotImplementedError)
def test_trace_writer_writes_jsonl(tmp_path):
    from argus.observability.trace import TraceEvent, TraceWriter
    import json
    path = tmp_path / "trace.jsonl"
    writer = TraceWriter(path=path)
    evt = TraceEvent(
        event_type="state_transition",
        timestamp="2026-03-07T00:00:00+00:00",
        run_id="run-1",
        payload={"from": "PLAN", "to": "EXECUTE", "duration_ms": 12.5, "task_id": "t1"},
    )
    writer.write(evt)
    writer.flush()
    lines = path.read_text().strip().split("\n")
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["event_type"] == "state_transition"
    assert data["run_id"] == "run-1"


@pytest.mark.xfail(strict=True, raises=NotImplementedError)
def test_trace_writer_appends_multiple_events(tmp_path):
    from argus.observability.trace import TraceEvent, TraceWriter
    path = tmp_path / "trace.jsonl"
    writer = TraceWriter(path=path)
    for i in range(3):
        writer.write(TraceEvent(
            event_type="tool_call",
            timestamp="2026-03-07T00:00:00+00:00",
            run_id="run-1",
            payload={"tool": f"tool_{i}", "success": True, "duration_ms": 5.0},
        ))
    writer.flush()
    lines = path.read_text().strip().split("\n")
    assert len(lines) == 3


@pytest.mark.xfail(strict=True, raises=NotImplementedError)
def test_trace_writer_creates_parent_dirs(tmp_path):
    from argus.observability.trace import TraceEvent, TraceWriter
    path = tmp_path / "runs" / "abc123" / "trace.jsonl"
    writer = TraceWriter(path=path)
    writer.write(TraceEvent(
        event_type="llm_call",
        timestamp="2026-03-07T00:00:00+00:00",
        run_id="run-1",
        payload={"model": "claude-3-5-sonnet", "state": "PLAN"},
    ))
    assert path.exists()


@pytest.mark.xfail(strict=True, raises=NotImplementedError)
def test_run_complete_cost_breakdown(tmp_path):
    """OBS-03: cost_breakdown readable from trace without other files."""
    from argus.observability.trace import TraceEvent, TraceWriter
    import json
    path = tmp_path / "trace.jsonl"
    writer = TraceWriter(path=path)
    cost_breakdown = [
        {"state": "PLAN", "model": "claude-3-5-sonnet", "input_tokens": 100,
         "output_tokens": 50, "cost_usd": 0.001},
    ]
    writer.write(TraceEvent(
        event_type="run_complete",
        timestamp="2026-03-07T00:00:00+00:00",
        run_id="run-1",
        payload={
            "final_state": "COMMIT",
            "total_cost_usd": 0.001,
            "cost_breakdown": cost_breakdown,
            "duration_ms": 150.0,
            "error": None,
        },
    ))
    writer.flush()
    lines = path.read_text().strip().split("\n")
    data = json.loads(lines[0])
    assert data["payload"]["cost_breakdown"][0]["model"] == "claude-3-5-sonnet"
    assert data["payload"]["total_cost_usd"] == 0.001
