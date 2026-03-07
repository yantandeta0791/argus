"""SecurityEventWriter — separate JSONL sink for OBS-04 — stub."""
from __future__ import annotations
from pathlib import Path


class SecurityEventWriter:
    def __init__(self, path: "Path | None") -> None:
        raise NotImplementedError

    def write(self, event) -> None:
        raise NotImplementedError

    def flush(self) -> None:
        raise NotImplementedError
