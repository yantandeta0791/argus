"""
SessionStore -- per-session read/write interface for argus.memory facts.

Thin facade bound to one session_id. Does not own the connection --
MemoryManager does. All methods are async for consistency with the
engine's async patterns.

The '__GLOBAL__' sentinel is an internal implementation detail used for
global facts (visible across all sessions). Callers use global_=True
parameter instead.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import aiosqlite

_GLOBAL_SENTINEL = "__GLOBAL__"


class SessionStore:
    """Per-session read/write interface for facts stored in SQLite.

    Usage:
        store = manager.session("session-001")
        await store.put("last_plan", {"goal": "test"})
        value = await store.get("last_plan")  # returns {"goal": "test"}
        all_facts = await store.facts()        # returns dict copy
    """

    def __init__(self, conn: aiosqlite.Connection, session_id: str) -> None:
        self._conn = conn
        self._session_id = session_id

    @property
    def session_id(self) -> str:
        """Return the session ID this store is bound to."""
        return self._session_id

    def _resolve_sid(self, global_: bool) -> str:
        """Return the session_id to use for database queries."""
        return _GLOBAL_SENTINEL if global_ else self._session_id

    async def get(self, key: str, *, global_: bool = False) -> Any | None:
        """Get a fact by key. Returns None if not found.

        Args:
            key: fact key to look up.
            global_: if True, look up in global scope (cross-session).
        """
        sid = self._resolve_sid(global_)
        cursor = await self._conn.execute(
            "SELECT value FROM facts WHERE key = ? AND session_id = ?",
            (key, sid),
        )
        row = await cursor.fetchone()
        return json.loads(row[0]) if row else None

    async def put(self, key: str, value: Any, *, global_: bool = False) -> None:
        """Upsert a fact. JSON-serializable values only.

        Args:
            key: fact key.
            value: JSON-serializable value.
            global_: if True, store in global scope (cross-session).
        """
        sid = self._resolve_sid(global_)
        now = datetime.now(timezone.utc).isoformat()
        await self._conn.execute(
            """INSERT INTO facts (key, value, session_id, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(key, session_id) DO UPDATE
               SET value = excluded.value, updated_at = excluded.updated_at""",
            (key, json.dumps(value), sid, now),
        )
        await self._conn.commit()

    async def facts(self, *, global_: bool = False) -> dict[str, Any]:
        """Return all facts for this session (or global). Returns a fresh dict.

        Args:
            global_: if True, return global facts instead of session-scoped.
        """
        sid = self._resolve_sid(global_)
        cursor = await self._conn.execute(
            "SELECT key, value FROM facts WHERE session_id = ?",
            (sid,),
        )
        rows = await cursor.fetchall()
        return {k: json.loads(v) for k, v in rows}

    async def delete(self, key: str, *, global_: bool = False) -> None:
        """Delete a fact by key.

        Args:
            key: fact key to delete.
            global_: if True, delete from global scope.
        """
        sid = self._resolve_sid(global_)
        await self._conn.execute(
            "DELETE FROM facts WHERE key = ? AND session_id = ?",
            (key, sid),
        )
        await self._conn.commit()
