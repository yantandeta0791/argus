"""CLI tests for argus demo command (CLI-01)."""

from typer.testing import CliRunner

runner = CliRunner()


def test_demo_exits_zero():
    from argus.cli.main import app

    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 0


def test_demo_output_contains_four_caught():
    from argus.cli.main import app

    result = runner.invoke(app, ["demo"])
    assert "4 caught" in result.output


def test_demo_table_has_four_rows():
    from argus.cli.main import app

    result = runner.invoke(app, ["demo"])
    # Table has 4 violation rows (numbered 1-4)
    assert "Permission Denied" in result.output
    assert "Prompt Injection" in result.output
    assert "Credential" in result.output
    assert "OWASP" in result.output
