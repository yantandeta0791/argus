"""CLI tests for argus scan command (CLI-03)."""

import json
from pathlib import Path
from typer.testing import CliRunner

runner = CliRunner()


def test_scan_clean_exits_zero(tmp_path):
    """A skill directory with no violations exits 0."""
    from argus.cli.main import app

    # Create a minimal valid skill directory (security_audit skill dir is clean)
    skill_dir = Path("argus/skills/security_audit")
    result = runner.invoke(app, ["scan", str(skill_dir)])
    assert result.exit_code == 0


def test_scan_dirty_exits_one(tmp_path):
    """A skill directory with ERROR/CRITICAL findings exits 1."""
    from argus.cli.main import app

    # Create a skill directory lacking required manifest fields
    skill_dir = tmp_path / "bad_skill"
    skill_dir.mkdir()
    (skill_dir / "skill.yaml").write_text("name: bad\n")  # missing required fields
    result = runner.invoke(app, ["scan", str(skill_dir)])
    assert result.exit_code == 1


def test_scan_missing_target_exits_two(tmp_path):
    """A non-existent target path exits 2."""
    from argus.cli.main import app

    result = runner.invoke(app, ["scan", str(tmp_path / "does_not_exist")])
    assert result.exit_code == 2


def test_scan_json_format(tmp_path):
    """--format json outputs valid JSON to stdout."""
    from argus.cli.main import app

    skill_dir = tmp_path / "bad_skill"
    skill_dir.mkdir()
    (skill_dir / "skill.yaml").write_text("name: bad\n")
    result = runner.invoke(app, ["scan", str(skill_dir), "--format", "json"])
    # Must be parseable JSON
    data = json.loads(result.output)
    assert "findings" in data
