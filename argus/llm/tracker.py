"""
SpendTracker -- in-memory per-run cost accumulator for Argus.

StateCostEntry  -- per-state cost record (state, model, tokens, cost_usd)
SpendTracker    -- accumulates entries; provides over_budget() as cost_hook

Design:
- Instantiate ONE SpendTracker per StateMachine.run() call (fresh-per-run).
  This avoids task spend leaking across tasks.
- Phase 4 provides daily_spend_usd at construction time from SQLite.
  The CLI layer loads today's cumulative spend before creating SpendTracker.
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
        tracker = SpendTracker(config.spend, daily_spend_usd=loaded_from_sqlite)
        machine = StateMachine(..., cost_hook=tracker.over_budget, ...)

    Args:
        config: SpendConfig with per_task_usd, per_session_usd, per_day_usd caps.
        daily_spend_usd: Pre-loaded daily cumulative spend from SQLite (Phase 4).
            Defaults to 0.0 when memory is not configured.
    """

    def __init__(self, config: SpendConfig, daily_spend_usd: float = 0.0) -> None:
        self._config = config
        self._task_spend: float = 0.0
        self._session_spend: float = 0.0
        self._daily_spend: float = daily_spend_usd
        self._entries: list[StateCostEntry] = []
        if config.per_day_usd is not None:
            logger.debug(
                "per_day_usd=%.4f, pre-loaded daily spend=%.4f",
                config.per_day_usd,
                daily_spend_usd,
            )

    def record(self, entry: StateCostEntry) -> None:
        """Record a StateCostEntry and accumulate spend totals."""
        self._entries.append(entry)
        self._task_spend += entry.cost_usd
        self._session_spend += entry.cost_usd

    def over_budget(self) -> bool:
        """Return True if any configured cap is exceeded.

        Synchronous -- matches StateMachine cost_hook: Callable[[], bool].
        Checks per_task_usd, per_session_usd, and per_day_usd (Phase 4).
        Daily check: (daily_spend + session_spend) >= per_day_usd.
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
        if (
            self._config.per_day_usd is not None
            and (self._daily_spend + self._session_spend) >= self._config.per_day_usd
        ):
            return True
        return False

    def entries(self) -> list[StateCostEntry]:
        """Return a copy of all recorded entries (insertion order preserved)."""
        return list(self._entries)
