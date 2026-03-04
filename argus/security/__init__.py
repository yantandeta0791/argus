"""
Public API surface for argus.security.

Re-exports all 7 symbols that Phase 2 and downstream consumers use via
`from argus.security import ...`. Implementation details live in sub-modules;
only these 7 names are the public contract.
"""

from argus.security.exceptions import (
    ArgusSecurityError,
    AuditUnavailableError,
    EgressViolationError,
    InjectionDetectedError,
    PermissionDeniedError,
)
from argus.security.events import GateType, SecurityEvent

__all__ = [
    "ArgusSecurityError",
    "AuditUnavailableError",
    "EgressViolationError",
    "InjectionDetectedError",
    "PermissionDeniedError",
    "GateType",
    "SecurityEvent",
]
