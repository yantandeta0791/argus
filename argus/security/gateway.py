"""
SecurityGateway — single entry point for all security enforcement.

Phase 2 calls:
    gateway.pre_tool_call(agent_role, tool_name, tool_input) -> dict
    gateway.post_tool_call(tool_output, skill_manifest=None) -> str

Gate execution order (fixed, non-negotiable):
    PRE:  1. Permission check  2. Audit pre-call event
    POST: 3. Injection scan    4. Secret/PII redaction  5. Egress check  6. Audit post-call event
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from argus.security.exceptions import ArgusSecurityError
from argus.security.permission.enforcer import PermissionEnforcer
from argus.security.permission.policy import PolicyConfig
from argus.security.prompt_shield.shield import PromptShield
from argus.security.redactor.redactor import SecretRedactor
from argus.security.egress.checker import EgressChecker
from argus.security.audit.logger import AuditLogger
from argus.security.events import SecurityEvent, GateType


@dataclass
class GatewayConfig:
    """
    Flat config for SecurityGateway. Constructed from argus.yaml at startup.
    All fields have safe defaults — permissive with no policy.
    """

    permissions: Optional[PolicyConfig] = None
    prompt_shield_patterns: list[str] = field(default_factory=list)
    egress_allowlist: list[str] = field(default_factory=list)


class SecurityGateway:
    """
    Composes all security gates. Phase 2 has exactly one try/except ArgusSecurityError boundary.
    Agents run INSIDE Argus — no LLM output, no agent config can bypass these gates.
    """

    def __init__(
        self, config: GatewayConfig, audit_logger: AuditLogger, obs: Any = None
    ):
        self._permission = PermissionEnforcer(config.permissions)
        self._shield = PromptShield(
            extra_patterns=config.prompt_shield_patterns or None
        )
        self._redactor = SecretRedactor()
        self._audit = audit_logger
        self._obs = obs
        # EgressChecker with a closure sink that forwards to obs if configured (Phase 7)
        self._security_events: list[SecurityEvent] = []

        def _egress_sink(event: SecurityEvent) -> None:
            self._security_events.append(event)
            if self._obs:
                self._obs.on_security_event(event)

        self._egress = EgressChecker(
            allowlist=config.egress_allowlist,
            event_sink=_egress_sink,
        )

    def pre_tool_call(
        self,
        agent_role: str,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Run before tool execution.
        Gate 1 — Permission: raises PermissionDeniedError if role cannot call tool.
        Gate 2 — Audit: raises AuditUnavailableError if logger is unreachable (fail-closed).
        Returns tool_input unchanged.
        """
        # Gate 1: Permission (hard stop)
        try:
            self._permission.enforce(agent_role, tool_name)
        except ArgusSecurityError as exc:
            if self._obs:
                event = SecurityEvent(
                    gate=GateType.PERMISSION,
                    outcome="blocked",
                    agent_role=agent_role,
                    tool_name=tool_name,
                    rule_triggered=getattr(exc, "rule", None),
                )
                self._obs.on_security_event(event)
            raise

        # Gate 2: Audit pre-call (hard stop — fail-closed)
        self._audit.send(
            {
                "event_type": "tool_call_pre",
                "agent_role": agent_role,
                "tool_name": tool_name,
                # tool_input deliberately omitted from audit — may contain sensitive params
                # Phase 7 adds structured input logging with redaction applied first
            }
        )

        return tool_input

    def post_tool_call(
        self,
        tool_output: str,
        skill_manifest: Any = None,
    ) -> str:
        """
        Run after tool returns, before output enters LLM context.
        Gate 3 — Injection: raises InjectionDetectedError; caller must use PLACEHOLDER.
        Gate 4 — Redaction: soft block; returns sanitized output.
        Gate 5 — Egress: log-only; emits SecurityEvent, never raises (v1).
        Gate 6 — Audit: raises AuditUnavailableError if logger unreachable (fail-closed).
        Returns clean (redacted) output.
        """
        # Gate 3: Prompt injection scan (hard stop)
        try:
            self._shield.scan(tool_output)
        except ArgusSecurityError as exc:
            if self._obs:
                event = SecurityEvent(
                    gate=GateType.PROMPT_SHIELD,
                    outcome="blocked",
                    tool_name="[post_tool_call]",
                    rule_triggered=getattr(exc, "rule", None),
                )
                self._obs.on_security_event(event)
            raise

        # Gate 4: Secret/PII redaction (soft block — run continues with scrubbed data)
        clean_output = self._redactor.redact(tool_output)

        # Gate 5: Egress allowlist check (log-only in v1)
        if skill_manifest is not None:
            egress_list = getattr(skill_manifest, "egress_allowlist", []) or []
            skill_name = getattr(skill_manifest, "name", "unknown")
            for hostname in egress_list:
                # Check each declared egress host against the allowlist
                self._egress.check(hostname=hostname, skill_name=skill_name)

        # Gate 6: Audit post-call (hard stop — fail-closed)
        self._audit.send(
            {
                "event_type": "tool_call_post",
                "output_length": len(clean_output),
                # Full clean_output deliberately omitted from audit payload —
                # AuditLogger caller (log_process) receives a summary, not raw data.
                # Phase 7 adds structured output logging.
            }
        )

        return clean_output

    @property
    def security_events(self) -> list[SecurityEvent]:
        """Read-only access to accumulated security events (for Phase 7 stream sink)."""
        return list(self._security_events)
