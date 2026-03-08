"""
Argus observability package — pure sink layer for execution traces, OTel spans,
and security event stream.

Public API (7 symbols):
    ObsConfig              — configuration dataclass for ObservabilityManager
    ObservabilityManager   — central coordinator (inject into StateMachine/LLMRouter/SecurityGateway)
    TraceEvent             — structured trace event dataclass
    TraceWriter            — JSONL writer for execution trace
    SecurityEventWriter    — JSONL writer for security event stream (OBS-04)
    OtelEmitter            — OpenTelemetry span emitter (OBS-02)
    FileSpanExporter       — SpanExporter that writes compact JSON lines to .jsonl
"""

from argus.observability.manager import ObsConfig, ObservabilityManager
from argus.observability.trace import TraceEvent, TraceWriter
from argus.observability.security_stream import SecurityEventWriter
from argus.observability.otel import OtelEmitter, FileSpanExporter

__all__ = [
    "ObsConfig",
    "ObservabilityManager",
    "TraceEvent",
    "TraceWriter",
    "SecurityEventWriter",
    "OtelEmitter",
    "FileSpanExporter",
]
