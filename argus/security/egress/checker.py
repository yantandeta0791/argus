from typing import Callable
from argus.security.events import SecurityEvent, GateType


class EgressChecker:
    """
    v1 egress allowlist checker — log-only, no network enforcement.

    Design note: EgressViolationError exists in the exception hierarchy but is NOT raised in v1.
    v1.1 upgrade: when container-level network enforcement is added (SBX-01),
    this method will raise EgressViolationError after logging the event.
    """

    def __init__(self, allowlist: list[str], event_sink: Callable[[SecurityEvent], None]):
        self._allowlist = set(allowlist)
        self._event_sink = event_sink

    def check(self, hostname: str, skill_name: str) -> None:
        """
        Check if hostname is in the allowlist.
        If not: emit a SecurityEvent. Never raises in v1 (log-only).
        """
        if hostname in self._allowlist:
            return  # allowed, no event

        # Violation: log it, do not block (v1 constraint — no network enforcement)
        self._event_sink(SecurityEvent(
            gate=GateType.EGRESS,
            outcome="violation",
            tool_name=skill_name,
            blocked_value=hostname[:200],
            rule_triggered=f"not in allowlist: {sorted(self._allowlist)}",
            metadata={"allowlist": sorted(self._allowlist), "attempted_host": hostname},
        ))
        # v1: return None — do not raise EgressViolationError
        # v1.1: raise EgressViolationError(gate="egress", blocked=hostname, rule="allowlist")
