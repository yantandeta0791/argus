"""Scan logic — finds credential matches in text."""

from __future__ import annotations

from argus.skills.credential_scanner.patterns import PATTERNS
from argus.skills.credential_scanner.report import CredentialFinding


def scan(text: str) -> list[CredentialFinding]:
    """Scan text for credential patterns.

    Args:
        text: The string to scan.

    Returns:
        List of CredentialFinding instances, sorted by span position.
        Overlapping matches are deduplicated: the pattern listed first in PATTERNS wins
        (lower pattern index takes precedence over higher-index patterns).
    """
    # Collect all (span_start, span_end, pattern_index, CredentialFinding)
    raw: list[tuple[int, int, int, CredentialFinding]] = []

    for pattern_index, pattern in enumerate(PATTERNS):
        pattern_id = pattern["pattern_id"]
        credential_type = pattern["credential_type"]
        severity = pattern["severity"]
        regex = pattern["regex"]

        for m in regex.finditer(text):
            raw_match = m.group(0)
            redacted = raw_match[:4] + "****"

            # Compute 1-indexed line number
            line_num = text[: m.start()].count("\n") + 1
            location = f"line {line_num}"

            finding = CredentialFinding(
                credential_type=credential_type,
                severity=severity,
                match=redacted,
                location=location,
                pattern_id=pattern_id,
            )
            raw.append((m.start(), m.end(), pattern_index, finding))

    if not raw:
        return []

    # Deduplicate: among overlapping spans, keep the one with lowest pattern_index.
    # Process matches in priority order (low pattern_index first), then accept greedily
    # but allow a higher-priority match to displace previously-accepted lower-priority ones.

    # Sort by pattern_index (priority) then span start
    raw.sort(key=lambda x: (x[2], x[0]))

    accepted: list[tuple[int, int, int, CredentialFinding]] = []

    for candidate in raw:
        c_start, c_end, c_pidx, c_finding = candidate

        # Find all accepted entries that overlap with this candidate
        overlapping = [
            (i, a_start, a_end, a_pidx)
            for i, (a_start, a_end, a_pidx, _) in enumerate(accepted)
            if c_start < a_end and c_end > a_start
        ]

        if not overlapping:
            # No overlap — accept directly
            accepted.append(candidate)
        else:
            # Candidate has lower priority (higher pattern_index) than any overlapping
            # accepted entry (since we process in priority order). Skip it.
            # (All overlapping accepted entries have lower pattern_index = higher priority)
            pass

    # Sort final accepted findings by span start position
    accepted.sort(key=lambda x: x[0])

    return [entry[3] for entry in accepted]
