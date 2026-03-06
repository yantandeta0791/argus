"""Regex credential patterns — CS-001 through CS-007."""
from __future__ import annotations

import re

PATTERNS: list[dict] = [
    {
        "pattern_id": "CS-001",
        "credential_type": "AWS Access Key",
        "severity": "CRITICAL",
        "regex": re.compile(r"AKIA[0-9A-Z]{16}"),
    },
    {
        "pattern_id": "CS-002",
        "credential_type": "AWS Secret Key",
        "severity": "HIGH",
        # Require at least one base64-special char (/+=) to reduce false positives
        # on alphanumeric-only sequences (e.g. parts of Anthropic/OpenAI keys).
        "regex": re.compile(r"(?=[A-Za-z0-9/+=]{0,39}[/+=])[A-Za-z0-9/+=]{40}"),
    },
    {
        "pattern_id": "CS-003",
        "credential_type": "GitHub Token",
        "severity": "CRITICAL",
        "regex": re.compile(r"ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{82}"),
    },
    {
        "pattern_id": "CS-004",
        "credential_type": "Anthropic API Key",
        "severity": "CRITICAL",
        "regex": re.compile(r"sk-ant-[A-Za-z0-9\-_]{93,}"),
    },
    {
        "pattern_id": "CS-005",
        "credential_type": "OpenAI API Key",
        "severity": "CRITICAL",
        "regex": re.compile(r"sk-(?!ant-)[A-Za-z0-9]{48}"),
    },
    {
        "pattern_id": "CS-006",
        "credential_type": "Bearer Token",
        "severity": "HIGH",
        "regex": re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*"),
    },
    {
        "pattern_id": "CS-007",
        "credential_type": "Generic Secret",
        "severity": "WARNING",
        "regex": re.compile(
            r"(?i)(?:secret|password|api_key|token)\s*[:=]\s*[^\s]{8,}"
        ),
    },
]
