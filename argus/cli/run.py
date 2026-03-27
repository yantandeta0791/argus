"""argus run — full Argus runtime execution."""

from __future__ import annotations
import asyncio
import os
from pathlib import Path
from argus.security.audit.daemon import AuditDaemon

import typer

app = typer.Typer()


@app.command()
def run_command(
    config: Path = typer.Option(
        Path("argus.yaml"), "--config", help="Path to argus.yaml"
    ),
    task: str = typer.Option("", "--task", help="Task string to run"),
    trace_dir: Path = typer.Option(
        Path("./runs"), "--trace-dir", help="Directory for trace output"
    ),
) -> None:
    """Execute an agent through the full Argus runtime."""
    # Fail fast: no API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        typer.echo(
            "Error: ANTHROPIC_API_KEY environment variable is not set.", err=True
        )
        raise typer.Exit(code=2)

    # Fail fast: no config file
    if not config.exists():
        typer.echo(f"Error: Config file not found: {config}", err=True)
        raise typer.Exit(code=2)

    asyncio.run(_run_async(config, task, trace_dir))


async def _run_async(config: Path, task: str, trace_dir: Path) -> None:
    """Wire and run the full Argus runtime stack."""
    import yaml
    from argus.llm.config import load_config, load_gateway_config
    from argus.llm.tracker import SpendTracker
    from argus.llm.router import LLMRouter
    from argus.engine.machine import StateMachine
    from argus.engine.states import RunContext
    from argus.security.gateway import SecurityGateway
    from argus.security.audit.logger import AuditLogger
    from argus.security.redactor.redactor import SecretRedactor
    from argus.memory.manager import MemoryManager, MemoryConfig
    from argus.observability.manager import ObservabilityManager, ObsConfig
    from argus.observability.otel import build_security_otel_emitter

    # Create trace directory
    trace_dir.mkdir(parents=True, exist_ok=True)

    # Observability — write trace and security stream to trace_dir
    obs = ObservabilityManager(
        ObsConfig(
            trace_path=trace_dir / "trace.jsonl",
            security_stream_path=trace_dir / "security.jsonl",
            enabled=True,
        )
    )

    # Load raw YAML once for both model config and gateway config
    with open(config) as f:
        raw = yaml.safe_load(f) or {}

    model_config = load_config(config)
    tracker = SpendTracker(model_config.spend)
    router = LLMRouter(
        config=model_config, tracker=tracker, obs=obs, redactor=SecretRedactor()
    )

    # Security gateway — real audit daemon and logger
    socket_path = str(trace_dir / "audit.sock")
    log_path = str(trace_dir / "audit.jsonl")
    daemon = AuditDaemon(socket_path=socket_path, log_path=log_path)
    daemon.start()
    try:
        audit_logger = AuditLogger(socket_path)
        gateway_config = load_gateway_config(raw)
        security_otel = None
        if gateway_config.otel is not None:
            security_otel = build_security_otel_emitter(gateway_config.otel)
        gateway = SecurityGateway(
            config=gateway_config, audit_logger=audit_logger, obs=obs,
            security_otel=security_otel,
        )

        # Memory — scoped DB to this run's trace_dir
        memory = MemoryManager(MemoryConfig(db_path=trace_dir / "memory.db"))
        await memory.connect()

        try:
            sm = StateMachine(
                gateway=gateway,
                cost_hook=tracker.over_budget,
                llm_callable=router,
                store=memory.session("run-session"),
                obs=obs,
            )
            ctx = RunContext(
                task_id="cli-run",
                task_input={"goal": task if task else "demo task"},
            )
            result = await sm.run(ctx)
            result.cost_breakdown = (
                tracker.entries()
            )  # populate per-state cost data (OBS-03)
            obs.on_run_complete(result)
            obs.flush()

            if result.success:
                typer.echo(
                    f"Run complete. Trace written to {trace_dir / 'trace.jsonl'}"
                )
                raise typer.Exit(code=0)
            else:
                typer.echo(
                    f"Run failed: {result.error or 'security violation or cost abort'}",
                    err=True,
                )
                raise typer.Exit(code=1)
        finally:
            await memory.close()
    finally:
        daemon.stop()
