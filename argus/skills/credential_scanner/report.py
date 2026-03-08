"""Credential scanner report dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CredentialFinding:
    """A single redacted credential match."""

    credential_type: str
    severity: str
    match: str  # Redacted: first 4 chars + "****"
    location: str  # "line {N}"
    pattern_id: str


@dataclass
class ScanReport:
    """Result of scanning a text for credentials."""

    findings: list[CredentialFinding] = field(default_factory=list)
    clean: bool = True
    scanned_chars: int = 0
    scanned_at: str = ""
