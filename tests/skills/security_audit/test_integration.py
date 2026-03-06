"""Integration xfail stubs for Security Audit skill."""
import pytest


@pytest.mark.xfail(strict=True, raises=NotImplementedError)
def test_clean_manifest_passes(tmp_path):
    from argus.skills.security_audit import run

    # A well-formed manifest should produce AuditReport.passed == True
    (tmp_path / "skill.yaml").write_text(
        "name: clean-skill\nversion: '1.0.0'\ntrust_tier: community\n"
        "permissions: []\ncontent_hash: 'sha256:" + "a" * 64 + "'\n"
        "blast_radius: local\nidempotent: true\ntimeout_s: 30.0\n"
    )
    report = run(tmp_path)
    assert report.passed is True
    assert report.findings == []


@pytest.mark.xfail(strict=True, raises=NotImplementedError)
def test_dirty_manifest_fails(tmp_path):
    from argus.skills.security_audit import run

    # SA-001 (missing fields) + SA-004 (wildcard permissions) → passed == False
    (tmp_path / "skill.yaml").write_text(
        "name: dirty-skill\npermissions: ['*']\n"  # missing version, content_hash
    )
    report = run(tmp_path)
    assert report.passed is False
    rule_ids = {f.rule_id for f in report.findings}
    assert "SA-001" in rule_ids or "SA-004" in rule_ids
