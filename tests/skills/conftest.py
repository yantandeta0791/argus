"""Shared fixtures for skill tests."""
import pytest
import yaml
from pathlib import Path
from unittest.mock import MagicMock


@pytest.fixture
def sample_manifest_dict():
    """Return a valid manifest dict with all required fields."""
    return {
        "name": "test-skill",
        "version": "1.0.0",
        "description": "A test skill for unit tests",
        "trust_tier": "verified",
        "permissions": ["file:read", "network:http"],
        "content_hash": "sha256:" + "a" * 64,
        "blast_radius": "local",
        "data_access": ["agent_config"],
        "egress_allowlist": ["api.example.com"],
        "timeout_s": 15.0,
        "idempotent": True,
    }


@pytest.fixture
def tmp_skill_dir(tmp_path):
    """Create a temporary skill directory with skill.yaml and __init__.py.

    The content_hash in skill.yaml is computed from the actual file contents
    so that hash verification passes during lifecycle tests.
    skill.yaml is excluded from hash computation (chicken-and-egg).
    """
    from argus.skills.hasher import compute_content_hash

    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()

    # Create a sample Python file first
    init_file = skill_dir / "__init__.py"
    init_file.write_text('print("skill output")\n')

    # Compute the real content hash (skill.yaml is excluded from hash)
    real_hash = compute_content_hash(skill_dir)

    # Write skill.yaml with the real hash
    manifest = {
        "name": "test-skill",
        "version": "1.0.0",
        "description": "A test skill",
        "trust_tier": "verified",
        "permissions": ["file:read"],
        "content_hash": real_hash,
    }
    yaml_file = skill_dir / "skill.yaml"
    yaml_file.write_text(yaml.dump(manifest))

    return skill_dir


@pytest.fixture
def mock_isolator():
    """Return a MagicMock of SkillIsolator with .run() returning 'skill output'."""
    isolator = MagicMock()
    isolator.run.return_value = "skill output"
    return isolator
