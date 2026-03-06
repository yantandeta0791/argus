"""
State types for the Argus execution engine.

TaskState   — 5-state StrEnum + ABORT terminal state (STM-01, STM-02)
RunContext  — working memory for one task run; deepcopy-safe for rollback (STM-03)
RunResult   — structured result returned to caller after run completes or aborts
LLMCallable — Protocol interface for state handlers; Phase 3 injects the real router

Design invariant: No LLM output ever selects a transition. TaskState members are
the only valid states; TRANSITION_SEQUENCE in machine.py is the only valid order.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, TYPE_CHECKING, runtime_checkable

if TYPE_CHECKING:
    from argus.llm.tracker import StateCostEntry


class TaskState(StrEnum):
    """Valid states for the Argus execution engine.

    PLAN through COMMIT form the normal forward sequence (STM-01).
    ABORT is the terminal error/cost-exceeded state (STM-03, STM-04).
    """
    PLAN = "PLAN"
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"
    REFLECT = "REFLECT"
    COMMIT = "COMMIT"
    ABORT = "ABORT"


@dataclass
class RunContext:
    """Working memory for one task run.

    Mutated in-place by state handlers. The StateMachine takes a deepcopy
    before the run begins; on failure it restores artifacts from that snapshot
    (STM-03 in-memory rollback). All fields must be deepcopy-compatible.
    """
    task_id: str
    task_input: dict[str, Any]
    artifacts: dict[str, Any] = field(default_factory=dict)
    current_state: TaskState = TaskState.PLAN
    error: Exception | None = None


@dataclass
class RunResult:
    """Structured result returned to the caller after a run ends.

    final_state == COMMIT  → success
    final_state == ABORT   → cost-budget abort (STM-04)
    any other state        → failure in that state (STM-03)
    """
    task_id: str
    final_state: TaskState
    artifacts: dict[str, Any]
    error: str | None = None
    success: bool = True
    cost_breakdown: list["StateCostEntry"] = field(default_factory=list)  # Phase 3: per-state cost records


@runtime_checkable
class LLMCallable(Protocol):
    """Protocol for injectable LLM callable.

    Phase 2 state handlers receive a stub that returns a fixed dict.
    Phase 3 replaces the stub with the real LiteLLM-backed router.
    The state machine never inspects the return value to decide transitions —
    transitions are always the static TRANSITION_SEQUENCE (STM-02).
    """
    async def __call__(self, context: RunContext) -> dict[str, Any]: ...
