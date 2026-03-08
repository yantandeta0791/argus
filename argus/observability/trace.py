"""
TraceEvent schema and JSONL execution trace writer.

Provides the structured execution trace (OBS-01) and cost reporting (OBS-03).
Each TraceEvent is written as a single compact JSON line to a .jsonl file.
The run_complete event embeds cost_breakdown — cost readable from trace alone.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TraceEvent:
    """Single event in the execution trace.

    event_type values:
        "state_transition" — payload: {from, to, duration_ms, task_id}
        "tool_call"        — payload: {tool, success, duration_ms, error}
                            (input/output omitted — may contain secrets)
        "llm_call"         — payload: {model, state, input_tokens, output_tokens,
                                       cost_usd, duration_ms}
        "run_complete"     — payload: {final_state, total_cost_usd, cost_breakdown,
                                       duration_ms, error}
                            cost_breakdown is list[dict] satisfying OBS-03
    """

    event_type: str  # "state_transition" | "tool_call" | "llm_call" | "run_complete"
    timestamp: str  # ISO-8601 UTC — datetime.now(timezone.utc).isoformat()
    run_id: str  # uuid4 — set once per ObservabilityManager instance
    payload: dict  # event-specific fields (see event_type docs above)


class TraceWriter:
    """Writes TraceEvent objects to a JSONL file.

    Opens the file once at construction. Flushes after every write for durability.
    Creates parent directories automatically.
    """

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(path, "a", encoding="utf-8")

    def write(self, event: TraceEvent) -> None:
        """Serialize event to JSON and append as a single line."""
        self._file.write(json.dumps(dataclasses.asdict(event)) + "\n")
        self._file.flush()

    def flush(self) -> None:
        """Ensure all buffered data is written to disk."""
        self._file.flush()
