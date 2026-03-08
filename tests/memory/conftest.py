"""Shared fixtures for argus.memory tests."""

import pytest


@pytest.fixture
def tmp_db_path(tmp_path):
    """Return a temporary database file path (file not created yet)."""
    return tmp_path / "test_state.db"


@pytest.fixture
def memory_config(tmp_db_path):
    """Return a MemoryConfig pointing to a temporary database."""
    from argus.memory.manager import MemoryConfig

    return MemoryConfig(db_path=tmp_db_path)


@pytest.fixture
def session_id():
    """Return a fixed test session ID."""
    return "test-session-001"
