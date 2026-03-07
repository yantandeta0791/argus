"""Integration tests for argus CLI (full e2e flows)."""
import time
import pytest
from typer.testing import CliRunner

runner = CliRunner()


def test_demo_timing():
    """Full demo run completes in under 10 seconds (no live LLM — all mocked)."""
    from argus.cli.main import app
    start = time.monotonic()
    result = runner.invoke(app, ["demo"])
    elapsed = time.monotonic() - start
    assert result.exit_code == 0
    assert elapsed < 10.0, f"Demo took {elapsed:.1f}s — must complete in < 10s"
