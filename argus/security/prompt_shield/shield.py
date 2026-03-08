import re

from argus.security.exceptions import InjectionDetectedError
from argus.security.prompt_shield.patterns import BUILTIN_PATTERNS


class PromptShield:
    """Regex-based prompt injection scanner.

    Scans tool output for OWASP LLM01:2025-aligned injection patterns.
    All patterns are compiled once at init time — never per-call.
    Zero-width Unicode obfuscation characters are stripped before matching.

    Attributes:
        PLACEHOLDER: Replacement string callers should insert into LLM context
                     when InjectionDetectedError is caught.
    """

    PLACEHOLDER = "[BLOCKED: injection detected]"

    def __init__(self, extra_patterns: list[str] | None = None) -> None:
        all_patterns = BUILTIN_PATTERNS + (extra_patterns or [])
        # Compile at init time — never per-call (performance + ReDoS surface reduction)
        self._compiled = [
            re.compile(p, re.IGNORECASE | re.MULTILINE) for p in all_patterns
        ]

    def _normalize(self, text: str) -> str:
        """Collapse whitespace and strip zero-width Unicode obfuscation characters."""
        # Strip zero-width spaces first (before whitespace collapse)
        text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def scan(self, tool_output: str) -> None:
        """Scan tool output for injection patterns after normalization.

        Raises InjectionDetectedError if any pattern matches.
        Returns None if clean.

        Caller MUST replace tool_output with PLACEHOLDER in LLM context on exception.
        """
        normalized = self._normalize(tool_output)
        for pattern in self._compiled:
            match = pattern.search(normalized)
            if match:
                raise InjectionDetectedError(
                    gate="prompt_shield",
                    blocked=match.group(0)[:200],
                    rule=pattern.pattern,
                )
