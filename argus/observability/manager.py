"""ObservabilityManager and ObsConfig — stub."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ObsConfig:
    trace_path: "Path | None" = None
    security_stream_path: "Path | None" = None
    otel_spans_path: "Path | None" = None
    service_name: str = "argus"
    enabled: bool = True


class ObservabilityManager:
    def __init__(self, config: ObsConfig) -> None:
        raise NotImplementedError

    def on_state_transition(self, from_state, to_state, context, duration_ms: float) -> None:
        raise NotImplementedError

    def on_tool_call(self, manifest, input_data, output_data, duration_ms: float, error=None) -> None:
        raise NotImplementedError

    def on_llm_call(self, model: str, state: str, usage: dict, cost_usd: float, duration_ms: float) -> None:
        raise NotImplementedError

    def on_security_event(self, event) -> None:
        raise NotImplementedError

    def on_run_complete(self, result) -> None:
        raise NotImplementedError

    def flush(self) -> None:
        raise NotImplementedError
