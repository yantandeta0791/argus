"""argus scan — static security analysis."""

from __future__ import annotations
import dataclasses
import json
from enum import Enum
from pathlib import Path

import typer

app = typer.Typer()


class OutputFormat(str, Enum):
    text = "text"
    json = "json"


@app.command()
def scan_command(
    target: Path = typer.Argument(
        ..., help="Path to skill directory or agent config YAML"
    ),
    fmt: OutputFormat = typer.Option(
        OutputFormat.text, "--format", help="Output format"
    ),
) -> None:
    """Static security scan of a skill manifest or agent config."""
    if not target.exists():
        typer.echo(f"Error: Target not found: {target}", err=True)
        raise typer.Exit(code=2)

    from argus.skills.security_audit import run as audit_run
    from argus.skills.lifecycle import SkillLifecycleManager
    from argus.security.exceptions import SkillIntegrityError
    from argus.cli.output import print_violation_table

    # Verify skill integrity before scanning if target is a skill directory.
    # SkillIntegrityError (hash mismatch on a valid manifest) aborts the scan --
    # a tampered skill must not be analysed.  Other errors (malformed manifest,
    # missing fields) are left for audit_run to report as SA-001 findings.
    skill_yaml = target / "skill.yaml" if target.is_dir() else None
    if skill_yaml and skill_yaml.exists():
        try:
            lifecycle = SkillLifecycleManager()
            lifecycle.verify_skill(target)
        except SkillIntegrityError:
            typer.echo(
                "Error: Skill integrity check failed — content hash mismatch", err=True
            )
            raise typer.Exit(code=1)
        except Exception:
            pass  # malformed manifest — let audit_run report it as SA-001

    report = audit_run(target)

    if fmt == OutputFormat.json:
        typer.echo(json.dumps(dataclasses.asdict(report), indent=2))
    else:
        if report.findings:
            violations = [
                {
                    "type": f.rule_id,
                    "severity": str(f.severity),
                    "details": f.message,
                }
                for f in report.findings
            ]
            print_violation_table(violations)
        else:
            typer.echo("No issues found.")

    raise typer.Exit(code=0 if report.passed else 1)
