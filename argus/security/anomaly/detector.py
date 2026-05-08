"""
AnomalyDetector — EWMA + z-score statistical anomaly detection engine.

Provides per-agent sliding windows with time-based eviction, EWMA baseline
tracking, and graduated response levels (OK / WARN / ESCALATE / BLOCK).

Design:
- All state is in-process (deque + dict) — no external deps
- Uses stdlib statistics.stdev — no scipy/numpy required
- Per-agent windows are completely isolated — agent-A baseline never affects agent-B
- Window eviction uses time.monotonic() — not wall clock (monotonic is stable)

Phase 10 Plan 01: Core engine. Integration into SecurityGateway gates is Plan 02.
"""

from __future__ import annotations

import statistics
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ResponseLevel(str, Enum):
    """Graduated response level returned by AnomalyDetector.record_and_check."""

    OK = "ok"
    WARN = "warn"
    ESCALATE = "escalate"
    BLOCK = "block"


@dataclass
class AnomalyConfig:
    """Configuration for the anomaly detection engine.

    Defaults are calibrated for typical agent tool-call frequency patterns.
    All thresholds are z-score multiples of the per-agent rolling stdev.
    """

    enabled: bool = True
    window_seconds: int = 60  # Sliding window duration in seconds
    min_observations: int = (
        10  # Warmup period — suppress detection until this many calls
    )
    warn_z: float = 2.0  # z-score >= warn_z  → WARN
    escalate_z: float = 3.0  # z-score >= escalate_z → ESCALATE
    block_z: float = 4.0  # z-score >= block_z  → BLOCK


@dataclass
class AnomalyResult:
    """Result returned by AnomalyDetector.record_and_check.

    level:    The graduated response level for this observation.
    z_score:  Computed z-score. 0.0 during warmup or when stdev=0.
    baseline: Current EWMA baseline at observation time.
    observed: The value that was passed to record_and_check.
    """

    level: ResponseLevel
    z_score: float
    baseline: float
    observed: float


# Sentinel for "no EWMA computed yet"
_NO_EWMA = object()

# EWMA smoothing factor (industry standard for short-term trend tracking)
_ALPHA = 0.3


