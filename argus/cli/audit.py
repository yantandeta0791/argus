"""Argus audit CLI command — streams the JSONL audit log and renders Rich panels.

Implements OPS-01 (display audit events) and OPS-02 (filter by type/severity/time).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator, Optional

import typer
from rich.panel import Panel
from rich import box

from argus.cli.output import console


# ---------------------------------------------------------------------------
# Duration parser
# ---------------------------------------------------------------------------

_DURATION_RE = re.compile(r"^(\d+)(m|h|d)$")


def _parse_duration(s: str) -> datetime:
    """Parse a relative duration string (e.g. '30m', '1h', '2d') to an absolute UTC datetime.

    The returned datetime is ``now() - duration``, i.e. the earliest point in time
    that an event must have to satisfy a ``--since <duration>`` filter.

    Raises:
        typer.BadParameter: if the format does not match ``<N>(m|h|d)``.
    """
    match = _DURATION_RE.match(s)
    if not match:
        raise typer.BadParameter(
            f"Invalid duration '{s}'. Expected format: 30m, 1h, 2d"
        )
    value = int(match.group(1))
    unit = match.group(2)
    delta = {
        "m": timedelta(minutes=value),
        "h": timedelta(hours=value),
        "d": timedelta(days=value),
    }[unit]
    return datetime.now(tz=timezone.utc) - delta


# ---------------------------------------------------------------------------
# Streaming JSONL reader
# ---------------------------------------------------------------------------


def _iter_events(log_path: Path) -> Iterator[dict]:
    """Yield events from a JSONL file one line at a time (streaming — never loads full file)."""
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


# ---------------------------------------------------------------------------
# Severity derivation
# ---------------------------------------------------------------------------

_HIGH_SEVERITY_PAIRS: set[tuple[str, str]] = {
    ("permission", "blocked"),
    ("egress", "blocked"),
    ("redaction", "redacted"),
    ("hitl", "blocked"),
}


def _normalize_event(event: dict) -> dict:
    """Normalize gateway audit records (event_type-keyed) to SecurityEvent shape (gate/outcome).

    If the event already has a 'gate' key, return as-is.  Otherwise, map event_type
    to gate/outcome so that both audit.jsonl and security.jsonl records render correctly.
    """
    if "gate" in event:
        return event
    event_type = event.get("event_type", "")
    mapping = {
        "tool_call_pre": ("audit", "allowed"),
        "tool_call_post": ("audit", "allowed"),
        "hitl_decision": ("hitl", "allowed" if event.get("approved") else "blocked"),
    }
    gate, outcome = mapping.get(event_type, (event_type, "unknown"))
    return {**event, "gate": gate, "outcome": outcome}


def _is_shadow_policy_decision(event: dict) -> bool:
    """Return whether an event belongs in the shadow-policy audit view."""
    return event.get("outcome") == "would_block" or (
        event.get("event_type") == "policy_decision" and event.get("mode") == "shadow"
    )


def _derive_severity(event: dict) -> str:
    """Derive a severity label from gate + outcome.

    Mapping:
    - prompt_shield + blocked -> CRITICAL
    - permission + blocked   -> HIGH
    - egress + blocked       -> HIGH
    - redaction + redacted   -> HIGH
    - hitl + blocked         -> HIGH
    - everything else        -> INFO
    """
    gate = event.get("gate", "")
    outcome = event.get("outcome", "")

    if gate == "prompt_shield" and outcome == "blocked":
        return "CRITICAL"
    if (gate, outcome) in _HIGH_SEVERITY_PAIRS:
        return "HIGH"
    return "INFO"


# ---------------------------------------------------------------------------
# Event filter
# ---------------------------------------------------------------------------


def _parse_event_timestamp(event: dict) -> datetime | None:
    """Parse the event's 'timestamp' field to a timezone-aware UTC datetime."""
    raw = event.get("timestamp")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _matches_filters(
    event: dict,
    type_filter: Optional[str],
    severity: Optional[str],
    since_dt: Optional[datetime],
    until_dt: Optional[datetime],
) -> bool:
    """Return True if the event passes ALL active filters (None means no filter)."""
    if type_filter is not None and event.get("gate") != type_filter:
        return False
    if severity is not None and _derive_severity(event) != severity:
        return False
    if since_dt is not None or until_dt is not None:
        event_ts = _parse_event_timestamp(event)
        if event_ts is None:
            return False
        if since_dt is not None and event_ts < since_dt:
            return False
        if until_dt is not None and event_ts > until_dt:
            return False
    return True


