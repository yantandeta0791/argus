"""
SessionStore -- per-session read/write interface for argus.memory facts.

Thin facade bound to one session_id. Does not own the connection --
MemoryManager does. All methods are async for consistency with the
engine's async patterns.

The '__GLOBAL__' sentinel is an internal implementation detail used for
global facts (visible across all sessions). Callers use global_=True
parameter instead.

Phase 4 Plan 02 implements CRUD methods; stubs raise NotImplementedError.
"""
from __future__ import annotations

from typing import Any


class SessionStore:
    """Per-session read/write interface for facts stored in SQLite.

    Usage:
        store = manager.session("session-001")
        await store.put("last_plan", {"goal": "test"})
        value = await store.get("last_plan")  # returns {"goal": "test"}
        all_facts = await store.facts()        # returns dict copy
    """

    def __init__(self, conn, session_id: str) -> None:
        self._conn = conn
        self._session_id = session_id

    @property
    def session_id(self) -> str:
        """Return the session ID this store is bound to."""
        return self._session_id

    async def get(self, key: str, *, global_: bool = False) -> Any | None:
        """Get a fact by key. Returns None if not found.

        Args:
            key: fact key to look up.
            global_: if True, look up in global scope (cross-session).

        Phase 4 Plan 02 implements this stub.
        """
        raise NotImplementedError("SessionStore.get not yet implemented")

    async def put(self, key: str, value: Any, *, global_: bool = False) -> None:
        """Upsert a fact. JSON-serializable values only.

        Args:
            key: fact key.
            value: JSON-serializable value.
            global_: if True, store in global scope (cross-session).

        Phase 4 Plan 02 implements this stub.
        """
        raise NotImplementedError("SessionStore.put not yet implemented")

    async def facts(self, *, global_: bool = False) -> dict[str, Any]:
        """Return all facts for this session (or global). Returns copies.

        Args:
            global_: if True, return global facts instead of session-scoped.

        Phase 4 Plan 02 implements this stub.
        """
        raise NotImplementedError("SessionStore.facts not yet implemented")

    async def delete(self, key: str, *, global_: bool = False) -> None:
        """Delete a fact by key.

        Args:
            key: fact key to delete.
            global_: if True, delete from global scope.

        Phase 4 Plan 02 implements this stub.
        """
        raise NotImplementedError("SessionStore.delete not yet implemented")
