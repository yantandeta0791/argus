"""Normalized, immutable policy gate decisions for the audit stream."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal


class PolicyMode(StrEnum):
    """Supported operating modes for deterministic pre-call policy gates."""

    ENFORCE = "enforce"
    SHADOW = "shadow"


@dataclass(frozen=True)
class PolicyDecision:
    """One policy-gate evaluation, serialized through a single stable contract."""

    decision_id: str
    mode: Literal["enforce", "shadow"] | PolicyMode
    outcome: Literal["allow", "block", "would_block"]
    gate: str
    tool_name: str
    agent_role: str
    rule: str | None
    reason: str
    caller_id: str | None
    hop_depth: int
    provenance: str
    policy_metadata: dict[str, Any]

    def to_audit_event(self) -> dict[str, Any]:
        """Return the audit payload; timestamps and chain fields belong to AuditLogger."""
        return {
            "event_type": "policy_decision",
            "decision_id": self.decision_id,
            "mode": self.mode.value if isinstance(self.mode, PolicyMode) else self.mode,
            "outcome": self.outcome,
            "gate": self.gate,
            "tool_name": self.tool_name,
            "agent_role": self.agent_role,
            "rule": self.rule,
            "reason": self.reason,
            "caller_id": self.caller_id,
            "hop_depth": self.hop_depth,
            "provenance": self.provenance,
            **self.policy_metadata,
        }
