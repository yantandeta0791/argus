"""
Argus — Deterministic Security Enforcement for AI Agents.

Phase 1 exports: security foundation (all gates, exceptions, events).
Phase 2 will add: state machine, tool contracts.
"""
from argus.security.exceptions import (
    ArgusSecurityError,
    PermissionDeniedError,
    InjectionDetectedError,
    EgressViolationError,
    AuditUnavailableError,
)
from argus.security.events import SecurityEvent, GateType
from argus.security.gateway import SecurityGateway, GatewayConfig
from argus.security.audit.chain import verify_chain

__version__ = "0.1.0"

__all__ = [
    # Exceptions (Phase 2 catches these at state machine boundary)
    "ArgusSecurityError",
    "PermissionDeniedError",
    "InjectionDetectedError",
    "EgressViolationError",
    "AuditUnavailableError",
    # Events (Phase 7 consumes these)
    "SecurityEvent",
    "GateType",
    # Gateway (Phase 2 instantiates this)
    "SecurityGateway",
    "GatewayConfig",
    # Audit verification (Phase 8 CLI exposes this)
    "verify_chain",
    "__version__",
]
