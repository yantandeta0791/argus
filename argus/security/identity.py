"""
Identity infrastructure for multi-agent enforcement.

Provides:
  - ContextVar definitions for caller_id and hop_depth propagation
  - set_caller_context / get_caller_context / reset_caller_context helpers
  - AgentRegistryConfig dataclass (caller_id -> role mapping + max depth)
  - AgentRegistry for resolving caller_id to RBAC role

Used by Gate 0.5 (identity check) in the security gateway and by framework
adapters (LangGraph, CrewAI, AutoGen) to bind caller context to tool calls.

MAGNT-01, MAGNT-02
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Module-level ContextVars — propagate automatically through async call stacks
# ---------------------------------------------------------------------------

_current_caller_id: ContextVar[str | None] = ContextVar(
    "_current_caller_id", default=None
)
_current_hop_depth: ContextVar[int] = ContextVar("_current_hop_depth", default=0)


def set_caller_context(caller_id: str, hop_depth: int) -> tuple:
    """Set the caller identity context for the current execution context.

    Returns a (id_token, depth_token) tuple that can be passed to
    reset_caller_context() to restore previous values.
    """
    id_token = _current_caller_id.set(caller_id)
    depth_token = _current_hop_depth.set(hop_depth)
    return (id_token, depth_token)


def get_caller_context() -> tuple[str | None, int]:
    """Read the current caller identity context.

    Returns:
        (caller_id, hop_depth) — (None, 0) when no context has been set.
    """
    return _current_caller_id.get(), _current_hop_depth.get()


def reset_caller_context(tokens: tuple) -> None:
    """Reset both ContextVars to their previous values using saved tokens.

    Args:
        tokens: The tuple returned by a previous set_caller_context() call.
    """
    id_token, depth_token = tokens
    _current_caller_id.reset(id_token)
    _current_hop_depth.reset(depth_token)


# ---------------------------------------------------------------------------
# AgentRegistryConfig and AgentRegistry
# ---------------------------------------------------------------------------


@dataclass
class AgentRegistryConfig:
    """Configuration for the agent identity registry.

    agents: mapping of caller_id -> RBAC role name
    max_delegation_depth: maximum allowed hop depth before raising DelegationDepthError
    """

    agents: dict[str, str] = field(default_factory=dict)
    max_delegation_depth: int = 3


class AgentRegistry:
    """Resolves caller_id to RBAC role for multi-agent enforcement.

    Resolution is permissive: unknown caller_ids fall back to the
    adapter-supplied agent_role rather than blocking. This prevents
    legitimate single-agent calls from being rejected when no agents:
    section is configured.
    """

    _DEFAULT_MAX_DEPTH = 3

    def __init__(self, config: AgentRegistryConfig | None) -> None:
        self._config = config

    def resolve_role(self, caller_id: str, fallback_role: str) -> str:
        """Resolve caller_id to its configured RBAC role.

        Args:
            caller_id: The identity of the calling agent.
            fallback_role: Role supplied by the adapter — used when caller_id
                           is not in the registry or no registry is configured.

        Returns:
            The registered role, or fallback_role if not found (permissive).
        """
        if self._config is None:
            return fallback_role
        return self._config.agents.get(caller_id, fallback_role)

    @property
    def max_depth(self) -> int:
        """Maximum allowed delegation hop depth."""
        if self._config is None:
            return self._DEFAULT_MAX_DEPTH
        return self._config.max_delegation_depth
