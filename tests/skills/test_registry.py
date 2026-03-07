"""Registry tests -- in-memory skill tracking.

Tests that SkillRegistry install/get/list/revoke operations work correctly.
"""


def test_install_and_get(sample_manifest_dict):
    """Install a skill manifest, retrieve it by name."""
    from argus.skills.registry import SkillRegistry
    from argus.skills.manifest import SkillManifest

    registry = SkillRegistry()
    manifest = SkillManifest(**sample_manifest_dict)
    registry.install(manifest)

    result = registry.get("test-skill")
    assert result is not None
    assert result["name"] == "test-skill"
    assert result["version"] == "1.0.0"
    assert "installed_at" in result


def test_list_skills(sample_manifest_dict):
    """List returns all installed skill names."""
    from argus.skills.registry import SkillRegistry
    from argus.skills.manifest import SkillManifest

    registry = SkillRegistry()
    manifest = SkillManifest(**sample_manifest_dict)
    registry.install(manifest)

    skills = registry.list_skills()
    assert skills == ["test-skill"]


def test_revoke(sample_manifest_dict):
    """Revoke removes a skill; subsequent get returns None."""
    from argus.skills.registry import SkillRegistry
    from argus.skills.manifest import SkillManifest

    registry = SkillRegistry()
    manifest = SkillManifest(**sample_manifest_dict)
    registry.install(manifest)
    assert registry.get("test-skill") is not None

    registry.revoke("test-skill")
    assert registry.get("test-skill") is None
    assert registry.list_skills() == []


def test_duplicate_install(sample_manifest_dict):
    """Installing same skill name twice overwrites the previous entry."""
    from argus.skills.registry import SkillRegistry
    from argus.skills.manifest import SkillManifest

    registry = SkillRegistry()
    manifest_v1 = SkillManifest(**{**sample_manifest_dict, "version": "1.0.0"})
    manifest_v2 = SkillManifest(**{**sample_manifest_dict, "version": "2.0.0"})

    registry.install(manifest_v1)
    registry.install(manifest_v2)

    result = registry.get("test-skill")
    assert result["version"] == "2.0.0"
    assert len(registry.list_skills()) == 1
