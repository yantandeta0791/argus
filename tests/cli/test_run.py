"""CLI tests for argus run command (CLI-02)."""
import pytest
from typer.testing import CliRunner

runner = CliRunner()


@pytest.mark.xfail(reason="argus.cli.run not yet implemented", strict=False)
def test_run_no_api_key_exits_2(tmp_path, monkeypatch):
    """argus run without ANTHROPIC_API_KEY exits 2 with a friendly error."""
    from argus.cli.main import app
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 2
    assert "ANTHROPIC_API_KEY" in result.output or "ANTHROPIC_API_KEY" in (result.stderr or "")


@pytest.mark.xfail(reason="argus.cli.run not yet implemented", strict=False)
def test_run_missing_config_exits_2(tmp_path, monkeypatch):
    """argus run with a non-existent config file exits 2."""
    from argus.cli.main import app
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    result = runner.invoke(app, ["run", "--config", str(tmp_path / "no_such_file.yaml")])
    assert result.exit_code == 2
