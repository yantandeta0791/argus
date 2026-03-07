"""argus scan — static security analysis."""
import typer
from pathlib import Path
from enum import Enum

app = typer.Typer()


class OutputFormat(str, Enum):
    text = "text"
    json = "json"


@app.command()
def scan_command(
    target: Path = typer.Argument(..., help="Path to skill directory or agent config YAML"),
    fmt: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    """Static security scan of a skill manifest or agent config."""
    raise NotImplementedError("argus scan not yet implemented")
