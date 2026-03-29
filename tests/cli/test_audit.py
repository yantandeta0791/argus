"""CLI tests for argus audit command (OPS-01, OPS-02).

All tests are RED at collection time because argus.cli.audit does not exist yet.
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typer.testing import CliRunner

# This import is intentionally at module level to force collection-time RED failure.
from argus.cli.audit import audit_command  # noqa: F401

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    gate: str,
    outcome: str,
    tool_name: str,
    agent_role: str = "analyst",
    minutes_ago: int = 0,
) -> dict:
    """Return a SecurityEvent-compatible dict for use in JSONL test fixtures."""
    ts = datetime.now(tz=timezone.utc) - timedelta(minutes=minutes_ago)
    return {
        "event_id": f"evt-{gate}-{outcome}",
        "timestamp": ts.isoformat(),
        "gate": gate,
        "outcome": outcome,
        "agent_role": agent_role,
        "tool_name": tool_name,
        "rule_triggered": f"{gate}_rule",
        "blocked_value": None,
        "prev_hash": "abc123" if minutes_ago == 0 else "def456",
        "metadata": {},
    }


def _write_jsonl(path: Path, events: list[dict]) -> None:
    """Write each event as a JSON line to path."""
    with open(path, "w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")


# ---------------------------------------------------------------------------
# OPS-01: Display audit events from JSONL log
# ---------------------------------------------------------------------------


def test_audit_prints_events(tmp_path):
    """OPS-01: argus audit --log <file> displays tool_name for each event."""
    from argus.cli.main import app

    tmp_log = tmp_path / "audit.jsonl"
    events = [
        _make_event("permission", "allowed", "read_file"),
        _make_event("egress", "blocked", "fetch_url"),
    ]
    _write_jsonl(tmp_log, events)

    result = runner.invoke(app, ["audit", "--log", str(tmp_log)])
    assert result.exit_code == 0
    assert "read_file" in result.output
    assert "fetch_url" in result.output


def test_audit_empty_log_exits_zero(tmp_path):
    """OPS-01: An empty log file exits 0 and reports no events found."""
    from argus.cli.main import app

    tmp_log = tmp_path / "empty.jsonl"
    tmp_log.write_text("")

    result = runner.invoke(app, ["audit", "--log", str(tmp_log)])
    assert result.exit_code == 0
    assert "No audit events found" in result.output


def test_audit_missing_log_exits_zero():
    """OPS-01: A non-existent log path exits 0 and reports no events found."""
    from argus.cli.main import app

    result = runner.invoke(app, ["audit", "--log", "/nonexistent/path.jsonl"])
    assert result.exit_code == 0
    assert "No audit events found" in result.output


def test_audit_hides_chain_fields(tmp_path):
    """OPS-01: prev_hash and event_id (chain fields) are not displayed to the user."""
    from argus.cli.main import app

    tmp_log = tmp_path / "audit.jsonl"
    event = _make_event("permission", "allowed", "read_file")
    event["prev_hash"] = "abc123"
    event["event_id"] = "uuid-here"
    _write_jsonl(tmp_log, [event])

    result = runner.invoke(app, ["audit", "--log", str(tmp_log)])
    assert "abc123" not in result.output
    assert "uuid-here" not in result.output


def test_audit_outcome_colors(tmp_path):
    """OPS-01: Both 'blocked' and 'allowed' outcomes are visible in rendered output."""
    from argus.cli.main import app

    tmp_log = tmp_path / "audit.jsonl"
    events = [
        _make_event("permission", "blocked", "write_file"),
        _make_event("permission", "allowed", "read_file"),
    ]
    _write_jsonl(tmp_log, events)

    result = runner.invoke(app, ["audit", "--log", str(tmp_log)])
    assert "blocked" in result.output
    assert "allowed" in result.output


# ---------------------------------------------------------------------------
# OPS-02: Filtering audit events by type, severity, and time window
# ---------------------------------------------------------------------------


def test_audit_filter_type(tmp_path):
    """OPS-02: --type permission shows only permission events, not egress events."""
    from argus.cli.main import app

    tmp_log = tmp_path / "audit.jsonl"
    events = [
        _make_event("permission", "allowed", "read_file"),
        _make_event("egress", "blocked", "fetch_url"),
    ]
    _write_jsonl(tmp_log, events)

    result = runner.invoke(app, ["audit", "--log", str(tmp_log), "--type", "permission"])
    assert "read_file" in result.output
    assert "fetch_url" not in result.output


def test_audit_filter_severity(tmp_path):
    """OPS-02: --severity HIGH shows only blocked events (HIGH severity)."""
    from argus.cli.main import app

    tmp_log = tmp_path / "audit.jsonl"
    events = [
        _make_event("permission", "blocked", "write_file"),
        _make_event("permission", "allowed", "read_file"),
    ]
    _write_jsonl(tmp_log, events)

    result = runner.invoke(app, ["audit", "--log", str(tmp_log), "--severity", "HIGH"])
    assert "write_file" in result.output
    assert "read_file" not in result.output


def test_audit_filter_since(tmp_path):
    """OPS-02: --since 1h shows only events from the last hour."""
    from argus.cli.main import app

    tmp_log = tmp_path / "audit.jsonl"
    events = [
        _make_event("permission", "allowed", "old_tool", minutes_ago=120),
        _make_event("permission", "allowed", "recent_tool", minutes_ago=10),
    ]
    _write_jsonl(tmp_log, events)

    result = runner.invoke(app, ["audit", "--log", str(tmp_log), "--since", "1h"])
    assert "recent_tool" in result.output
    assert "old_tool" not in result.output


def test_audit_filter_until(tmp_path):
    """OPS-02: --until 1h shows only events older than 1 hour."""
    from argus.cli.main import app

    tmp_log = tmp_path / "audit.jsonl"
    events = [
        _make_event("permission", "allowed", "old_tool", minutes_ago=120),
        _make_event("permission", "allowed", "recent_tool", minutes_ago=10),
    ]
    _write_jsonl(tmp_log, events)

    result = runner.invoke(app, ["audit", "--log", str(tmp_log), "--until", "1h"])
    assert "old_tool" in result.output
    assert "recent_tool" not in result.output


def test_audit_filter_no_match_exits_zero(tmp_path):
    """OPS-02: When no events match the filter, exits 0 and reports no matches."""
    from argus.cli.main import app

    tmp_log = tmp_path / "audit.jsonl"
    events = [
        _make_event("permission", "allowed", "read_file"),
    ]
    _write_jsonl(tmp_log, events)

    result = runner.invoke(app, ["audit", "--log", str(tmp_log), "--type", "egress"])
    assert result.exit_code == 0
    assert "No events match" in result.output


# ---------------------------------------------------------------------------
# Dual-format support: gateway audit records (event_type-keyed)
# ---------------------------------------------------------------------------


def test_audit_normalizes_gateway_records(tmp_path):
    """OPS-01: argus audit can render gateway audit.jsonl records (event_type-keyed)."""
    from argus.cli.main import app

    tmp_log = tmp_path / "audit.jsonl"
    events = [
        {"event_type": "tool_call_pre", "agent_role": "analyst", "tool_name": "read_file"},
        {"event_type": "hitl_decision", "approved": False, "tool_name": "delete_db", "tool_input": {}},
    ]
    _write_jsonl(tmp_log, events)

    result = runner.invoke(app, ["audit", "--log", str(tmp_log)])
    assert result.exit_code == 0
    assert "read_file" in result.output
    assert "delete_db" in result.output


def test_audit_filter_type_on_gateway_records(tmp_path):
    """OPS-02: --type filter works on normalized gateway records."""
    from argus.cli.main import app

    tmp_log = tmp_path / "audit.jsonl"
    events = [
        {"event_type": "tool_call_pre", "agent_role": "analyst", "tool_name": "read_file"},
        {"event_type": "hitl_decision", "approved": False, "tool_name": "delete_db", "tool_input": {}},
    ]
    _write_jsonl(tmp_log, events)

    result = runner.invoke(app, ["audit", "--log", str(tmp_log), "--type", "hitl"])
    assert "delete_db" in result.output
    assert "read_file" not in result.output
