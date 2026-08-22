"""Tests for provenance ContextVar primitives (PROV-01)."""

from __future__ import annotations

import pytest

from argus.security.provenance import (
    Provenance,
    get_provenance,
    reset_provenance,
    set_provenance,
)


def test_set_and_get_roundtrip():
    tokens = set_provenance(Provenance.UNTRUSTED_RETRIEVAL)
    try:
        assert get_provenance() == Provenance.UNTRUSTED_RETRIEVAL
    finally:
        reset_provenance(tokens)


def test_accepts_string_value():
    tokens = set_provenance("untrusted_retrieval")
    try:
        assert get_provenance() is Provenance.UNTRUSTED_RETRIEVAL
    finally:
        reset_provenance(tokens)


def test_default_is_user_originated():
    assert get_provenance() == Provenance.USER_ORIGINATED


def test_reset_restores_previous_value():
    outer = set_provenance(Provenance.SYSTEM)
    inner = set_provenance(Provenance.UNTRUSTED_RETRIEVAL)
    reset_provenance(inner)
    assert get_provenance() == Provenance.SYSTEM
    reset_provenance(outer)


def test_invalid_value_raises_value_error():
    with pytest.raises(ValueError, match="Invalid provenance"):
        set_provenance("made_up_value")


def test_token_based_reset_is_async_safe():
    """Mirrors identity ContextVar semantics — token reset works across awaits."""

    async def inner() -> None:
        tokens = set_provenance(Provenance.UNTRUSTED_RETRIEVAL)
        reset_provenance(tokens)

    import asyncio

    asyncio.run(inner())
    assert get_provenance() == Provenance.USER_ORIGINATED
