"""
State types for the Argus execution engine.

TaskState: 5-state enum + ABORT terminal state (STM-01, STM-02)
RunContext: working memory for one task run; rolled back on failure (STM-03)
RunResult: structured result returned to caller after run completes or aborts
LLMCallable: Protocol interface injected by Phase 3; stub in Phase 2

Full implementation in plan 02-02.
"""
from __future__ import annotations
from enum import StrEnum
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


class TaskState(StrEnum):
    PLAN = "PLAN"
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"
    REFLECT = "REFLECT"
    COMMIT = "COMMIT"
    ABORT = "ABORT"


@dataclass
class RunContext:
    task_id: str
    task_input: dict[str, Any]
    artifacts: dict[str, Any] = field(default_factory=dict)
    current_state: TaskState = TaskState.PLAN
    error: Exception | None = None


@dataclass
class RunResult:
    task_id: str
    final_state: TaskState
    artifacts: dict[str, Any]
    error: str | None = None
    success: bool = True


@runtime_checkable
class LLMCallable(Protocol):
    async def __call__(self, context: RunContext) -> dict[str, Any]: ...
