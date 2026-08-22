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
    warning: str | None = None


def summarize_decisions(events: Iterable[dict]) -> PolicyDecisionSummary:
    """Aggregate policy decisions by hash and gate/tool/rule without merging policies."""
    groups: dict[str, Counter[DecisionKey]] = defaultdict(Counter)
    total_decisions = 0
    total_would_blocks = 0
    for event in events:
        if event.get("event_type") != "policy_decision":
            continue
        total_decisions += 1
        if event.get("outcome") != "would_block":
            continue
        total_would_blocks += 1
        policy_hash = event.get("policy_hash", "[missing]")
        groups[policy_hash][
            (
                event.get("gate", "unknown"),
                event.get("tool_name", ""),
                event.get("rule"),
            )
        ] += 1
    hashes = tuple(sorted(groups))
    return PolicyDecisionSummary(
        total_decisions=total_decisions,
        total_would_blocks=total_would_blocks,
        policy_hashes=hashes,
        groups={policy_hash: dict(counts) for policy_hash, counts in groups.items()},
        warning=(
            "Multiple policy hashes observed; results are grouped by policy hash."
            if len(hashes) > 1
            else None
        ),
    )
