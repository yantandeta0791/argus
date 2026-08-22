"""
Egress allowlist checker with two enforcement modes.

Modes:
  log_only (default) — v0.x behavior. Out-of-allowlist hostnames emit a
                       SecurityEvent but never raise.
  enforce            — v0.6 behavior. Out-of-allowlist hostnames emit the
                       SecurityEvent AND raise EgressViolationError, failing
                       the tool call closed.

The mode is configured per-gateway via GatewayConfig.egress_enforce (bool).
This is application-level enforcement: it gates declared egress targets at
the tool boundary. Network-layer enforcement (containers/netns) remains the
deployment's responsibility and is documented in docs/egress-enforcement.md.
"""

from __future__ import annotations

from typing import Callable

from argus.security.events import GateType, SecurityEvent


class EgressChecker:
    """Allowlist checker for declared egress targets.

    Args:
        allowlist:  Hostnames the skill/tool may contact.
        event_sink: Callback receiving a SecurityEvent on violation.
        enforce:    When True, violations raise EgressViolationError after
                    emitting the event (fail-closed). When False (default),
                    violations are logged only — v0.x behavior.
    """

    def __init__(
        self,
        allowlist: list[str],
        event_sink: Callable[[SecurityEvent], None],
        enforce: bool = False,
    ):
        self._allowlist = set(allowlist)
        self._event_sink = event_sink
        self._enforce = enforce

    @property
    def enforce(self) -> bool:
        return self._enforce

    def check(self, hostname: str, skill_name: str) -> None:
        """Check hostname against the allowlist.

        In-allowlist: return silently.
        Violation:    emit SecurityEvent, then raise EgressViolationError when
                      enforcement is enabled — otherwise return (log-only).
        """
        from argus.security.exceptions import EgressViolationError

        if hostname in self._allowlist:
            return  # allowed, no event

        self._event_sink(
            SecurityEvent(
                gate=GateType.EGRESS,
                outcome="violation",
                tool_name=skill_name,
                blocked_value=hostname[:200],
                rule_triggered=f"not in allowlist: {sorted(self._allowlist)}",
                metadata={
                    "allowlist": sorted(self._allowlist),
                    "attempted_host": hostname,
                    "mode": "enforce" if self._enforce else "log_only",
                },
            )
        )
        if self._enforce:
            raise EgressViolationError(
                gate="egress",
                blocked=hostname,
                rule=f"not in allowlist: {sorted(self._allowlist)}",
            )
        # log_only mode: violation recorded, call continues (v0.x behavior)
