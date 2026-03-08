"""Security Audit skill — scans skill manifests for misconfigurations."""

from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path

from argus.skills.security_audit.checker import check_manifest
from argus.skills.security_audit.findings import AuditReport


def run(target: Path) -> AuditReport:
    """Scan a skill directory for manifest misconfigurations.

    Args:
        target: Path to the skill directory containing skill.yaml.

    Returns:
        AuditReport with all findings and a passed bool (True iff no ERROR/CRITICAL).
    """
    findings = check_manifest(target)
    passed = all(f.severity not in ("ERROR", "CRITICAL") for f in findings)
    return AuditReport(
        target=str(target),
        findings=findings,
        passed=passed,
        scanned_at=datetime.now(timezone.utc).isoformat(),
    )
