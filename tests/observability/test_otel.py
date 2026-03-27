def test_otel_emitter_llm_call_span():
    from argus.observability.otel import OtelEmitter
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    emitter = OtelEmitter(service_name="argus-test", exporter=exporter)
    emitter.emit_llm_call(
        model="claude-3-5-sonnet",
        state="PLAN",
        input_tokens=100,
        output_tokens=50,
        run_id="test-run-001",
    )
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "gen_ai.client.operation"
    assert spans[0].attributes["gen_ai.system"] == "anthropic"
    assert spans[0].attributes["gen_ai.request.model"] == "claude-3-5-sonnet"
    assert spans[0].attributes["gen_ai.usage.input_tokens"] == 100
    assert spans[0].attributes["gen_ai.usage.output_tokens"] == 50
    assert spans[0].attributes["gen_ai.operation.name"] == "chat"


def test_otel_emitter_state_transition_span():
    from argus.observability.otel import OtelEmitter
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    emitter = OtelEmitter(service_name="argus-test", exporter=exporter)
    emitter.emit_state_transition(from_state="PLAN", to_state="EXECUTE", run_id="run-1")
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "argus.state_transition"
    assert spans[0].attributes["argus.state.from"] == "PLAN"
    assert spans[0].attributes["argus.state.to"] == "EXECUTE"
    assert spans[0].attributes["argus.run_id"] == "run-1"


def test_file_span_exporter_writes_jsonl(tmp_path):
    from argus.observability.otel import FileSpanExporter, OtelEmitter

    path = tmp_path / "spans.jsonl"
    exporter = FileSpanExporter(path=path)
    emitter = OtelEmitter(service_name="argus-test", exporter=exporter)
    emitter.emit_llm_call(
        model="claude-3-5-sonnet",
        state="EXECUTE",
        input_tokens=200,
        output_tokens=80,
        run_id="run-2",
    )
    emitter.flush()
    import json

    lines = path.read_text().strip().split("\n")
    assert len(lines) == 1
    span_data = json.loads(lines[0])
    # to_json() produces OTel-standard JSON with "name" field
    assert "name" in span_data
    assert span_data["name"] == "gen_ai.client.operation"


def test_file_span_exporter_creates_parent_dirs(tmp_path):
    from argus.observability.otel import FileSpanExporter

    path = tmp_path / "runs" / "abc" / "spans.jsonl"
    exporter = FileSpanExporter(path=path)
    exporter.shutdown()
    assert path.exists()


# ---------------------------------------------------------------------------
# OPS-04: Security violation span emission
# ---------------------------------------------------------------------------


def test_emit_security_violation_span():
    """OPS-04: emit_security_violation() emits an argus.security.violation span
    with the correct attributes.

    RED: OtelEmitter does not yet have emit_security_violation().
    """
    from argus.observability.otel import OtelEmitter
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    emitter = OtelEmitter(service_name="argus-test", exporter=exporter)
    emitter.emit_security_violation(
        event_type="permission",
        tool_name="read_file",
        severity="HIGH",
        agent_role="analyst",
    )
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "argus.security.violation"
    assert spans[0].attributes["argus.security.event_type"] == "permission"
    assert spans[0].attributes["argus.security.tool_name"] == "read_file"
    assert spans[0].attributes["argus.security.severity"] == "HIGH"
    assert spans[0].attributes["argus.security.agent_role"] == "analyst"
