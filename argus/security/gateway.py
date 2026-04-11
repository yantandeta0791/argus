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

from argus.security.anomaly.detector import AnomalyDetector, ResponseLevel
from argus.security.exceptions import (
    ArgusSecurityError,
    AnomalyBlockedError,
    ApprovalDeniedError,
    DelegationDepthError,
)
from argus.security.hitl import HITLConfig, HITLGate
from argus.security.identity import AgentRegistry, get_caller_context
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
    hitl: Optional[HITLConfig] = None
    otel: Optional[Any] = None  # OtelConfig from argus/llm/config.py (lazy typed to avoid circular import)
    agents: Optional[Any] = None  # AgentRegistryConfig (lazy typed to avoid circular import) — MAGNT-01
    max_delegation_depth: int = 3  # mirrors AgentRegistryConfig.max_delegation_depth — MAGNT-02
    anomaly: Optional[Any] = None  # AnomalyConfig (lazy typed to avoid circular import) — ANOM-01


class SecurityGateway:
    """
    Composes all security gates. Phase 2 has exactly one try/except ArgusSecurityError boundary.
    Agents run INSIDE Argus — no LLM output, no agent config can bypass these gates.
    """

    def __init__(
        self,
        config: GatewayConfig,
        audit_logger: AuditLogger,
        obs: Any = None,
        security_otel: Any = None,
    ):
        self._permission = PermissionEnforcer(config.permissions)
        self._shield = PromptShield(
            extra_patterns=config.prompt_shield_patterns or None
        )
        self._redactor = SecretRedactor(
            extra_patterns=config.prompt_shield_patterns or None,
        )
        self._audit = audit_logger
        self._obs = obs
        self._security_otel = security_otel  # OtelEmitter or None (OPS-04)
        # Store hitl config; HITLGate is instantiated lazily in pre_tool_call so
        # the module-level HITLGate reference remains patchable during tests.
        self._hitl_config = config.hitl
        # AgentRegistry for Gate 0.5 identity resolution (MAGNT-01)
        self._agent_registry = AgentRegistry(config.agents)
        # Gate 1.75 / Gate 5.5: per-metric AnomalyDetector instances (ANOM-01)
        if config.anomaly is not None:
            self._anomaly_freq = AnomalyDetector(config.anomaly, metric_type="frequency")
            self._anomaly_egress = AnomalyDetector(config.anomaly, metric_type="egress")
        else:
            self._anomaly_freq = None
            self._anomaly_egress = None
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

    def _emit_violation(
        self,
        gate: str,
        tool_name: str | None,
        agent_role: str | None,
        caller_id: str | None = None,
        hop_depth: int = 0,
    ) -> None:
        """Emit OTel violation span if security OTel emitter is configured (OPS-04).

        caller_id and hop_depth are MAGNT-04 identity attributes passed from Gate 0.5.
        Only called on violation outcomes — allowed tool calls must NOT emit spans.
        """
        if not self._security_otel:
            return
        severity_map = {
            "prompt_shield": "CRITICAL",
            "permission": "HIGH",
            "egress": "HIGH",
            "redaction": "HIGH",
            "hitl": "HIGH",
            "identity": "HIGH",
            "anomaly": "HIGH",
        }
        severity = severity_map.get(gate, "INFO")
        self._security_otel.emit_security_violation(
            event_type=gate,
            tool_name=tool_name,
            severity=severity,
            agent_role=agent_role,
            caller_id=caller_id,
            hop_depth=hop_depth,
        )

    def pre_tool_call(
        self,
        agent_role: str,
        tool_name: str,
        tool_input: dict[str, Any],
        *,
        caller_id: str | None = None,
        hop_depth: int | None = None,
    ) -> dict[str, Any]:
        """
        Run before tool execution.
        Gate 0.5 — Identity: resolves caller_id from ContextVars, checks delegation depth.
        Gate 1   — Permission: raises PermissionDeniedError if role cannot call tool.
        Gate 1.5 — HITL: pauses for human approval if configured.
        Gate 2   — Audit: raises AuditUnavailableError if logger is unreachable (fail-closed).
        Returns tool_input unchanged.
        """
        # Gate 0.5: Identity resolution and delegation depth enforcement (MAGNT-01/03/04/05)
        ctx_caller_id, ctx_hop_depth = get_caller_context()
        effective_caller_id: str | None = caller_id if caller_id is not None else ctx_caller_id
        effective_hop_depth: int = hop_depth if hop_depth is not None else ctx_hop_depth

        # Resolve agent_role from AgentRegistry when caller_id is known
        if effective_caller_id is not None:
            agent_role = self._agent_registry.resolve_role(effective_caller_id, agent_role)

        # Fail-closed: reject calls that exceed max delegation depth
        max_depth = self._agent_registry.max_depth
        if effective_hop_depth > max_depth:
            self._emit_violation(
                "identity", tool_name, agent_role,
                caller_id=effective_caller_id, hop_depth=effective_hop_depth,
            )
            raise DelegationDepthError(
                gate="identity",
                blocked=tool_name,
                rule=f"hop_depth={effective_hop_depth} > max={max_depth}",
                caller_id=effective_caller_id,
                hop_depth=effective_hop_depth,
            )

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
            self._emit_violation(
                "permission", tool_name, agent_role,
                caller_id=effective_caller_id, hop_depth=effective_hop_depth,
            )
            raise

        # Gate 1.75 pre-compute: check frequency anomaly BEFORE HITL prompt so
        # anomaly context can be merged into the HITL banner (ANOM-01)
        freq_result = None
        anomaly_context = None
        if self._anomaly_freq is not None:
            freq_result = self._anomaly_freq.record_and_check(
                caller_id=effective_caller_id or agent_role,
                value=1.0,
                tool_name=tool_name,
            )
            if freq_result.level == ResponseLevel.BLOCK:
                # Fail-closed auto-deny — no HITL prompt
                self._audit.send({
                    "event_type": "anomaly_blocked",
                    "metric_type": "frequency",
                    "z_score": freq_result.z_score,
                    "baseline": freq_result.baseline,
                    "observed": freq_result.observed,
                    "tool_name": tool_name,
                    "caller_id": effective_caller_id,
                })
                self._emit_violation(
                    "anomaly", tool_name, agent_role,
                    caller_id=effective_caller_id, hop_depth=effective_hop_depth,
                )
                raise AnomalyBlockedError(
                    gate="anomaly",
                    blocked=tool_name,
                    rule=f"z={freq_result.z_score:.2f}>block_z={self._anomaly_freq._config.block_z}",
                )
            elif freq_result.level == ResponseLevel.ESCALATE:
                recent = self._anomaly_freq.get_recent_calls(effective_caller_id or agent_role)
                anomaly_context = {
                    "metric_type": "frequency",
                    "z_score": freq_result.z_score,
                    "baseline": freq_result.baseline,
                    "observed": freq_result.observed,
                    "recent_calls": recent,
                }

        # Gate 1.5: HITL approval gate — merges anomaly context when both fire
        needs_hitl = bool(self._hitl_config and self._hitl_config.needs_approval(tool_name))
        needs_anomaly_hitl = anomaly_context is not None

        if needs_hitl or needs_anomaly_hitl:
            hitl_cfg = self._hitl_config or HITLConfig()
            try:
                HITLGate(hitl_cfg).check(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    caller_id=effective_caller_id,
                    hop_depth=effective_hop_depth,
                    max_depth=max_depth,
                    anomaly_context=anomaly_context,
                )
                if needs_hitl:
                    # Approved — log the decision before continuing to Gate 2
                    self._audit.send(
                        {
                            "event_type": "hitl_decision",
                            "approved": True,
                            "tool_name": tool_name,
                            "tool_input": tool_input,
                        }
                    )
            except ApprovalDeniedError as exc:
                # Denied — log the decision before re-raising
                if needs_hitl:
                    self._audit.send(
                        {
                            "event_type": "hitl_decision",
                            "approved": False,
                            "timed_out": exc.timed_out,
                            "tool_name": tool_name,
                            "tool_input": tool_input,
                        }
                    )
                self._emit_violation(
                    "hitl", tool_name, agent_role,
                    caller_id=effective_caller_id, hop_depth=effective_hop_depth,
                )
                raise

        # After HITL, handle WARN level (log-only, no interruption)
        if freq_result is not None and freq_result.level == ResponseLevel.WARN:
            self._audit.send({
                "event_type": "anomaly_warn",
                "metric_type": "frequency",
                "z_score": freq_result.z_score,
                "baseline": freq_result.baseline,
                "observed": freq_result.observed,
                "tool_name": tool_name,
                "caller_id": effective_caller_id,
            })

        # Gate 2: Audit pre-call (hard stop — fail-closed)
        self._audit.send(
            {
                "event_type": "tool_call_pre",
                "agent_role": agent_role,
                "tool_name": tool_name,
                "caller_id": effective_caller_id,
                "hop_depth": effective_hop_depth,
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
            self._emit_violation("prompt_shield", "[post_tool_call]", None)
            raise

        # Gate 4: Secret/PII redaction (soft block — run continues with scrubbed data)
        clean_output = self._redactor.redact(tool_output)
        if clean_output != tool_output:
            self._emit_violation("redaction", None, None)

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
