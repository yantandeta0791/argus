"""Rich terminal output helpers for Argus CLI."""
from __future__ import annotations
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# force_terminal=True ensures Rich writes color codes even inside CliRunner (non-TTY).
# No explicit file= so Rich resolves sys.stdout lazily — prevents "closed file" errors
# when pytest re-uses the module across multiple CliRunner invocations.
console = Console(force_terminal=True)

_SEVERITY_COLORS = {
    "CRITICAL": "bold red",
    "HIGH": "red",
    "WARNING": "yellow",
    "INFO": "dim",
}


def print_violation_table(violations: list[dict]) -> None:
    """Render violations as a Rich ROUNDED table."""
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Type", style="bold")
    table.add_column("Severity", justify="center")
    table.add_column("Details")

    for i, v in enumerate(violations, start=1):
        sev = v.get("severity", "INFO")
        color = _SEVERITY_COLORS.get(sev, "white")
        table.add_row(
            str(i),
            v.get("type", ""),
            f"[{color}]{sev}[/{color}]",
            v.get("details", ""),
        )
    console.print(table)


def print_demo_header(injected: int, caught: int) -> None:
    """Render the demo benchmark summary panel."""
    status = "[bold green]✓[/bold green]" if caught == injected else "[bold red]✗[/bold red]"
    console.print(Panel(
        f"  Argus Demo — Security Benchmark\n"
        f"  {injected} violations injected • {caught} caught {status}",
        box=box.ROUNDED,
    ))
