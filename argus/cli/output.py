"""Rich terminal output helpers for Argus CLI."""
from __future__ import annotations
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console(force_terminal=True, file=sys.stdout)


def print_violation_table(violations: list[dict]) -> None:
    """Render violations as a Rich table. Stub — not yet implemented."""
    pass


def print_demo_header(injected: int, caught: int) -> None:
    """Render the demo benchmark header panel. Stub — not yet implemented."""
    pass
