"""SessionStore tests -- MEM-02, MEM-03."""


async def test_session_fact_put_and_get(tmp_db_path):
    """MEM-02: put a fact, get it back, assert equal."""
    from argus.memory.manager import MemoryManager, MemoryConfig

    mgr = MemoryManager(MemoryConfig(db_path=tmp_db_path))
    await mgr.connect()
    store = mgr.session("s1")
    await store.put("key1", "value1")
    result = await store.get("key1")
    assert result == "value1"
    await mgr.close()


async def test_session_fact_persists_across_reads(tmp_db_path):
    """MEM-02: put then get twice, both return same value."""
    from argus.memory.manager import MemoryManager, MemoryConfig

    mgr = MemoryManager(MemoryConfig(db_path=tmp_db_path))
    await mgr.connect()
    store = mgr.session("s1")
    await store.put("key1", {"nested": True})
    r1 = await store.get("key1")
    r2 = await store.get("key1")
    assert r1 == r2 == {"nested": True}
    await mgr.close()


async def test_session_isolation(tmp_db_path):
    """MEM-02: put in session A, get in session B returns None."""
    from argus.memory.manager import MemoryManager, MemoryConfig

    mgr = MemoryManager(MemoryConfig(db_path=tmp_db_path))
    await mgr.connect()
    store_a = mgr.session("session-A")
    store_b = mgr.session("session-B")
    await store_a.put("secret", "alpha")
    result = await store_b.get("secret")
    assert result is None
    await mgr.close()


async def test_global_fact_cross_session(tmp_db_path):
    """MEM-03: put global in session A, get global in session B returns value."""
    from argus.memory.manager import MemoryManager, MemoryConfig

    mgr = MemoryManager(MemoryConfig(db_path=tmp_db_path))
    await mgr.connect()
    store_a = mgr.session("session-A")
    store_b = mgr.session("session-B")
    await store_a.put("config_key", {"version": 1}, global_=True)
    result = await store_b.get("config_key", global_=True)
    assert result == {"version": 1}
    await mgr.close()


async def test_facts_returns_copy(tmp_db_path):
    """MEM-03: facts() returns dict, mutating it does not affect store."""
    from argus.memory.manager import MemoryManager, MemoryConfig

    mgr = MemoryManager(MemoryConfig(db_path=tmp_db_path))
    await mgr.connect()
    store = mgr.session("s1")
    await store.put("k", "v")
    facts = await store.facts()
    facts["k"] = "MUTATED"
    original = await store.get("k")
    assert original == "v"
    await mgr.close()


async def test_get_missing_key_returns_none(tmp_db_path):
    """MEM-02/03: get nonexistent key returns None, not KeyError."""
    from argus.memory.manager import MemoryManager, MemoryConfig

    mgr = MemoryManager(MemoryConfig(db_path=tmp_db_path))
    await mgr.connect()
    store = mgr.session("s1")
    result = await store.get("nonexistent")
    assert result is None
    await mgr.close()


async def test_put_overwrites_existing(tmp_db_path):
    """MEM-03: put same key twice, get returns latest value."""
    from argus.memory.manager import MemoryManager, MemoryConfig

    mgr = MemoryManager(MemoryConfig(db_path=tmp_db_path))
    await mgr.connect()
    store = mgr.session("s1")
    await store.put("key1", "first")
    await store.put("key1", "second")
    result = await store.get("key1")
    assert result == "second"
    await mgr.close()


async def test_delete_removes_fact(tmp_db_path):
    """MEM-03: put then delete then get returns None."""
    from argus.memory.manager import MemoryManager, MemoryConfig

    mgr = MemoryManager(MemoryConfig(db_path=tmp_db_path))
    await mgr.connect()
    store = mgr.session("s1")
    await store.put("key1", "value1")
    await store.delete("key1")
    result = await store.get("key1")
    assert result is None
    await mgr.close()
