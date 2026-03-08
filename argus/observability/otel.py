"""
OtelEmitter and FileSpanExporter — OpenTelemetry span emission (OBS-02).

Emits spans with gen_ai.* semantic convention attributes for LLM calls and
argus.* attributes for state transitions.

CRITICAL: gen_ai.* constants are NOT available in opentelemetry-semantic-conventions
0.61b0 — use the module-level raw string constants defined here.

CRITICAL: Uses a LOCAL TracerProvider per ObservabilityManager instance.
Do NOT call trace.set_tracer_provider() — that pollutes global state.
"""

from __future__ import annotations

from pathlib import Path

from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)

# Raw string constants — gen_ai.* semconv not yet in opentelemetry-semantic-conventions 0.61b0
_GEN_AI_SYSTEM = "gen_ai.system"
_GEN_AI_REQUEST_MODEL = "gen_ai.request.model"
_GEN_AI_RESPONSE_MODEL = "gen_ai.response.model"
_GEN_AI_OPERATION_NAME = "gen_ai.operation.name"
_GEN_AI_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
_GEN_AI_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
_ARGUS_STATE_FROM = "argus.state.from"
_ARGUS_STATE_TO = "argus.state.to"
_ARGUS_RUN_ID = "argus.run_id"
_ARGUS_STATE = "argus.state"


class FileSpanExporter(SpanExporter):
    """Writes each finished span as a compact JSON line to a .jsonl file.

    span.to_json(indent=None) produces OTLP-compatible JSON — collectors like
    Jaeger, Zipkin-OTLP, and OTel Collector (file receiver) can ingest it.
    """

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(path, "a", encoding="utf-8")

    def export(self, spans) -> SpanExportResult:
        try:
            for span in spans:
                self._file.write(span.to_json(indent=None) + "\n")
            self._file.flush()
            return SpanExportResult.SUCCESS
        except Exception:
            return SpanExportResult.FAILURE

    def shutdown(self) -> None:
        try:
            self._file.flush()
            self._file.close()
        except Exception:
            pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        try:
            self._file.flush()
            return True
        except Exception:
            return False


class OtelEmitter:
    """Emits OpenTelemetry spans using a local TracerProvider.

    Uses SimpleSpanProcessor (synchronous — no background thread).
    Each ObservabilityManager instance owns its own TracerProvider; global
    OTel state is never modified.
    """

    def __init__(self, service_name: str, exporter: SpanExporter) -> None:
        resource = Resource.create({SERVICE_NAME: service_name})
        self._provider = TracerProvider(resource=resource)
        self._provider.add_span_processor(SimpleSpanProcessor(exporter))
        self._tracer = self._provider.get_tracer("argus.otel")

    def emit_llm_call(
        self,
        model: str,
        state: str,
        input_tokens: int,
        output_tokens: int,
        run_id: str,
    ) -> None:
        """Emit a gen_ai.client.operation span for an LLM call (OBS-02)."""
        with self._tracer.start_as_current_span("gen_ai.client.operation") as span:
            span.set_attribute(_GEN_AI_SYSTEM, "anthropic")
            span.set_attribute(_GEN_AI_OPERATION_NAME, "chat")
            span.set_attribute(_GEN_AI_REQUEST_MODEL, model)
            span.set_attribute(_GEN_AI_RESPONSE_MODEL, model)
            span.set_attribute(_GEN_AI_USAGE_INPUT_TOKENS, input_tokens)
            span.set_attribute(_GEN_AI_USAGE_OUTPUT_TOKENS, output_tokens)
            span.set_attribute(_ARGUS_RUN_ID, run_id)
            span.set_attribute(_ARGUS_STATE, state)

    def emit_state_transition(self, from_state, to_state, run_id: str) -> None:
        """Emit an argus.state_transition span (OBS-02)."""
        with self._tracer.start_as_current_span("argus.state_transition") as span:
            span.set_attribute(_ARGUS_STATE_FROM, str(from_state))
            span.set_attribute(_ARGUS_STATE_TO, str(to_state))
            span.set_attribute(_ARGUS_RUN_ID, run_id)

    def flush(self) -> None:
        """Flush and shut down the provider. Call once at manager.flush() time."""
        try:
            self._provider.force_flush()
            self._provider.shutdown()
        except Exception:
            pass
