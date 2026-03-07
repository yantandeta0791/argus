"""Argus CLI entry point."""
import typer

app = typer.Typer(
    name="argus",
    help="Deterministic security enforcement layer for AI agents.",
    no_args_is_help=True,
    add_completion=False,
)


def _register() -> None:
    from argus.cli import demo as demo_mod
    from argus.cli import run as run_mod
    from argus.cli.scan import scan_command

    app.add_typer(demo_mod.app, name="demo")
    app.add_typer(run_mod.app, name="run")
    # Register scan_command directly so `argus scan <target>` works as a
    # first-class command (not a group), which allows positional arguments.
    app.command(name="scan")(scan_command)


_register()
