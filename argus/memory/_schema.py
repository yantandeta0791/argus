"""
Schema DDL and migration logic for argus.memory SQLite store.

Uses PRAGMA user_version for schema versioning. MIGRATIONS dict maps
version numbers to lists of DDL statements. init_schema() applies
pending migrations on connect.

Design: '__GLOBAL__' sentinel used for global facts (not NULL) to avoid
SQLite NULL uniqueness pitfall in composite primary keys.
"""
from __future__ import annotations

SCHEMA_VERSION = 1

MIGRATIONS: dict[int, list[str]] = {
    1: [
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            run_count INTEGER NOT NULL DEFAULT 0,
            metadata TEXT NOT NULL DEFAULT '{}'
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS facts (
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            session_id TEXT NOT NULL DEFAULT '__GLOBAL__',
            updated_at TEXT NOT NULL,
            PRIMARY KEY (key, session_id)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_facts_session
        ON facts(session_id)
        """,
    ],
}


async def init_schema(conn) -> None:
    """Apply pending schema migrations based on PRAGMA user_version.

    Reads current version, applies all MIGRATIONS entries with version >
    current, sets user_version to latest applied version.

    Phase 4 Plan 02 implements this; stub raises NotImplementedError.
    """
    raise NotImplementedError("init_schema not yet implemented")
