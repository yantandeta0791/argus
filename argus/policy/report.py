"""Streaming aggregation for policy-decision rollout evidence."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable


DecisionKey = tuple[str, str, str | None]


@dataclass(frozen=True)
class PolicyDecisionSummary:
    total_decisions: int
    total_would_blocks: int
    policy_hashes: tuple[str, ...]
    groups: dict[str, dict[DecisionKey, int]]
    totals_by_policy_hash: dict[str, tuple[int, int]]
    warning: str | None = None


def summarize_decisions(events: Iterable[dict]) -> PolicyDecisionSummary:
    """Aggregate policy decisions by hash and gate/tool/rule without merging policies."""
    groups: dict[str, Counter[DecisionKey]] = defaultdict(Counter)
    totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    total_decisions = 0
    total_would_blocks = 0
    for event in events:
        if event.get("event_type") != "policy_decision":
            continue
        # The rollout report is shadow-only; never blend enforced observations.
        if event.get("mode") not in (None, "shadow"):
            continue
        policy_hash = event.get("policy_hash", "[missing]")
        total_decisions += 1
        totals[policy_hash][0] += 1
        if event.get("outcome") != "would_block":
            continue
        total_would_blocks += 1
        totals[policy_hash][1] += 1
        groups[policy_hash][
            (
                event.get("gate", "unknown"),
                event.get("tool_name", ""),
                event.get("rule"),
            )
        ] += 1
    hashes = tuple(sorted(totals))
    return PolicyDecisionSummary(
        total_decisions=total_decisions,
        total_would_blocks=total_would_blocks,
        policy_hashes=hashes,
        groups={policy_hash: dict(counts) for policy_hash, counts in groups.items()},
        totals_by_policy_hash={
            policy_hash: (values[0], values[1])
            for policy_hash, values in totals.items()
        },
        warning=(
            "Multiple policy hashes observed; results are grouped by policy hash."
            if len(hashes) > 1
            else None
        ),
    )
