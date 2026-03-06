"""Credential scanner report dataclasses — stub."""
from dataclasses import dataclass


@dataclass
class CredentialFinding:
    credential_type: str
    severity: str
    match: str
    location: str
    pattern_id: str


@dataclass
class ScanReport:
    findings: list[CredentialFinding]
    clean: bool
    scanned_chars: int
    scanned_at: str
