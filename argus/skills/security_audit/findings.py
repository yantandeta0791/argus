"""Finding dataclasses for Security Audit skill — stub."""
from __future__ import annotations
from enum import StrEnum
from dataclasses import dataclass


class Severity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class Finding:
    rule_id: str
    severity: Severity
    message: str
    location: str
    remediation: str


@dataclass
class AuditReport:
    target: str
    findings: list[Finding]
    passed: bool
    scanned_at: str
