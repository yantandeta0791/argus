"""argus serve — REST API sidecar."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import typer
from pydantic import BaseModel


class ToolCallRequest(BaseModel):
    agent_role: str
    tool_name: str
    tool_input: dict[str, Any]
    tool_output: str | None = None
    caller_id: str | None = None  # MAGNT-01: calling agent identity
    hop_depth: int = 0  # MAGNT-01: delegation depth from root supervisor


class ToolCallResponse(BaseModel):
    decision: str
    tool_output: str | None = None
    violation: str | None = None
    detail: str | None = None
    audit_entry: dict[str, Any]


def build_app(gateway):
    """Build and return the FastAPI app. Testable seam — no uvicorn dependency."""
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse

    from argus.security.exceptions import ArgusSecurityError

    app = FastAPI(title="Argus REST Sidecar")

    @app.get("/")
    async def health_check():
        return {"status": "ok"}

    @app.post("/tool-call", response_model=ToolCallResponse)
    async def tool_call(req: ToolCallRequest):
        from argus.security.hitl import HITLConfig

        # HITL guard: REST cannot handle terminal-based HITL approval
        hitl_config = getattr(gateway, "_hitl_config", None)
        if isinstance(hitl_config, HITLConfig) and hitl_config.needs_approval(
            req.tool_name
        ):
            return JSONResponse(
                status_code=503,
                content={
                    "decision": "block",
                    "violation": "hitl_unavailable",
                    "detail": (
                        "HITL approval is terminal-only and not supported over REST in v0.3.0. "
                        "See HITL-06 for future webhook support."
                    ),
                    "audit_entry": {
                        "event_type": "hitl_unavailable",
                        "agent_role": req.agent_role,
                        "tool_name": req.tool_name,
                    },
                },
            )

        # Pre-gate (with optional caller identity for multi-agent enforcement)
        gateway.pre_tool_call(
            req.agent_role,
            req.tool_name,
            req.tool_input,
            caller_id=req.caller_id,
            hop_depth=req.hop_depth,
        )

        # Post-gate (only if tool_output provided)
        redacted_output: str | None = None
        if req.tool_output is not None:
            redacted_output = gateway.post_tool_call(req.tool_output)

        audit_entry: dict[str, Any] = {
            "event_type": "tool_call_pre",
            "agent_role": req.agent_role,
            "tool_name": req.tool_name,
        }

        return ToolCallResponse(
            decision="allow",
            tool_output=redacted_output,
            audit_entry=audit_entry,
        )

    @app.exception_handler(ArgusSecurityError)
    async def security_error_handler(request: Request, exc: ArgusSecurityError):
        return JSONResponse(
            status_code=403,
            content={
                "decision": "block",
                "violation": exc.gate,
                "detail": str(exc),
                "audit_entry": {
                    "event_type": "violation",
                    "gate": exc.gate,
                    "tool_name": exc.blocked,
                    "rule": exc.rule,
                },
            },
        )

    return app


def serve_command(
    config: Path = typer.Option(
        Path("argus.yaml"), "--config", help="Path to argus.yaml"
    ),
    host: str = typer.Option("127.0.0.1", "--host", help="Bind address"),
    port: int = typer.Option(8080, "--port", help="Bind port"),
    audit_dir: Path = typer.Option(
        Path("./runs/serve"), "--audit-dir", help="Audit log directory"
    ),
) -> None:
    """Start the Argus REST API sidecar."""
    if not config.exists():
        typer.echo(f"Error: Config file not found: {config}", err=True)
        raise typer.Exit(code=2)

    asyncio.run(_serve_async(config, host, port, audit_dir))


async def _serve_async(config: Path, host: str, port: int, audit_dir: Path) -> None:
    """Wire and run the Argus REST sidecar."""
    try:
        import uvicorn
        import yaml
    except ImportError:
        typer.echo("Error: Install the REST extra: pip install argus[rest]")
        raise typer.Exit(code=2)

    from argus.llm.config import load_gateway_config
    from argus.security.audit.daemon import AuditDaemon
    from argus.security.audit.logger import AuditLogger
    from argus.security.gateway import SecurityGateway

    try:
        from argus.observability.otel import build_security_otel_emitter
    except ImportError:
        build_security_otel_emitter = None  # type: ignore[assignment]

    # Ensure audit directory exists
    audit_dir.mkdir(parents=True, exist_ok=True)

    socket_path = str(audit_dir / "audit.sock")
    log_path = str(audit_dir / "audit.jsonl")
    daemon = AuditDaemon(socket_path=socket_path, log_path=log_path)
    daemon.start()

    try:
        with open(config) as f:
            raw = yaml.safe_load(f) or {}

        gateway_config = load_gateway_config(raw)

        audit_logger = AuditLogger(socket_path)

        security_otel = None
        if build_security_otel_emitter is not None and gateway_config.otel is not None:
            security_otel = build_security_otel_emitter(gateway_config.otel)

        gateway = SecurityGateway(
            config=gateway_config,
            audit_logger=audit_logger,
            security_otel=security_otel,
        )

        app = build_app(gateway)

        typer.echo(f"Argus REST sidecar listening on http://{host}:{port}")

        server_config = uvicorn.Config(app, host=host, port=port, log_level="warning")
        server = uvicorn.Server(server_config)
        await server.serve()
    finally:
        daemon.stop()
