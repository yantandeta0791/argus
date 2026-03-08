"""SKILL-02 lifecycle tests -- 7-stage skill lifecycle management.

Tests that SkillLifecycleManager drives skills through all stages,
emits SecurityEvents, delegates to SkillIsolator, and handles failures.
"""
import pytest
import yaml


def test_full_lifecycle(tmp_skill_dir, mock_isolator):
    """SKILL-02: runs through all 7 stages for a valid skill."""
    from argus.skills.lifecycle import SkillLifecycleManager
    events = []
    manager = SkillLifecycleManager(
        isolator=mock_isolator, event_sink=events.append,
    )
    result = manager.run_lifecycle(tmp_skill_dir)
    assert result["success"] is True
    assert result["skill_name"] == "test-skill"
    assert len(result["stages_completed"]) == 7


def test_stage_events(tmp_skill_dir, mock_isolator):
    """SKILL-02: each transition emits SecurityEvent with GateType.SKILL_LIFECYCLE."""
    from argus.skills.lifecycle import SkillLifecycleManager
    from argus.security.events import GateType
    events = []
    manager = SkillLifecycleManager(
        isolator=mock_isolator, event_sink=events.append,
    )
    manager.run_lifecycle(tmp_skill_dir)
    assert len(events) >= 14  # 7 stages x 2 events (entered + completed)
    assert all(e.gate == GateType.SKILL_LIFECYCLE for e in events)
    # Check stage metadata is present
    stages_seen = {e.metadata["stage"] for e in events}
    assert "install" in stages_seen
    assert "verify" in stages_seen
    assert "execute" in stages_seen
    assert "revoke" in stages_seen


def test_failure_triggers_revoke(tmp_skill_dir, mock_isolator):
    """SKILL-02: stage failure triggers cleanup revocation."""
    from argus.skills.lifecycle import SkillLifecycleManager
    from argus.security import SkillIntegrityError

    # Tamper with manifest to cause verify failure (wrong hash)
    yaml_path = tmp_skill_dir / "skill.yaml"
    manifest_data = yaml.safe_load(yaml_path.read_text())
    manifest_data["content_hash"] = "sha256:" + "0" * 64  # wrong hash
    yaml_path.write_text(yaml.dump(manifest_data))

    events = []
    manager = SkillLifecycleManager(
        isolator=mock_isolator, event_sink=events.append,
    )
    with pytest.raises(SkillIntegrityError):
        manager.run_lifecycle(tmp_skill_dir)

    # Verify REVOKE cleanup ran
    revoke_events = [e for e in events if e.metadata.get("stage") == "revoke"]
    assert len(revoke_events) >= 1
    assert any(e.metadata.get("trigger") == "failure" for e in revoke_events)


def test_verify_stage_checks_hash(tmp_skill_dir, mock_isolator):
    """SKILL-02: VERIFY stage calls hash verification and passes for valid skill."""
    from argus.skills.lifecycle import SkillLifecycleManager
    events = []
    manager = SkillLifecycleManager(
        isolator=mock_isolator, event_sink=events.append,
    )
    result = manager.run_lifecycle(tmp_skill_dir)
    verify_events = [e for e in events if e.metadata.get("stage") == "verify"]
    assert any(e.outcome == "completed" for e in verify_events)


def test_execute_stage_uses_isolator(tmp_skill_dir, mock_isolator):
    """SKILL-02: EXECUTE stage delegates to SkillIsolator."""
    from argus.skills.lifecycle import SkillLifecycleManager
    manager = SkillLifecycleManager(isolator=mock_isolator)
    manager.run_lifecycle(tmp_skill_dir)
    mock_isolator.run.assert_called_once()


def test_verify_skill_returns_manifest(tmp_skill_dir):
    """verify_skill runs INSTALL + VERIFY and returns the manifest."""
    from argus.skills.lifecycle import SkillLifecycleManager

    events = []
    lifecycle = SkillLifecycleManager(event_sink=events.append)
    manifest = lifecycle.verify_skill(tmp_skill_dir)

    assert manifest.name == "test-skill"
    assert manifest.trust_tier == "verified"

    # Only INSTALL and VERIFY stages should have been executed
    stages_seen = [e.metadata["stage"] for e in events]
    assert "install" in stages_seen
    assert "verify" in stages_seen
    # No SANDBOX, EXECUTE, etc.
    assert "sandbox" not in stages_seen
    assert "execute" not in stages_seen
    assert "revoke" not in stages_seen


def test_verify_skill_rejects_tampered_hash(tmp_skill_dir):
    """verify_skill raises SkillIntegrityError when content hash is wrong."""
    from argus.skills.lifecycle import SkillLifecycleManager
    from argus.security import SkillIntegrityError

    # Tamper with the manifest hash
    yaml_path = tmp_skill_dir / "skill.yaml"
    manifest_data = yaml.safe_load(yaml_path.read_text())
    manifest_data["content_hash"] = "sha256:" + "0" * 64
    yaml_path.write_text(yaml.dump(manifest_data))

    lifecycle = SkillLifecycleManager()
    with pytest.raises(SkillIntegrityError):
        lifecycle.verify_skill(tmp_skill_dir)


def test_verify_skill_builtin_skill():
    """verify_skill works on a real builtin skill directory."""
    from pathlib import Path
    from argus.skills.lifecycle import SkillLifecycleManager

    skill_dir = Path(__file__).parent.parent.parent / "argus" / "skills" / "security_audit"
    lifecycle = SkillLifecycleManager()
    manifest = lifecycle.verify_skill(skill_dir)

    assert manifest.name == "security-audit"
    assert manifest.trust_tier == "builtin"
