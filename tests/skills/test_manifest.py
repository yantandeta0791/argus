"""SKILL-01 manifest tests -- YAML manifest validation and trust tier enforcement.

Tests that the SkillManifest Pydantic model validates all required fields,
rejects invalid manifests, and enforces trust tier restrictions.
"""

import pytest


def test_valid_manifest(sample_manifest_dict):
    """SKILL-01: valid manifest dict loads and validates all fields."""
    from argus.skills.manifest import SkillManifest

    m = SkillManifest(**sample_manifest_dict)
    assert m.name == "test-skill"
    assert m.version == "1.0.0"
    assert m.trust_tier == "verified"
    assert m.blast_radius == "local"
    assert m.permissions == ["file:read", "network:http"]
    assert m.content_hash == "sha256:" + "a" * 64


def test_invalid_manifest_missing_fields():
    """SKILL-01: missing required field raises ValidationError."""
    from pydantic import ValidationError
    from argus.skills.manifest import SkillManifest

    with pytest.raises(ValidationError):
        SkillManifest(name="incomplete")  # missing required fields


def test_builtin_tier_rejected_external(tmp_path):
    """SKILL-01: builtin tier from non-argus/skills/ dir raises SkillIntegrityError."""
    from argus.skills.manifest import SkillManifest, validate_trust_tier
    from argus.security import SkillIntegrityError

    m = SkillManifest(
        name="fake-builtin",
        version="1.0.0",
        description="test",
        trust_tier="builtin",
        permissions=[],
        content_hash="sha256:" + "a" * 64,
    )
    with pytest.raises(SkillIntegrityError):
        validate_trust_tier(m, tmp_path)


def test_blast_radius_enum():
    """SKILL-01: blast_radius accepts valid values, rejects invalid."""
    from argus.skills.manifest import BlastRadius, SkillManifest

    assert BlastRadius.NONE == "none"
    assert BlastRadius.LOCAL == "local"
    assert BlastRadius.NETWORK == "network"
    assert BlastRadius.SYSTEM == "system"
    m = SkillManifest(
        name="test",
        version="1.0.0",
        description="test",
        trust_tier="verified",
        permissions=[],
        content_hash="sha256:" + "a" * 64,
        blast_radius="local",
    )
    assert m.blast_radius == BlastRadius.LOCAL


def test_content_hash_prefix_validation():
    """SKILL-01: content_hash without sha256: prefix is rejected."""
    from pydantic import ValidationError
    from argus.skills.manifest import SkillManifest

    with pytest.raises(ValidationError, match="content_hash"):
        SkillManifest(
            name="test",
            version="1.0.0",
            description="test",
            trust_tier="verified",
            permissions=[],
            content_hash="bad_hash",
        )


def test_permissions_list(sample_manifest_dict):
    """SKILL-01: permissions field accepts list of strings."""
    from argus.skills.manifest import SkillManifest

    m = SkillManifest(**sample_manifest_dict)
    assert m.permissions == ["file:read", "network:http"]
