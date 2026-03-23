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
