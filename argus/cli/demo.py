"""argus demo — synthetic security benchmark."""
import typer

app = typer.Typer()


@app.command()
def demo_command() -> None:
    """Run synthetic security benchmark — no API key required."""
    raise NotImplementedError("argus demo not yet implemented")
