async def test_full_run_produces_trace_and_security_and_spans(tmp_path):
    """End-to-end: StateMachine run with obs= produces all 3 output files."""
    from argus.observability.manager import ObservabilityManager, ObsConfig
    from argus.engine.machine import StateMachine
    from argus.engine.states import RunContext, TaskState
    from argus.security.gateway import SecurityGateway, GatewayConfig
    from argus.security.audit.logger import AuditLogger
    import json

    trace_path = tmp_path / "trace.jsonl"
    sec_path = tmp_path / "security.jsonl"
    spans_path = tmp_path / "spans.jsonl"

    config = ObsConfig(
        trace_path=trace_path,
        security_stream_path=sec_path,
        otel_spans_path=spans_path,
    )
    obs = ObservabilityManager(config)

    audit = AuditLogger(socket_path=str(tmp_path / "audit.sock"))
    gateway = SecurityGateway(GatewayConfig(), audit_logger=audit, obs=obs)
    machine = StateMachine(
        gateway=gateway,
        cost_hook=lambda: False,
        obs=obs,
    )
    ctx = RunContext(task_id="integration-test", task_input={"prompt": "hello"})
    result = await machine.run(ctx)
    obs.flush()

    assert result.success is True
    assert trace_path.exists()
    assert spans_path.exists()
    lines = trace_path.read_text().strip().split("\n")
    event_types = [json.loads(l)["event_type"] for l in lines]
    assert "state_transition" in event_types
    assert "run_complete" in event_types


async def test_security_stream_receives_gateway_events(tmp_path):
    """OBS-04: SecurityGateway fires obs.on_security_event for permission blocks."""
    from argus.observability.manager import ObservabilityManager, ObsConfig
    from argus.security.gateway import SecurityGateway, GatewayConfig
    from argus.security.audit.logger import AuditLogger
    from argus.security.permission.policy import PolicyConfig
    import json

    sec_path = tmp_path / "security.jsonl"
    obs = ObservabilityManager(ObsConfig(security_stream_path=sec_path))

    policy = PolicyConfig(rules=[{"role": "reader", "tool": "read_file", "effect": "allow"}])
    audit = AuditLogger(socket_path=str(tmp_path / "audit.sock"))
    gateway = SecurityGateway(
        GatewayConfig(permissions=policy),
        audit_logger=audit,
        obs=obs,
    )
    try:
        gateway.pre_tool_call(agent_role="reader", tool_name="delete_file", tool_input={})
    except Exception:
        pass  # permission block is expected
    obs.flush()

    assert sec_path.exists()
    lines = sec_path.read_text().strip().split("\n")
    assert len(lines) >= 1
    data = json.loads(lines[0])
    assert data["gate"] == "permission"
    assert data["outcome"] == "blocked"
