"""
Tool contract system for the Argus execution engine.

ToolManifest  — declares tool name, input/output schemas, and resilience config
ToolRunner    — wraps every tool call with:
                  1. Pydantic v2 input schema validation (TOOL-01, pre-execution)
                  2. SecurityGateway.pre_tool_call (ArgusSecurityError -> re-raise)
                  3. tenacity AsyncRetrying with exponential backoff (TOOL-02)
                  4. Module-level circuit breaker by tool name (TOOL-03)
                  5. TOOL-04: idempotent=False -> no retry on ambiguous failures
                  6. SecurityGateway.post_tool_call on clean string (re-raise on error)
                  7. Pydantic v2 output schema validation (TOOL-01, post-return)

Circuit breaker scope: module-level registry keyed by tool_name ensures failure
counts persist across ToolRunner instances (avoids per-instance counter reset pitfall
documented in 02-RESEARCH.md section Pitfall 1).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Type

from pydantic import BaseModel
from tenacity import (
    AsyncRetrying,
    retry_if_not_exception_type,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from circuitbreaker import circuit, CircuitBreakerError  # noqa: F401 (re-exported for tests)

# Ambiguous failures — non-idempotent tools must NOT retry these (TOOL-04)
# The call may have already succeeded; retry would duplicate the side-effect.
AMBIGUOUS_EXCEPTIONS = (TimeoutError, ConnectionError, OSError)

# Module-level circuit breaker registry.
# Key: tool_name. Value: async wrapper function decorated with @circuit once.
# ToolRunner.call() routes through this registry, not through a per-instance method.
_CIRCUIT_REGISTRY: dict[str, Callable] = {}


def _make_circuit_wrapper(
    tool_name: str, failure_threshold: int, recovery_timeout: int
) -> Callable:
    """Create and register a circuit-breaker-wrapped async caller for a tool name.

    Called once per unique (tool_name, failure_threshold, recovery_timeout) combination.
    The @circuit decorator is applied at definition time — failure counts persist
    across all ToolRunner instances that share the same tool_name.
    """

    @circuit(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exception=Exception,
        name=tool_name,
    )
    async def _protected(tool_fn: Callable, validated_input: BaseModel) -> Any:
        return await tool_fn(validated_input)

    return _protected


@dataclass
class ToolManifest:
    """Declares the contract and resilience config for one tool.

    Fields:
        name:               Tool identifier used in audit logs and circuit breaker registry.
        input_schema:       Pydantic BaseModel subclass. Validated before execution (TOOL-01).
        output_schema:      Pydantic BaseModel subclass. Validated after return (TOOL-01).
        idempotent:         True (default) — retry on any exception. False — skip retry
                            on AMBIGUOUS_EXCEPTIONS (TOOL-04).
        max_attempts:       Maximum retry attempts including first call (TOOL-02).
        backoff_base:       Multiplier for wait_exponential in seconds (TOOL-02).
        failure_threshold:  Consecutive failures before circuit opens (TOOL-03).
        recovery_timeout:   Seconds before half-open probe attempt (TOOL-03).
    """

    name: str
    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel]
    idempotent: bool = True
    max_attempts: int = 3
    backoff_base: float = 1.0
    failure_threshold: int = 5
    recovery_timeout: int = 30


class ToolRunner:
    """Runs a tool callable through the full validation + resilience + security pipeline.

    One ToolRunner per tool per StateMachine instance. Holds a reference to the
    module-level circuit breaker wrapper — failure counts persist across calls.

    Args:
        manifest:  ToolManifest declaring the contract and resilience config.
        tool_fn:   Async callable: (validated_input: BaseModel) -> dict[str, Any].
                   Receives the Pydantic-validated input model, not the raw dict.
        gateway:   SecurityGateway. pre_tool_call and post_tool_call wrap execution.
                   ArgusSecurityError from either gate propagates immediately (not caught here).
        obs:       ObservabilityManager (optional). on_tool_call() emitted after each call.
                   None = no-op. Never raises.
    """

    def __init__(
        self, manifest: ToolManifest, tool_fn: Callable, gateway: Any, obs: Any = None
    ) -> None:
        self._manifest = manifest
        self._tool_fn = tool_fn
        self._gateway = gateway
        self._obs = obs

        # Ensure one circuit breaker wrapper exists for this tool name (module-level)
        if manifest.name not in _CIRCUIT_REGISTRY:
            _CIRCUIT_REGISTRY[manifest.name] = _make_circuit_wrapper(
                tool_name=manifest.name,
                failure_threshold=manifest.failure_threshold,
                recovery_timeout=manifest.recovery_timeout,
            )
        self._circuit_call = _CIRCUIT_REGISTRY[manifest.name]

    async def call(self, agent_role: str, raw_input: dict[str, Any]) -> BaseModel:
        """Execute the tool through the full pipeline.

        Pipeline order:
          1. Pydantic input validation (raises ValidationError on mismatch — TOOL-01)
          2. SecurityGateway.pre_tool_call (raises ArgusSecurityError -> caller handles)
          3. tenacity retry + circuitbreaker execution (TOOL-02, TOOL-03, TOOL-04)
          4. SecurityGateway.post_tool_call on string output (raises ArgusSecurityError -> caller handles)
          5. Pydantic output validation (raises ValidationError on mismatch — TOOL-01)

        Returns:
            Instance of manifest.output_schema (validated Pydantic model).

        Raises:
            pydantic.ValidationError:  Input or output schema mismatch.
            ArgusSecurityError:        Security gate violation (re-raised, not caught).
            CircuitBreakerError:       Circuit is open — subsequent calls fail fast (TOOL-03).
            Exception:                 Original tool exception after max retry attempts.
        """
        import time as _time

        # Step 1: Validate input before calling anything (TOOL-01)
        validated_input = self._manifest.input_schema.model_validate(raw_input)

        # Step 2: Security pre-call gate (ArgusSecurityError propagates up — not caught here)
        self._gateway.pre_tool_call(
            agent_role,
            self._manifest.name,
            validated_input.model_dump(),
        )

        # Step 3: Execute with retry + circuit breaker (time for observability)
        _t0 = _time.monotonic()
        _error: Exception | None = None
        try:
            raw_output = await self._execute_with_resilience(validated_input)
        except Exception as exc:
            _error = exc
            _duration_ms = (_time.monotonic() - _t0) * 1000
            if self._obs is not None:
                try:
                    self._obs.on_tool_call(
                        self._manifest,
                        validated_input.model_dump(),
                        None,
                        _duration_ms,
                        error=str(exc),
                    )
                except Exception:
                    pass
            raise

        _duration_ms = (_time.monotonic() - _t0) * 1000

        # Step 4: Security post-call gate on string representation (TOOL-01 output must be clean)
        output_str = (
            json.dumps(raw_output) if isinstance(raw_output, dict) else str(raw_output)
        )
        clean_str = self._gateway.post_tool_call(output_str)

        # Reconstruct dict from cleaned string for output validation
        try:
            clean_dict = json.loads(clean_str)
        except (json.JSONDecodeError, TypeError):
            clean_dict = {"result": clean_str}

        # Step 5: Validate output schema before result enters agent context (TOOL-01)
        result = self._manifest.output_schema.model_validate(clean_dict)

        # Emit tool_call event to observability sink (OBS-01)
        if self._obs is not None:
            try:
                self._obs.on_tool_call(
                    self._manifest,
                    validated_input.model_dump(),
                    clean_dict,
                    _duration_ms,
                )
            except Exception:
                pass

        return result

    async def _execute_with_resilience(self, validated_input: BaseModel) -> Any:
        """Run tool_fn with tenacity retry (outer) and circuit breaker (inner).

        Retry conditions (TOOL-04):
          idempotent=True  -> retry on any Exception
          idempotent=False -> skip retry on AMBIGUOUS_EXCEPTIONS (may already have succeeded)

        Circuit breaker (TOOL-03):
          Opens after failure_threshold consecutive failures (module-level counter).
          Half-open probe after recovery_timeout seconds.
          Open circuit raises CircuitBreakerError immediately without calling tool_fn.
        """
        if self._manifest.idempotent:
            retry_condition = retry_if_exception_type(Exception)
        else:
            # Non-idempotent: do NOT retry on ambiguous failures (TOOL-04)
            retry_condition = retry_if_not_exception_type(AMBIGUOUS_EXCEPTIONS)

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self._manifest.max_attempts),
            wait=wait_exponential(
                multiplier=self._manifest.backoff_base,
                min=self._manifest.backoff_base,
                max=60,
            ),
            retry=retry_condition,
            reraise=True,  # propagate original exception, not RetryError (see research pitfall 2)
        ):
            with attempt:
                # Circuit breaker is the innermost layer — failure counts tracked at module level
                return await self._circuit_call(self._tool_fn, validated_input)
