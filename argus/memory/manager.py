"""
MemoryManager -- connection lifecycle and session factory for argus.memory.

Owns a single long-lived aiosqlite connection per process. Creates
SessionStore instances bound to a session_id. Manages schema initialization
on first connect.

Design:
- Single connection with WAL journal mode for concurrent read/write safety.
- PRAGMA user_version for future schema migration tracking.
- MemoryConfig resolves db_path with XDG_DATA_HOME support.

Phase 4 Plan 02 implements connect/close/session; stubs raise NotImplementedError.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argus.memory.store import SessionStore


@dataclass
class MemoryConfig:
    """Configuration for the memory subsystem.

    db_path: explicit database file path. None = auto-resolve to
    ~/.argus/state.db (XDG_DATA_HOME respected if set).
    """
    db_path: Path | None = None


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
        self._conn = None

    async def connect(self) -> None:
        """Open SQLite connection and initialize schema.

        Phase 4 Plan 02 implements this stub.
        """
        raise NotImplementedError("MemoryManager.connect not yet implemented")

    async def close(self) -> None:
        """Close SQLite connection and release resources.

        Phase 4 Plan 02 implements this stub.
        """
        raise NotImplementedError("MemoryManager.close not yet implemented")

    def session(self, session_id: str) -> "SessionStore":
        """Create a SessionStore bound to this connection and session_id.

        Phase 4 Plan 02 implements this stub.
        """
        raise NotImplementedError("MemoryManager.session not yet implemented")
