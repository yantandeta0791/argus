"""xfail stubs for Security Audit checker — SA-001 through SA-007."""
import pytest


@pytest.mark.xfail(strict=True, raises=NotImplementedError)
def test_sa001_missing_required_fields(tmp_path):
    from argus.skills.security_audit import run
    from argus.skills.security_audit.findings import Severity

    # Create a skill.yaml missing required fields
    (tmp_path / "skill.yaml").write_text(
        "name: bad-skill\nversion: '1.0.0'\n"  # missing permissions, content_hash
    )
    report = run(tmp_path)
    assert any(f.rule_id == "SA-001" for f in report.findings)
    assert any(f.severity == Severity.ERROR for f in report.findings)


@pytest.mark.xfail(strict=True, raises=NotImplementedError)
def test_sa002_trust_tier_mismatch(tmp_path):
    from argus.skills.security_audit import run

    # builtin trust tier declared but skill is outside argus/skills/
    (tmp_path / "skill.yaml").write_text(
        "name: external-skill\nversion: '1.0.0'\ntrust_tier: builtin\n"
        "permissions: []\ncontent_hash: 'sha256:" + "a" * 64 + "'\n"
    )
    report = run(tmp_path)
    assert any(f.rule_id == "SA-002" for f in report.findings)


@pytest.mark.xfail(strict=True, raises=NotImplementedError)
def test_sa003_high_blast_radius_no_egress(tmp_path):
    from argus.skills.security_audit import run

    # SYSTEM blast radius with no egress_allowlist
    (tmp_path / "skill.yaml").write_text(
        "name: dangerous-skill\nversion: '1.0.0'\ntrust_tier: community\n"
        "permissions: []\ncontent_hash: 'sha256:" + "a" * 64 + "'\n"
        "blast_radius: system\negress_allowlist: []\n"
    )
    report = run(tmp_path)
    assert any(f.rule_id == "SA-003" for f in report.findings)


@pytest.mark.xfail(strict=True, raises=NotImplementedError)
def test_sa004_wildcard_permissions(tmp_path):
    from argus.skills.security_audit import run

    # permissions list contains wildcard
    (tmp_path / "skill.yaml").write_text(
        "name: wild-skill\nversion: '1.0.0'\ntrust_tier: community\n"
        "permissions: ['*']\ncontent_hash: 'sha256:" + "a" * 64 + "'\n"
    )
    report = run(tmp_path)
    assert any(f.rule_id == "SA-004" for f in report.findings)


@pytest.mark.xfail(strict=True, raises=NotImplementedError)
def test_sa005_invalid_content_hash_format(tmp_path):
    from argus.skills.security_audit import run

    # content_hash missing sha256: prefix
    (tmp_path / "skill.yaml").write_text(
        "name: bad-hash-skill\nversion: '1.0.0'\ntrust_tier: community\n"
        "permissions: []\ncontent_hash: 'notahash'\n"
    )
    report = run(tmp_path)
    assert any(f.rule_id == "SA-005" for f in report.findings)


@pytest.mark.xfail(strict=True, raises=NotImplementedError)
def test_sa006_nonidempotent_network_blast(tmp_path):
    from argus.skills.security_audit import run

    # idempotent=False with network blast_radius
    (tmp_path / "skill.yaml").write_text(
        "name: risky-skill\nversion: '1.0.0'\ntrust_tier: community\n"
        "permissions: []\ncontent_hash: 'sha256:" + "a" * 64 + "'\n"
        "blast_radius: network\nidempotent: false\negress_allowlist: ['api.example.com']\n"
    )
    report = run(tmp_path)
    assert any(f.rule_id == "SA-006" for f in report.findings)


@pytest.mark.xfail(strict=True, raises=NotImplementedError)
def test_sa007_excessive_timeout(tmp_path):
    from argus.skills.security_audit import run

    # timeout_s > 300
    (tmp_path / "skill.yaml").write_text(
        "name: slow-skill\nversion: '1.0.0'\ntrust_tier: community\n"
        "permissions: []\ncontent_hash: 'sha256:" + "a" * 64 + "'\n"
        "timeout_s: 600.0\n"
    )
    report = run(tmp_path)
    assert any(f.rule_id == "SA-007" for f in report.findings)
