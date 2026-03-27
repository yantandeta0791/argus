"""argus serve — REST API sidecar (stub)."""

import typer


def serve_command(
    config: str = typer.Option("argus.yaml", "--config", help="Path to argus.yaml"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind"),
    port: int = typer.Option(8080, "--port", help="Port to listen on"),
) -> None:
    raise NotImplementedError


def build_app(gateway):
    raise NotImplementedError