class AnomalyDetector:
    """Per-agent sliding-window anomaly detector using EWMA + z-score.

    Thread safety: NOT thread-safe. Each SecurityGateway instance owns exactly
    one AnomalyDetector; single-worker enforcement required when anomaly gate
    is enabled (documented in REST sidecar config).

    Usage:
        detector = AnomalyDetector(config=AnomalyConfig(), metric_type="frequency")
        result = detector.record_and_check(caller_id="agent-A", value=1.0, tool_name="search")
        if result.level == ResponseLevel.BLOCK:
            raise AnomalyBlockedError(...)
    """

    def __init__(self, config: AnomalyConfig, metric_type: str = "frequency") -> None:
        """
        config:       AnomalyConfig instance with detection thresholds.
        metric_type:  "frequency" (calls/second) or "egress" (bytes). Stored for
                      Plan 02 routing; detection logic is identical for both.
        """
        self._config = config
        self._metric_type = metric_type
        # Per-agent state keyed by caller_id
        # Each entry: {"window": deque[float], "timestamps": deque[float],
        #               "ewma": float | _NO_EWMA, "tools": deque[(tool_name, timestamp)]}
        self._state: dict[str, dict[str, Any]] = {}

    def _get_or_create_state(self, caller_id: str) -> dict[str, Any]:
        """Return the per-agent state dict, creating it if not yet seen."""
        if caller_id not in self._state:
            self._state[caller_id] = {
                "window": deque(),
                "timestamps": deque(),
                "ewma": _NO_EWMA,
                "tools": deque(),
            }
        return self._state[caller_id]

    def _evict_old_entries(self, state: dict[str, Any], now: float) -> None:
        """Remove observations older than window_seconds from the front of the deques."""
        cutoff = now - self._config.window_seconds
        while state["timestamps"] and state["timestamps"][0] <= cutoff:
            state["timestamps"].popleft()
            state["window"].popleft()
            # Tools deque mirrors window deque length — evict in lockstep
            if state["tools"]:
                state["tools"].popleft()

    def record_and_check(
        self, caller_id: str, value: float, tool_name: str
    ) -> AnomalyResult:
        """Record one observation for caller_id and return an AnomalyResult.

        Steps:
          1. Get or create per-agent state.
          2. Evict entries older than window_seconds.
          3. Append new observation + timestamp.
          4. Update EWMA.
          5. Warmup guard: if n < min_observations or n < 2, return OK.
          6. Compute stdev; if stdev == 0, return OK (degenerate case).
          7. Compute z_score; map to ResponseLevel via threshold comparisons.

        Thresholds are applied in descending order (BLOCK > ESCALATE > WARN > OK).
        """
        now = time.monotonic()
        state = self._get_or_create_state(caller_id)

        # Step 2: Evict stale entries
        self._evict_old_entries(state, now)

        # Capture pre-update EWMA for z-score computation.
        # We compare the new value against the *prior* baseline — not the one
        # already contaminated by the spike. This ensures a large spike returns
        # the correct BLOCK level rather than inflating its own denominator.
        prior_ewma: float | None = None if state["ewma"] is _NO_EWMA else state["ewma"]

        # Step 3: Append new observation
        state["window"].append(value)
        state["timestamps"].append(now)
        state["tools"].append((tool_name, now))

        # Step 4: Update EWMA (post-append — used for future baseline)
        if state["ewma"] is _NO_EWMA:
            state["ewma"] = value
        else:
            state["ewma"] = _ALPHA * value + (1 - _ALPHA) * state["ewma"]

        # For AnomalyResult.baseline we expose the post-update EWMA
        ewma: float = state["ewma"]  # type: ignore[assignment]

        # Step 5: Warmup guard — need prior_ewma and at least min_observations *before*
        # this call so stdev is meaningful
        n = len(state["window"])
        if prior_ewma is None or n < self._config.min_observations or n < 2:
            return AnomalyResult(
                level=ResponseLevel.OK,
                z_score=0.0,
                baseline=ewma,
                observed=value,
            )

        # Step 6: Stdev computed from the window EXCLUDING the current observation so
        # a spike does not inflate its own denominator.
        # Use window[-n:-1] = all entries except the last one (just appended).
        prior_window = list(state["window"])[:-1]
        if len(prior_window) < 2:
            return AnomalyResult(
                level=ResponseLevel.OK,
                z_score=0.0,
                baseline=ewma,
                observed=value,
            )
        stdev = statistics.stdev(prior_window)
        if stdev == 0:
            # Perfectly stable baseline: any deviation from the prior EWMA is an anomaly.
            # Treat as BLOCK when value != prior_ewma, OK when value == prior_ewma.
            if value == prior_ewma:
                return AnomalyResult(
                    level=ResponseLevel.OK,
                    z_score=0.0,
                    baseline=ewma,
                    observed=value,
                )
            else:
                return AnomalyResult(
                    level=ResponseLevel.BLOCK,
                    z_score=float("inf"),
                    baseline=ewma,
                    observed=value,
                )

        # Step 7: z-score using the pre-update EWMA as the baseline
        z_score = (value - prior_ewma) / stdev

        cfg = self._config
        if z_score >= cfg.block_z:
            level = ResponseLevel.BLOCK
        elif z_score >= cfg.escalate_z:
            level = ResponseLevel.ESCALATE
        elif z_score >= cfg.warn_z:
            level = ResponseLevel.WARN
        else:
            level = ResponseLevel.OK

        return AnomalyResult(
            level=level,
            z_score=z_score,
            baseline=ewma,
            observed=value,
        )

    def get_recent_calls(self, caller_id: str, n: int = 5) -> list[tuple[str, float]]:
        """Return the last N (tool_name, timestamp) pairs for HITL banner context.

        Returns an empty list if caller_id has no recorded calls.
        """
        state = self._state.get(caller_id)
        if not state:
            return []
        tools = list(state["tools"])
        return tools[-n:] if len(tools) >= n else tools
