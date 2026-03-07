"""
SecurityEventWriter — separate JSONL sink for security events (OBS-04).

Writes SecurityEvent objects to a dedicated JSONL file, independent of the
execution trace. Callers can consume the security stream without any knowledge
of the trace format or trace file path.

path=None silently discards all events — no exceptions raised.
"""
from __future__ import annotations

from pathlib import Path

from argus.security.events import SecurityEvent


class SecurityEventWriter:
    """Writes SecurityEvent objects to a separate JSONL file.

    Each line is SecurityEvent.model_dump_json() — Pydantic v2 serialization
    that handles datetime -> ISO-8601 string conversion correctly.

    If path is None, all operations are no-ops (events are silently discarded).
    """

    def __init__(self, path: "Path | None") -> None:
        self._file = None
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(path, "a", encoding="utf-8")

    def write(self, event: SecurityEvent) -> None:
        """Append a SecurityEvent as a JSON line. No-op if path was None."""
        if self._file is None:
            return
        self._file.write(event.model_dump_json() + "\n")
        self._file.flush()

    def flush(self) -> None:
        """Flush buffered data to disk. No-op if path was None."""
        if self._file is not None:
            self._file.flush()
