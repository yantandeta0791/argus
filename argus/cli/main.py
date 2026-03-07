"""Argus CLI entry point."""
import typer

app = typer.Typer(
    name="argus",
    help="Deterministic security enforcement layer for AI agents.",
    no_args_is_help=True,
    add_completion=False,
)


def _register() -> None:
    from argus.cli.run import run_command
    from argus.cli.scan import scan_command
    from argus.cli.demo import demo_command

    # Register all three commands directly so they work as first-class commands
    # (not groups), matching `argus run`, `argus scan <target>`, `argus demo` patterns.
    app.command(name="run")(run_command)
    app.command(name="scan")(scan_command)
    app.command(name="demo")(demo_command)


_register()