# ---------------------------------------------------------------------------
# Panel renderer
# ---------------------------------------------------------------------------

_OUTCOME_BORDER_COLORS: dict[str, str] = {
    "blocked": "red",
    "allowed": "green",
    "redacted": "yellow",
    "would_block": "#ff8700",
}


def _render_event(event: dict) -> None:
    """Render a single security event as a Rich Panel with outcome-based border color.

    Fields hidden from output: prev_hash, event_id (chain integrity fields).
    """
    outcome = event.get("outcome", "unknown")
    border_color = _OUTCOME_BORDER_COLORS.get(outcome, "dim")

    gate = event.get("gate", "unknown")
    tool_name = event.get("tool_name", "")
    agent_role = event.get("agent_role", "")
    rule_triggered = event.get("rule_triggered", "")

    # Human-readable timestamp
    raw_ts = event.get("timestamp", "")
    try:
        ts_dt = datetime.fromisoformat(raw_ts)
        if ts_dt.tzinfo is None:
            ts_dt = ts_dt.replace(tzinfo=timezone.utc)
        timestamp_str = ts_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, TypeError):
        timestamp_str = raw_ts

    lines = [
        f"[dim]{timestamp_str}[/dim]",
        f"[bold]{gate}[/bold]",
        f"outcome: {outcome}",
    ]
    if tool_name:
        lines.append(f"tool: {tool_name}")
    if agent_role:
        lines.append(f"role: {agent_role}")
    if rule_triggered:
        lines.append(f"rule: {rule_triggered}")
    if event.get("event_type") == "policy_decision":
        lines.append(f"mode: {event.get('mode', '')}")
        lines.append(f"decision: {outcome}")
        if event.get("rule"):
            lines.append(f"rule: {event['rule']}")
        if event.get("reason"):
            lines.append(f"reason: {event['reason']}")
        policy_name = event.get("policy_name")
        policy_version = event.get("policy_version")
        if policy_name and policy_version:
            lines.append(f"policy: {policy_name}@{policy_version}")
        if policy_hash := event.get("policy_hash"):
            lines.append(f"policy_hash: {policy_hash[:12]}")

    content = "\n".join(lines)
    console.print(Panel(content, box=box.ROUNDED, border_style=border_color))


# ---------------------------------------------------------------------------
# Main command
# ---------------------------------------------------------------------------


def audit_command(
    log: Path = typer.Option(
        Path("./runs/security.jsonl"),
        help="Path to JSONL audit log file.",
    ),
    type: Optional[str] = typer.Option(  # noqa: A002
        None,
        "--type",
        help="Filter by gate type (e.g. permission, egress, redaction).",
    ),
    severity: Optional[str] = typer.Option(
        None,
        "--severity",
        help="Filter by severity (CRITICAL, HIGH, INFO).",
    ),
    since: Optional[str] = typer.Option(
        None,
        "--since",
        help="Show only events newer than this duration ago (e.g. 1h, 30m, 2d).",
    ),
    until: Optional[str] = typer.Option(
        None,
        "--until",
        help="Show only events older than this duration ago (e.g. 1h, 30m, 2d).",
    ),
    shadow: bool = typer.Option(
        False, "--shadow", help="Show shadow policy decisions."
    ),
) -> None:
    """Stream and render the Argus JSONL audit log as Rich panels."""
    # Resolve log existence and emptiness
    if not log.exists() or log.stat().st_size == 0:
        console.print("No audit events found. Run `argus run` to generate events.")
        return

    # Parse time filters
    since_dt: Optional[datetime] = None
    until_dt: Optional[datetime] = None
    if since is not None:
        since_dt = _parse_duration(since)
    if until is not None:
        until_dt = _parse_duration(until)

    matched_count = 0
    for raw_event in _iter_events(log):
        event = _normalize_event(raw_event)
        if shadow and not _is_shadow_policy_decision(event):
            continue
        if _matches_filters(event, type, severity, since_dt, until_dt):
            _render_event(event)
            matched_count += 1

    if matched_count == 0:
        # Could be empty file (handled above) or zero-match filter
        console.print("No events match your filter")
