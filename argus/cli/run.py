"""argus run — full runtime execution."""
import typer
from pathlib import Path

app = typer.Typer()


@app.command()
def run_command(
    config: Path = typer.Option(Path("argus.yaml"), "--config", help="Path to argus.yaml"),
    task: str = typer.Option("", "--task", help="Task string to run"),
    trace_dir: Path = typer.Option(Path("./runs"), "--trace-dir", help="Directory for trace output"),
) -> None:
    """Execute an agent through the full Argus runtime."""
    raise NotImplementedError("argus run not yet implemented")
