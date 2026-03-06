"""End-to-end integration tests for all three Tier 1 skills."""
import pytest
import yaml
from pathlib import Path

from argus.skills import load_manifest, verify_content_hash, compute_content_hash


# --- Security Audit ---

def test_security_audit_produces_findings(tmp_path):
    from argus.skills.security_audit import run
    # Create dirty skill.yaml: wildcard permissions + timeout > 300
    skill_dir = tmp_path / "dirty-skill"
    skill_dir.mkdir()
    (skill_dir / "__init__.py").write_text("# stub\n")
    real_hash = compute_content_hash(skill_dir)
    manifest = {
        "name": "dirty-skill", "version": "1.0.0",
        "description": "dirty", "trust_tier": "verified",
        "permissions": ["*"],  # SA-004
        "content_hash": real_hash,
        "timeout_s": 400.0,   # SA-007
    }
    (skill_dir / "skill.yaml").write_text(yaml.dump(manifest))
    report = run(skill_dir)
    assert not report.passed
    rule_ids = [f.rule_id for f in report.findings]
    assert "SA-004" in rule_ids
    assert "SA-007" in rule_ids


def test_security_audit_clean_manifest_passes(tmp_path):
    from argus.skills.security_audit import run
    skill_dir = tmp_path / "clean-skill"
    skill_dir.mkdir()
    (skill_dir / "__init__.py").write_text("# stub\n")
    real_hash = compute_content_hash(skill_dir)
    manifest = {
        "name": "clean-skill", "version": "1.0.0",
        "description": "clean", "trust_tier": "verified",
        "permissions": ["file:read"],
        "content_hash": real_hash,
    }
    (skill_dir / "skill.yaml").write_text(yaml.dump(manifest))
    report = run(skill_dir)
    assert report.passed
    assert report.findings == []


# --- OWASP Top 10 ---

def test_owasp_detects_excessive_permissions():
    from argus.skills.owasp_top10 import run
    report = run({"permissions": ["*"]})
    asi02 = next(c for c in report.categories if c.category_id == "ASI02")
    assert not asi02.passed
    assert report.failed_count >= 1


def test_owasp_clean_config_all_pass():
    from argus.skills.owasp_top10 import run
    # Provide all required fields so every ASI check passes
    config = {
        "cost_cap": 1.0,           # ASI07: cost_cap present
        "audit_log_path": "/tmp/audit.log",  # ASI08: audit_log_path present
    }
    report = run(config)
    assert report.passed_count == 10
    assert report.coverage_pct == 100.0


# --- Credential Scanner ---

def test_credential_scanner_detects_aws_key():
    from argus.skills.credential_scanner import run
    report = run("AKIAIOSFODNN7EXAMPLE12345678")
    assert not report.clean
    assert len(report.findings) >= 1
    assert report.findings[0].pattern_id == "CS-001"
    assert report.findings[0].match.endswith("****")


def test_credential_scanner_clean_text():
    from argus.skills.credential_scanner import run
    report = run("no credentials in this text whatsoever")
    assert report.clean
    assert report.findings == []


# --- Phase 5 hash verification ---

def test_all_three_skill_manifests_load_and_verify():
    skills_root = Path(__file__).parent.parent.parent / "argus" / "skills"
    for name in ["security_audit", "owasp_top10", "credential_scanner"]:
        skill_dir = skills_root / name
        manifest = load_manifest(skill_dir)
        assert verify_content_hash(skill_dir, manifest.content_hash), \
            f"Hash mismatch for {name}: manifest has {manifest.content_hash}"
        assert manifest.trust_tier == "builtin"
        assert manifest.blast_radius == "local"
        assert manifest.idempotent is True
