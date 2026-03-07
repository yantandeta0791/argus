"""OtelEmitter and FileSpanExporter — stub."""
from __future__ import annotations
from pathlib import Path


class FileSpanExporter:
    def __init__(self, path: Path) -> None:
        raise NotImplementedError

    def export(self, spans) -> object:
        raise NotImplementedError

    def shutdown(self) -> None:
        raise NotImplementedError

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        raise NotImplementedError


class OtelEmitter:
    def __init__(self, service_name: str, exporter) -> None:
        raise NotImplementedError

    def emit_llm_call(self, model: str, state: str, input_tokens: int,
                      output_tokens: int, run_id: str) -> None:
        raise NotImplementedError

    def emit_state_transition(self, from_state, to_state, run_id: str) -> None:
        raise NotImplementedError

    def flush(self) -> None:
        raise NotImplementedError
