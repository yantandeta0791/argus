"""
Security exception hierarchy for Argus.

Catchable ONLY at the Phase 2 state machine layer.
Do not add retry logic, suppression mechanisms, or any way for caller code
to handle exceptions at a lower level.
"""


class ArgusSecurityError(Exception):
    """Base class for all Argus security violations.

    Attributes:
        gate: Which gate fired (e.g. "permission", "prompt_shield")
        blocked: What was blocked (tool name, matched pattern, hostname)
        rule: Which rule/pattern triggered the block
    """

    def __init__(self, gate: str, blocked: str, rule: str) -> None:
        self.gate = gate
        self.blocked = blocked
        self.rule = rule
        super().__init__(f"[{gate}] blocked={blocked!r} rule={rule!r}")


class PermissionDeniedError(ArgusSecurityError):
    """Raised when a tool call is denied by the permission gate."""

    pass


class InjectionDetectedError(ArgusSecurityError):
    """Raised when prompt injection is detected by the prompt shield gate."""

    pass


class EgressViolationError(ArgusSecurityError):
    """Raised when an egress violation is detected by the egress gate."""

    pass


class SkillIntegrityError(ArgusSecurityError):
    """Raised when a skill's content hash does not match its manifest.

    Distinguishes integrity failures from permission/injection errors.
    """

    pass


class AuditUnavailableError(ArgusSecurityError):
    """Raised when the audit logger is unavailable.

    Uses a simplified constructor that accepts only a message string.
    Sets gate="audit", blocked="", rule="" internally so that
    catch-all `except ArgusSecurityError` still works.
    """

    def __init__(self, message: str) -> None:
        # Bypass ArgusSecurityError.__init__ — use Exception directly
        Exception.__init__(self, message)
        self.gate = "audit"
        self.blocked = ""
        self.rule = ""
