def test_security_event_writer_writes_jsonl(tmp_path):
    from argus.observability.security_stream import SecurityEventWriter
    from argus.security.events import SecurityEvent, GateType
    import json

    path = tmp_path / "security.jsonl"
    writer = SecurityEventWriter(path=path)
    event = SecurityEvent(
        gate=GateType.PERMISSION,
        outcome="blocked",
        agent_role="reader",
        tool_name="delete_file",
        rule_triggered="deny:reader:delete_file",
    )
    writer.write(event)
    writer.flush()
    lines = path.read_text().strip().split("\n")
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["gate"] == "permission"
    assert data["outcome"] == "blocked"


def test_security_event_writer_none_path_is_noop():
    """OBS-04: path=None silently discards events — no error raised."""
    from argus.observability.security_stream import SecurityEventWriter
    from argus.security.events import SecurityEvent, GateType

    writer = SecurityEventWriter(path=None)
    event = SecurityEvent(gate=GateType.EGRESS, outcome="violation")
    writer.write(event)  # must not raise
    writer.flush()


def test_security_stream_independent_of_trace(tmp_path):
    """OBS-04: security stream does not depend on trace path."""
    from argus.observability.security_stream import SecurityEventWriter
    from argus.security.events import SecurityEvent, GateType
    import json

    # Only security path provided — no trace path
    sec_path = tmp_path / "security.jsonl"
    writer = SecurityEventWriter(path=sec_path)
    writer.write(SecurityEvent(gate=GateType.PROMPT_SHIELD, outcome="blocked"))
    writer.flush()
    assert sec_path.exists()
    data = json.loads(sec_path.read_text().strip())
    assert data["gate"] == "prompt_shield"


def test_security_event_writer_creates_parent_dirs(tmp_path):
    from argus.observability.security_stream import SecurityEventWriter
    from argus.security.events import SecurityEvent, GateType

    path = tmp_path / "runs" / "abc123" / "security.jsonl"
    writer = SecurityEventWriter(path=path)
    writer.write(SecurityEvent(gate=GateType.EGRESS, outcome="violation"))
    assert path.exists()
