"""
ObservabilityManager — central coordinator for all observability sinks (OBS-01..04).

Coordinates:
  - TraceWriter (JSONL execution trace, OBS-01/03)
  - SecurityEventWriter (separate security event stream, OBS-04)
  - OtelEmitter (OpenTelemetry spans, OBS-02)

All on_* methods:
  - Are no-ops when config.enabled=False
  - Are wrapped in try/except — observability failures never crash the agent
  - Are synchronous (StateMachine runs in single async event loop, no locking needed)

run_id is a uuid4 generated once at construction time, shared across all sinks.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from argus.observability.otel import FileSpanExporter, OtelEmitter
from argus.observability.security_stream import SecurityEventWriter
from argus.observability.trace import TraceEvent, TraceWriter


@dataclass
class ObsConfig:
    """Configuration for ObservabilityManager.

    All paths default to None — sinks are disabled unless a path is provided.
    enabled=False disables all sinks without removing the manager from call sites.
    """
    trace_path: "Path | None" = None
    security_stream_path: "Path | None" = None
    otel_spans_path: "Path | None" = None
    service_name: str = "argus"
    enabled: bool = True


class ObservabilityManager:
    """Coordinates execution trace, security stream, and OTel spans.

    Inject as: StateMachine(obs=mgr), LLMRouter(obs=mgr), SecurityGateway(obs=mgr).
    All sinks are optional — None paths result in no I/O for that sink.
    """

    def __init__(self, config: ObsConfig) -> None:
        self._config = config
        self._run_id = str(uuid.uuid4())

        if not config.enabled:
            # No-op mode — no sinks opened, no files created
            self._trace_writer = None
            self._sec_writer = SecurityEventWriter(None)
            self._otel = OtelEmitter(service_name=config.service_name, exporter=InMemorySpanExporter())
            return

        # Construct sinks based on config paths
        self._trace_writer: TraceWriter | None = (
            TraceWriter(config.trace_path) if config.trace_path is not None else None
        )
        self._sec_writer = SecurityEventWriter(config.security_stream_path)

        # OtelEmitter always constructed — use InMemorySpanExporter as no-op when no path
        if config.otel_spans_path is not None:
            exporter = FileSpanExporter(config.otel_spans_path)
        else:
            exporter = InMemorySpanExporter()
        self._otel = OtelEmitter(service_name=config.service_name, exporter=exporter)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def on_state_transition(
        self,
        from_state: Any,
        to_state: Any,
        context: Any,
        duration_ms: float,
    ) -> None:
        """Trace state transition + emit OTel span."""
        try:
            if not self._config.enabled:
                return
            task_id = getattr(context, "task_id", None)
            if self._trace_writer is not None:
                self._trace_writer.write(TraceEvent(
                    event_type="state_transition",
                    timestamp=self._now(),
                    run_id=self._run_id,
                    payload={
                        "from": str(from_state),
                        "to": str(to_state),
                        "duration_ms": duration_ms,
                        "task_id": task_id,
                    },
                ))
            self._otel.emit_state_transition(from_state, to_state, self._run_id)
        except Exception:
            pass  # observability failure never crashes the agent

    def on_tool_call(
        self,
        manifest: Any,
        input_data: Any,
        output_data: Any,
        duration_ms: float,
        error: Any = None,
    ) -> None:
        """Trace a tool call outcome (input/output omitted — may contain secrets)."""
        try:
            if not self._config.enabled:
                return
            tool_name = getattr(manifest, "name", str(manifest))
            if self._trace_writer is not None:
                self._trace_writer.write(TraceEvent(
                    event_type="tool_call",
                    timestamp=self._now(),
                    run_id=self._run_id,
                    payload={
                        "tool": tool_name,
                        "success": error is None,
                        "duration_ms": duration_ms,
                        "error": str(error) if error is not None else None,
                    },
                ))
        except Exception:
            pass

    def on_llm_call(
        self,
        model: str,
        state: str,
        usage: dict,
        cost_usd: float,
        duration_ms: float,
    ) -> None:
        """Trace an LLM call + emit OTel gen_ai span."""
        try:
            if not self._config.enabled:
                return
            input_tokens = usage.get("input", 0)
            output_tokens = usage.get("output", 0)
            if self._trace_writer is not None:
                self._trace_writer.write(TraceEvent(
                    event_type="llm_call",
                    timestamp=self._now(),
                    run_id=self._run_id,
                    payload={
                        "model": model,
                        "state": state,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cost_usd": cost_usd,
                        "duration_ms": duration_ms,
                    },
                ))
            self._otel.emit_llm_call(
                model=model,
                state=state,
                input_tokens=int(input_tokens),
                output_tokens=int(output_tokens),
                run_id=self._run_id,
            )
        except Exception:
            pass

    def on_security_event(self, event: Any) -> None:
        """Forward a SecurityEvent to the separate security stream."""
        try:
            if not self._config.enabled:
                return
            if event is not None:
                self._sec_writer.write(event)
        except Exception:
            pass

    def on_run_complete(self, result: Any) -> None:
        """Write run_complete TraceEvent with embedded cost_breakdown (OBS-03)."""
        try:
            if not self._config.enabled:
                return
            if self._trace_writer is None:
                return
            cost_breakdown = getattr(result, "cost_breakdown", []) or []
            # Normalize StateCostEntry objects to dicts if needed
            normalized = []
            for entry in cost_breakdown:
                if isinstance(entry, dict):
                    normalized.append(entry)
                else:
                    # StateCostEntry dataclass — convert to dict
                    import dataclasses as dc
                    normalized.append(dc.asdict(entry) if dc.is_dataclass(entry) else vars(entry))
            total_cost = sum(e.get("cost_usd", 0.0) for e in normalized)
            self._trace_writer.write(TraceEvent(
                event_type="run_complete",
                timestamp=self._now(),
                run_id=self._run_id,
                payload={
                    "final_state": str(getattr(result, "final_state", "unknown")),
                    "total_cost_usd": total_cost,
                    "cost_breakdown": normalized,
                    "duration_ms": 0.0,  # caller may override if needed
                    "error": getattr(result, "error", None),
                },
            ))
        except Exception:
            pass

    def flush(self) -> None:
        """Flush all active sinks. Call after run completion."""
        try:
            if self._trace_writer is not None:
                self._trace_writer.flush()
            self._sec_writer.flush()
            self._otel.flush()
        except Exception:
            pass
