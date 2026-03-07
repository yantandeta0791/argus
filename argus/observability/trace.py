"""TraceEvent schema and JSONL writer — stub."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TraceEvent:
    event_type: str   # "state_transition" | "tool_call" | "llm_call" | "run_complete"
    timestamp: str    # ISO-8601 UTC
    run_id: str       # uuid4
    payload: dict     # event-specific fields


class TraceWriter:
    def __init__(self, path: Path) -> None:
        raise NotImplementedError

    def write(self, event: TraceEvent) -> None:
        raise NotImplementedError

    def flush(self) -> None:
        raise NotImplementedError
