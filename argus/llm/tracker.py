"""
SpendTracker: in-memory per-run cost accumulator.
Provides cost_hook factory (Callable[[], bool]) for StateMachine.
StateCostEntry: per-state cost record stored in RunResult.cost_breakdown.
Implemented in Plan 03-02.
"""
from __future__ import annotations

from dataclasses import dataclass

from argus.llm.config import SpendConfig


@dataclass
class StateCostEntry:
    state: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class SpendTracker:
    def __init__(self, config: SpendConfig) -> None:
        raise NotImplementedError("Plan 03-02 implements SpendTracker")

    def record(self, entry: StateCostEntry) -> None:
        raise NotImplementedError

    def over_budget(self) -> bool:
        raise NotImplementedError

    def entries(self) -> list[StateCostEntry]:
        raise NotImplementedError
