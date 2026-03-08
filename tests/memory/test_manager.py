"""MemoryManager tests -- MEM-03 schema init and lifecycle."""


async def test_schema_init(tmp_db_path):
    """MEM-03: connect creates tables, user_version=1."""
    from argus.memory.manager import MemoryManager, MemoryConfig
    import aiosqlite

    mgr = MemoryManager(MemoryConfig(db_path=tmp_db_path))
    await mgr.connect()
    # Verify schema via direct connection
    async with aiosqlite.connect(str(tmp_db_path)) as conn:
        cursor = await conn.execute("PRAGMA user_version")
        row = await cursor.fetchone()
        assert row[0] == 1
        # Check tables exist
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [r[0] for r in await cursor.fetchall()]
        assert "facts" in tables
        assert "sessions" in tables
    await mgr.close()


async def test_connect_creates_db_file(tmp_db_path):
    """MEM-03: after connect, db file exists on disk."""
    from argus.memory.manager import MemoryManager, MemoryConfig

    assert not tmp_db_path.exists()
    mgr = MemoryManager(MemoryConfig(db_path=tmp_db_path))
    await mgr.connect()
    assert tmp_db_path.exists()
    await mgr.close()


async def test_session_returns_store(tmp_db_path):
    """MEM-02: session() returns a SessionStore instance."""
    from argus.memory.manager import MemoryManager, MemoryConfig
    from argus.memory.store import SessionStore

    mgr = MemoryManager(MemoryConfig(db_path=tmp_db_path))
    await mgr.connect()
    store = mgr.session("test-sid")
    assert isinstance(store, SessionStore)
    assert store.session_id == "test-sid"
    await mgr.close()


async def test_close_closes_connection(tmp_db_path):
    """MEM-03: after close, connection is None."""
    from argus.memory.manager import MemoryManager, MemoryConfig

    mgr = MemoryManager(MemoryConfig(db_path=tmp_db_path))
    await mgr.connect()
    await mgr.close()
    assert mgr._conn is None
