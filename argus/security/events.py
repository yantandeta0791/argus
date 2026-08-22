"""
Security event schema for Argus.

SecurityEvent is the canonical record emitted by every gate when it fires.
The metadata field is a forward-compatible escape hatch for Phase 7 observability.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid

from pydantic import BaseModel, Field


class GateType(str, Enum):
    PERMISSION = "permission"
    AUDIT = "audit"
    REDACTION = "redaction"
    SANDBOX = "sandbox"
    PROMPT_SHIELD = "prompt_shield"
    EGRESS = "egress"
    SKILL_LIFECYCLE = "skill_lifecycle"
    HITL = "hitl"
    IDENTITY = "identity"
    ANOMALY = "anomaly"


class SecurityEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    gate: GateType
    outcome: str  # "blocked" | "allowed" | "redacted" | "violation"
    agent_role: str | None = None
    tool_name: str | None = None
    rule_triggered: str | None = None
    blocked_value: str | None = None  # truncated; never full secret value
    metadata: dict[str, Any] = Field(default_factory=dict)
    caller_id: str | None = (
        None  # multi-agent: identity of the calling agent (MAGNT-01)
    )
    hop_depth: int = 0  # multi-agent: delegation chain depth (MAGNT-02)

    @classmethod
    def from_context(
        cls,
        *,
        gate: "GateType",
        outcome: str,
        agent_role: str | None = None,
        tool_name: str | None = None,
        rule_triggered: str | None = None,
        blocked_value: str | None = None,
        metadata: dict[str, Any] | None = None,
        caller_id: str | None = None,
        hop_depth: int = 0,
    ) -> "SecurityEvent":
        """CLEAN-04: construct a SecurityEvent with caller_id/hop_depth resolved
        from the active ContextVars when not passed explicitly. Lazy import avoids
        a circular import (events.py <- gateway.py -> identity.py)."""
        from argus.security.identity import get_caller_context

        ctx_caller_id, ctx_hop_depth = get_caller_context()
        return cls(
            gate=gate,
            outcome=outcome,
            agent_role=agent_role,
            tool_name=tool_name,
            rule_triggered=rule_triggered,
            blocked_value=blocked_value,
            metadata=metadata or {},
            caller_id=caller_id if caller_id is not None else ctx_caller_id,
            hop_depth=hop_depth if hop_depth else ctx_hop_depth,
        )
