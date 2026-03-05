"""
Tool contract system — Pydantic schema validation, tenacity retry, circuit breaker.
Full implementation in plan 02-04.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Type
from pydantic import BaseModel


@dataclass
class ToolManifest:
    name: str
    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel]
    idempotent: bool = True
    max_attempts: int = 3
    backoff_base: float = 1.0
    failure_threshold: int = 5
    recovery_timeout: int = 30


class ToolRunner:
    """Wraps a tool callable with schema validation, retry, and circuit breaker."""

    def __init__(self, manifest: ToolManifest, tool_fn, gateway):
        raise NotImplementedError("ToolRunner implemented in plan 02-04")

    async def call(self, agent_role: str, raw_input: dict[str, Any]) -> Any:
        raise NotImplementedError("ToolRunner implemented in plan 02-04")
