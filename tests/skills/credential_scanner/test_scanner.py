"""xfail stubs for credential scanner core behavior."""
import pytest


@pytest.mark.xfail(strict=True, raises=NotImplementedError)
def test_clean_context_no_findings():
    from argus.skills.credential_scanner import run

    text = "Hello world, this is a completely clean string with no secrets."
    report = run(text)
    assert report.clean is True
    assert report.findings == []


@pytest.mark.xfail(strict=True, raises=NotImplementedError)
def test_dict_context_serialized():
    from argus.skills.credential_scanner import run

    # dict input is serialized to JSON before scanning
    context = {"message": "Hello world no secrets here", "user": "alice"}
    report = run(context)
    assert report.clean is True


@pytest.mark.xfail(strict=True, raises=NotImplementedError)
def test_match_redacted():
    from argus.skills.credential_scanner import run

    text = "token: ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890"
    report = run(text)
    assert len(report.findings) > 0
    finding = report.findings[0]
    # Match shows first 4 chars + "****"
    assert "****" in finding.match
    assert len(finding.match) > 4


@pytest.mark.xfail(strict=True, raises=NotImplementedError)
def test_multiple_credentials():
    from argus.skills.credential_scanner import run

    text = (
        "aws_key=AKIAIOSFODNN7EXAMPLE1234 "
        "and github token: ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890"
    )
    report = run(text)
    assert len(report.findings) >= 2
