"""
Instruction provenance tracking (Phase 12 — PROV-01).

Tracks WHERE the instruction that triggered a tool call came from:
  - untrusted_retrieval: content returned from RAG, web fetch, MCP server
                         responses, or reads of user-uploaded files
  - user_originated:     the direct user prompt (default)
  - system:              framework-internal/config-driven calls

Provenance is set deterministically at adapter boundaries — never inferred
from prompt content (see REQUIREMENTS.md out-of-scope table). API mirrors
identity.set_caller_context / get_caller_context exactly.

Used by Gate 0.75 (provenance check) in the security gateway.
"""

from __future__ import annotations

from contextvars import ContextVar
from enum import StrEnum


class Provenance(StrEnum):
    """Closed enum of valid provenance values (PROV-01)."""

    UNTRUSTED_RETRIEVAL = "untrusted_retrieval"
    USER_ORIGINATED = "user_originated"
    SYSTEM = "system"


_current_provenance: ContextVar[str] = ContextVar(
    "_current_provenance", default=Provenance.USER_ORIGINATED.value
)


def set_provenance(value: str | Provenance) -> tuple:
    """Set the active provenance for the current execution context.

    Accepts a Provenance member or its string value; any other value raises
    ValueError immediately (fail-closed against typos, unlike a silent default).

    Returns a token for reset_provenance().
    """
    resolved = _resolve(value)
    return (_current_provenance.set(resolved),)


def get_provenance() -> Provenance:
    """Read the active provenance. Defaults to USER_ORIGINATED."""
    return Provenance(_current_provenance.get())


def reset_provenance(tokens: tuple) -> None:
    """Reset provenance using the token from a previous set_provenance() call."""
    (token,) = tokens
    _current_provenance.reset(token)


def _resolve(value: str | Provenance) -> str:
    if isinstance(value, Provenance):
        return value.value
    try:
        return Provenance(value).value
    except ValueError:
        valid = ", ".join(p.value for p in Provenance)
        raise ValueError(
            f"Invalid provenance {value!r}. Valid values: {valid}"
        ) from None
