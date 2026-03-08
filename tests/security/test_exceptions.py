# These will import from argus.security.exceptions
def test_permission_denied_is_argus_security_error():
    from argus.security.exceptions import PermissionDeniedError, ArgusSecurityError
    assert issubclass(PermissionDeniedError, ArgusSecurityError)


def test_injection_detected_is_argus_security_error():
    from argus.security.exceptions import InjectionDetectedError, ArgusSecurityError
    assert issubclass(InjectionDetectedError, ArgusSecurityError)


def test_egress_violation_is_argus_security_error():
    from argus.security.exceptions import EgressViolationError, ArgusSecurityError
    assert issubclass(EgressViolationError, ArgusSecurityError)


def test_audit_unavailable_is_argus_security_error():
    from argus.security.exceptions import AuditUnavailableError, ArgusSecurityError
    assert issubclass(AuditUnavailableError, ArgusSecurityError)


def test_argus_security_error_payload_fields():
    from argus.security.exceptions import PermissionDeniedError
    exc = PermissionDeniedError(gate="permission", blocked="write_file", rule="role=reader tool=write_file")
    assert exc.gate == "permission"
    assert exc.blocked == "write_file"
    assert exc.rule == "role=reader tool=write_file"
