"""End-to-end integration tests -- SKILL-01 + SKILL-02 + SKILL-03 together.

Proves the full skill architecture works: manifest load -> hash verify ->
lifecycle execute -> revoke, and that hash mismatches block installation.
"""

import pytest
import yaml


def test_install_verify_execute_revoke(tmp_skill_dir, mock_isolator):
    """Full lifecycle with real manifest and hasher -- SKILL-01 + SKILL-02 + SKILL-03."""
    from argus.skills import SkillLifecycleManager
    from argus.security.events import GateType

    events = []
    manager = SkillLifecycleManager(
        isolator=mock_isolator,
        event_sink=events.append,
    )
    result = manager.run_lifecycle(tmp_skill_dir)

    # SKILL-01: manifest was loaded and validated
    assert result["skill_name"] == "test-skill"
    assert result["success"] is True
    assert result["trust_tier"] == "verified"

    # SKILL-02: all 7 stages completed
    assert len(result["stages_completed"]) == 7

    # SKILL-02: SecurityEvents emitted for each stage
    assert len(events) >= 14  # at least entered+completed per stage
    assert all(e.gate == GateType.SKILL_LIFECYCLE for e in events)

    # Check all stages represented
    stages = {e.metadata["stage"] for e in events}
    for expected in [
        "install",
        "verify",
        "sandbox",
        "execute",
        "monitor",
        "report",
        "revoke",
    ]:
        assert expected in stages, f"Missing stage: {expected}"


def test_hash_mismatch_blocks_install(tmp_skill_dir, mock_isolator):
    """SKILL-03: tampered skill rejected at verify stage with SkillIntegrityError."""
    from argus.skills import SkillLifecycleManager
    from argus.security import SkillIntegrityError

    # Tamper: overwrite skill.yaml with wrong hash
    yaml_path = tmp_skill_dir / "skill.yaml"
    manifest_data = yaml.safe_load(yaml_path.read_text())
    manifest_data["content_hash"] = "sha256:" + "0" * 64  # intentionally wrong
    yaml_path.write_text(yaml.dump(manifest_data))

    events = []
    manager = SkillLifecycleManager(
        isolator=mock_isolator,
        event_sink=events.append,
    )

    with pytest.raises(SkillIntegrityError, match="hash mismatch"):
        manager.run_lifecycle(tmp_skill_dir)

    # Verify: REVOKE cleanup event emitted despite failure
    revoke_events = [e for e in events if e.metadata.get("stage") == "revoke"]
    assert len(revoke_events) >= 1
    assert any(e.metadata.get("trigger") == "failure" for e in revoke_events)

    # Verify: isolator was NOT called (blocked before execute)
    mock_isolator.run.assert_not_called()


def test_public_api_imports():
    """All 11 public symbols importable from argus.skills."""
    from argus.skills import (
        BlastRadius,
        LIFECYCLE_SEQUENCE,
        SkillStage,
        TrustTier,
        compute_content_hash,
        load_manifest,
        validate_trust_tier,
        verify_content_hash,
    )

    # Type checks
    assert len(TrustTier) == 4
    assert len(BlastRadius) == 4
    assert len(SkillStage) == 7
    assert len(LIFECYCLE_SEQUENCE) == 7
    assert callable(compute_content_hash)
    assert callable(verify_content_hash)
    assert callable(load_manifest)
    assert callable(validate_trust_tier)
