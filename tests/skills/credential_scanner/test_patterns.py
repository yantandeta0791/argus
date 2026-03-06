"""Tests for credential scanner patterns — CS-001 through CS-007."""
import pytest


def test_cs001_aws_access_key():
    from argus.skills.credential_scanner import run

    text = "The config uses AKIAIOSFODNN7EXAMPLE1234 for authentication."
    report = run(text)
    assert len(report.findings) > 0
    assert any(f.pattern_id == "CS-001" for f in report.findings)
    assert any(f.credential_type == "AWS Access Key" for f in report.findings)


def test_cs002_aws_secret_key():
    from argus.skills.credential_scanner import run

    text = "aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    report = run(text)
    assert len(report.findings) > 0
    assert any(f.pattern_id == "CS-002" for f in report.findings)


def test_cs003_github_token():
    from argus.skills.credential_scanner import run

    text = "token: ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890"
    report = run(text)
    assert len(report.findings) > 0
    assert any(f.pattern_id == "CS-003" for f in report.findings)
    assert any(f.credential_type == "GitHub Token" for f in report.findings)


def test_cs004_anthropic_api_key():
    from argus.skills.credential_scanner import run

    text = "api_key=sk-ant-api03-" + "a" * 93
    report = run(text)
    assert len(report.findings) > 0
    assert any(f.pattern_id == "CS-004" for f in report.findings)
    assert any(f.credential_type == "Anthropic API Key" for f in report.findings)


def test_cs005_openai_api_key():
    from argus.skills.credential_scanner import run

    text = "OPENAI_KEY=sk-" + "A" * 48
    report = run(text)
    assert len(report.findings) > 0
    assert any(f.pattern_id == "CS-005" for f in report.findings)
    assert any(f.credential_type == "OpenAI API Key" for f in report.findings)


def test_cs006_bearer_token():
    from argus.skills.credential_scanner import run

    text = "Authorization: Bearer abc123tokenXYZ"
    report = run(text)
    assert len(report.findings) > 0
    assert any(f.pattern_id == "CS-006" for f in report.findings)
    assert any(f.credential_type == "Bearer Token" for f in report.findings)


def test_cs007_generic_secret():
    from argus.skills.credential_scanner import run

    text = "api_key=supersecretvalue123"
    report = run(text)
    assert len(report.findings) > 0
    assert any(f.pattern_id == "CS-007" for f in report.findings)
