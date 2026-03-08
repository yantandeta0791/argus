"""
MemoryManager -- connection lifecycle and session factory for argus.memory.

Owns a single long-lived aiosqlite connection per process. Creates
SessionStore instances bound to a session_id. Manages schema initialization
on first connect.

Design:
- Single connection with WAL journal mode for concurrent read/write safety.
- PRAGMA user_version for future schema migration tracking.
- MemoryConfig resolves db_path with XDG_DATA_HOME support.
- Phase 4 provides the persistence layer for MEM-02 and MEM-03.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import aiosqlite

from argus.memory._schema import init_schema
from argus.memory.store import SessionStore


@dataclass
class MemoryConfig:
    """Configuration for the memory subsystem.

    db_path: explicit database file path. None = auto-resolve to
    ~/.argus/state.db (XDG_DATA_HOME respected if set).
    """

    db_path: Path | None = None

    def resolved_path(self) -> Path:
        """Resolve the database file path.

        Priority:
        1. Explicit db_path if set.
        2. $XDG_DATA_HOME/argus/state.db if XDG_DATA_HOME is set.
        3. ~/.argus/state.db as fallback.

        Creates parent directories if they don't exist.
        """
        if self.db_path is not None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            return self.db_path

        xdg = os.environ.get("XDG_DATA_HOME")
        if xdg:
            base = Path(xdg) / "argus"
        else:
            base = Path.home() / ".argus"

        base.mkdir(parents=True, exist_ok=True)
        return base / "state.db"


class MemoryManager:
    """Connection lifecycle manager for argus.memory SQLite store.

    Usage:
        manager = MemoryManager(MemoryConfig(db_path=Path("/tmp/test.db")))
        await manager.connect()
        store = manager.session("session-001")
        await store.put("key", "value")
        await manager.close()
    """

    def __init__(self, config: MemoryConfig | None = None) -> None:
        self._config = config or MemoryConfig()
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Open SQLite connection and initialize schema.

        Sets WAL journal mode for concurrent read/write safety,
        enables foreign key enforcement, and applies any pending
        schema migrations via init_schema().
        """
        path = self._config.resolved_path()
        self._conn = await aiosqlite.connect(str(path))
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await init_schema(self._conn)

    async def close(self) -> None:
        """Close SQLite connection and release resources."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    def session(self, session_id: str) -> SessionStore:
        """Create a SessionStore bound to this connection and session_id.

        Raises AssertionError if not connected (connect() not called).
        """
        assert self._conn is not None, (
            "MemoryManager not connected -- call connect() first"
        )
        return SessionStore(conn=self._conn, session_id=session_id)
