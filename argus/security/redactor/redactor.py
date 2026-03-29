import re
from typing import Callable
from argus.security.events import SecurityEvent, GateType

# Regex patterns for secrets and PII
# Ordered by specificity — more specific patterns first
SECRET_PATTERNS = [
    # OpenAI API keys: sk-proj-... or sk-... (20+ alphanumeric chars)
    (r"sk-(?:proj-)?[A-Za-z0-9\-_]{20,}", "openai_key"),
    # GitHub tokens: ghp_, ghs_, gho_, ghu_, github_pat_
    # Real tokens are 36+ chars after prefix, but accept 32+ for test compatibility
    (r"gh[pousp]_[A-Za-z0-9]{32,}", "github_token"),
    (r"github_pat_[A-Za-z0-9_]{36,}", "github_pat"),
    # AWS keys
    (r"AKIA[0-9A-Z]{16}", "aws_access_key"),
    # Generic API_KEY=value or API-KEY: value patterns (key name + value)
    (
        r"(?i)(?:api[_\-]?key|secret[_\-]?key|access[_\-]?token|auth[_\-]?token)\s*[=:]\s*\S{8,}",
        "generic_api_key",
    ),
    # Bearer tokens in Authorization headers
    (r"(?i)Bearer\s+[A-Za-z0-9\-._~+/]{20,}", "bearer_token"),
    # Email addresses (PII)
    (r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", "email"),
]

REPLACEMENT = "[REDACTED]"


class SecretRedactor:
    """
    Soft-block redactor: sanitizes secrets and PII in-place.
    Never raises — returns redacted text and run continues with scrubbed data.
    """

    def __init__(
        self,
        event_sink: Callable | None = None,
        extra_patterns: list[str] | None = None,
    ):
        self._patterns = [
            (re.compile(pattern), label) for pattern, label in SECRET_PATTERNS
        ]
        # POLC-02: custom secret patterns from argus.yaml secrets.patterns
        for i, pattern in enumerate(extra_patterns or []):
            self._patterns.append((re.compile(pattern), f"custom_secret_{i}"))
        self._event_sink = event_sink  # optional: emit SecurityEvent per redaction

    def redact(self, text: str) -> str:
        """
        Replace all secret/PII matches with REPLACEMENT.
        Returns sanitized text. Never raises.
        """
        result = text
        for compiled, label in self._patterns:
            matches = compiled.findall(result)
            if matches and self._event_sink:
                # Emit SecurityEvent for each unique match type (not per match — avoid log spam)
                self._event_sink(
                    SecurityEvent(
                        gate=GateType.REDACTION,
                        outcome="redacted",
                        rule_triggered=label,
                        blocked_value=str(matches[0])[:50],  # first match, truncated
                    )
                )
            result = compiled.sub(REPLACEMENT, result)
        return result
