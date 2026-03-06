"""Credential Scanner skill — detects exposed API keys, tokens, and secrets."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from argus.skills.credential_scanner.scanner import scan
from argus.skills.credential_scanner.report import ScanReport


def run(context: "str | dict") -> ScanReport:
    """Scan context for exposed credentials.

    Args:
        context: String or dict to scan. Dicts are serialized to JSON first.

    Returns:
        ScanReport with all findings (redacted matches) and a clean bool.
        clean is True iff no CRITICAL or HIGH severity findings.
    """
    if isinstance(context, dict):
        text = json.dumps(context)
    else:
        text = context

    findings = scan(text)
    clean = all(f.severity == "WARNING" for f in findings)
    return ScanReport(
        findings=findings,
        clean=clean,
        scanned_chars=len(text),
        scanned_at=datetime.now(timezone.utc).isoformat(),
    )
