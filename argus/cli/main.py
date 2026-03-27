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
    from argus.cli.audit import audit_command
    from argus.cli.serve import serve_command

    # Register all commands directly so they work as first-class commands
    # (not groups), matching `argus run`, `argus scan <target>`, `argus demo`, `argus audit` patterns.
    app.command(name="run")(run_command)
    app.command(name="scan")(scan_command)
    app.command(name="demo")(demo_command)
    app.command(name="audit")(audit_command)
    app.command(name="serve")(serve_command)


_register()
