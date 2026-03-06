"""Integration xfail stubs for Credential Scanner skill."""
import pytest


@pytest.mark.xfail(strict=True, raises=NotImplementedError)
def test_run_string_context():
    from argus.skills.credential_scanner import run

    text = "The key is AKIAIOSFODNN7EXAMPLE1234 in plain sight."
    report = run(text)
    assert len(report.findings) > 0
    assert any(f.credential_type == "AWS Access Key" for f in report.findings)
    assert report.clean is False


@pytest.mark.xfail(strict=True, raises=NotImplementedError)
def test_run_dict_context():
    from argus.skills.credential_scanner import run

    context = {"api_key": "ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890"}
    report = run(context)
    assert len(report.findings) > 0
    assert any(f.credential_type == "GitHub Token" for f in report.findings)


@pytest.mark.xfail(strict=True, raises=NotImplementedError)
def test_run_clean():
    from argus.skills.credential_scanner import run

    report = run("hello world no secrets here")
    assert report.clean is True
    assert len(report.findings) == 0
