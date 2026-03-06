"""
SpendTracker -- in-memory per-run cost accumulator for Argus.

StateCostEntry  -- per-state cost record (state, model, tokens, cost_usd)
SpendTracker    -- accumulates entries; provides over_budget() as cost_hook

Design:
- Instantiate ONE SpendTracker per StateMachine.run() call (fresh-per-run).
  This avoids task spend leaking across tasks.
- per_day_usd cap is NOT enforced -- SpendTracker is in-memory; cross-run
  enforcement requires Phase 4 SQLite persistence. A warning is logged when
  per_day_usd is configured so users know enforcement is deferred.
- over_budget() is synchronous -- matches StateMachine.cost_hook signature
  exactly: Callable[[], bool]
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from argus.llm.config import SpendConfig

logger = logging.getLogger(__name__)


@dataclass
class StateCostEntry:
    """Cost record for one LLM call in one state."""
    state: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class SpendTracker:
    """Accumulates LLM call costs for one StateMachine run.

    Instantiate once per run. Pass over_budget as the cost_hook to StateMachine:
        tracker = SpendTracker(config.spend)
        machine = StateMachine(..., cost_hook=tracker.over_budget, ...)
    """

    def __init__(self, config: SpendConfig) -> None:
        self._config = config
        self._task_spend: float = 0.0
        self._session_spend: float = 0.0
        self._entries: list[StateCostEntry] = []
        if config.per_day_usd is not None:
            logger.warning(
                "per_day_usd cap configured but NOT enforced in Phase 3 -- "
                "cross-run enforcement requires Phase 4 SQLite persistence. "
                "Configure per_task_usd or per_session_usd for immediate enforcement."
            )

    def record(self, entry: StateCostEntry) -> None:
        """Record a StateCostEntry and accumulate spend totals."""
        self._entries.append(entry)
        self._task_spend += entry.cost_usd
        self._session_spend += entry.cost_usd

    def over_budget(self) -> bool:
        """Return True if any configured cap is exceeded.

        Synchronous -- matches StateMachine cost_hook: Callable[[], bool].
        per_day_usd is not checked (see module docstring).
        """
        if (
            self._config.per_task_usd is not None
            and self._task_spend >= self._config.per_task_usd
        ):
            return True
        if (
            self._config.per_session_usd is not None
            and self._session_spend >= self._config.per_session_usd
        ):
            return True
        return False

    def entries(self) -> list[StateCostEntry]:
        """Return a copy of all recorded entries (insertion order preserved)."""
        return list(self._entries)
