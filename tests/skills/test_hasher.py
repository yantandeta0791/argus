"""SKILL-03 hash verification tests -- deterministic SHA-256 content hashing.

Tests that compute_content_hash produces deterministic hashes, excludes
__pycache__/.pyc/.git files, and that verify_content_hash detects mismatches.
"""
import pytest


def test_hash_match(tmp_skill_dir):
    """SKILL-03: compute hash and verify it matches."""
    from argus.skills.hasher import compute_content_hash, verify_content_hash
    h = compute_content_hash(tmp_skill_dir)
    assert verify_content_hash(tmp_skill_dir, h) is True


def test_hash_mismatch_error(tmp_skill_dir):
    """SKILL-03: verify with wrong hash returns False."""
    from argus.skills.hasher import verify_content_hash
    assert verify_content_hash(tmp_skill_dir, "sha256:" + "0" * 64) is False


def test_excluded_files(tmp_skill_dir):
    """SKILL-03: __pycache__/*.pyc files do not affect hash."""
    from argus.skills.hasher import compute_content_hash
    h1 = compute_content_hash(tmp_skill_dir)
    # Add excluded files
    cache_dir = tmp_skill_dir / "__pycache__"
    cache_dir.mkdir()
    (cache_dir / "module.cpython-312.pyc").write_bytes(b"bytecode")
    h2 = compute_content_hash(tmp_skill_dir)
    assert h1 == h2


def test_deterministic_order(tmp_skill_dir):
    """SKILL-03: same files produce same hash on repeated calls."""
    from argus.skills.hasher import compute_content_hash
    h1 = compute_content_hash(tmp_skill_dir)
    h2 = compute_content_hash(tmp_skill_dir)
    assert h1 == h2


def test_empty_dir_rejected(tmp_path):
    """SKILL-03: empty skill directory raises ValueError."""
    from argus.skills.hasher import compute_content_hash
    empty_dir = tmp_path / "empty-skill"
    empty_dir.mkdir()
    with pytest.raises(ValueError, match="No hashable files"):
        compute_content_hash(empty_dir)


def test_hash_prefix_format(tmp_skill_dir):
    """SKILL-03: returned hash starts with 'sha256:' followed by 64 hex chars."""
    from argus.skills.hasher import compute_content_hash
    h = compute_content_hash(tmp_skill_dir)
    assert h.startswith("sha256:")
    assert len(h.split(":")[1]) == 64
