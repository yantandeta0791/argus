import pytest


@pytest.mark.xfail(reason="SEC-06 not yet implemented", strict=False)
def test_violation_logged():
    from argus.security.egress.checker import EgressChecker
    from argus.security.events import SecurityEvent, GateType
    events = []
    checker = EgressChecker(
        allowlist=["api.example.com"],
        event_sink=events.append,
    )
    checker.check(hostname="evil.attacker.com", skill_name="test_skill")
    assert len(events) == 1
    assert events[0].gate == GateType.EGRESS
    assert events[0].outcome == "violation"


@pytest.mark.xfail(reason="SEC-06 not yet implemented", strict=False)
def test_log_only_no_network_block():
    from argus.security.egress.checker import EgressChecker
    from argus.security.exceptions import EgressViolationError
    events = []
    checker = EgressChecker(
        allowlist=["api.example.com"],
        event_sink=events.append,
    )
    # v1: check() logs but does NOT raise EgressViolationError (no network enforcement)
    try:
        checker.check(hostname="evil.attacker.com", skill_name="test_skill")
        violation_raised = False
    except EgressViolationError:
        violation_raised = True
    assert not violation_raised, "v1 egress is log-only, must not raise exception"
    assert len(events) == 1
