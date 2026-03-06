"""Tests for SpendTracker -- COST-03, COST-04."""
import pytest
from argus.llm.tracker import StateCostEntry


@pytest.mark.xfail(raises=NotImplementedError, strict=True, reason="Plan 03-02")
def test_over_budget_returns_false_when_under_cap():
    """COST-03: over_budget() is False when spend is below cap."""
    from argus.llm.tracker import SpendTracker
    from argus.llm.config import SpendConfig
    tracker = SpendTracker(SpendConfig(per_task_usd=1.0))
    entry = StateCostEntry("PLAN", "anthropic/claude-opus-4-6", 10, 20, 0.001)
    tracker.record(entry)
    assert tracker.over_budget() is False


@pytest.mark.xfail(raises=NotImplementedError, strict=True, reason="Plan 03-02")
def test_over_budget_returns_true_when_cap_exceeded():
    """COST-03: over_budget() returns True when per_task_usd is exceeded."""
    from argus.llm.tracker import SpendTracker
    from argus.llm.config import SpendConfig
    tracker = SpendTracker(SpendConfig(per_task_usd=0.001))
    entry = StateCostEntry("PLAN", "anthropic/claude-opus-4-6", 100, 200, 0.01)
    tracker.record(entry)
    assert tracker.over_budget() is True


@pytest.mark.xfail(raises=NotImplementedError, strict=True, reason="Plan 03-02")
def test_no_cap_never_over_budget():
    """COST-03: over_budget() always False when no cap configured."""
    from argus.llm.tracker import SpendTracker
    from argus.llm.config import SpendConfig
    tracker = SpendTracker(SpendConfig())  # all None
    for _ in range(10):
        tracker.record(StateCostEntry("PLAN", "anthropic/claude-opus-4-6", 1000, 2000, 10.0))
    assert tracker.over_budget() is False


@pytest.mark.xfail(raises=NotImplementedError, strict=True, reason="Plan 03-02")
def test_cost_breakdown_entries_populated():
    """COST-04: entries() returns all recorded StateCostEntry records."""
    from argus.llm.tracker import SpendTracker
    from argus.llm.config import SpendConfig
    tracker = SpendTracker(SpendConfig())
    e1 = StateCostEntry("PLAN", "anthropic/claude-opus-4-6", 10, 20, 0.0015)
    e2 = StateCostEntry("EXECUTE", "anthropic/claude-sonnet-4-6", 5, 15, 0.0005)
    tracker.record(e1)
    tracker.record(e2)
    entries = tracker.entries()
    assert len(entries) == 2
    assert entries[0].state == "PLAN"
    assert entries[1].cost_usd == 0.0005


@pytest.mark.xfail(raises=NotImplementedError, strict=True, reason="Plan 03-02")
def test_session_spend_cap():
    """COST-03: over_budget() respects per_session_usd cap."""
    from argus.llm.tracker import SpendTracker
    from argus.llm.config import SpendConfig
    tracker = SpendTracker(SpendConfig(per_session_usd=0.005))
    for state in ["PLAN", "EXECUTE", "VERIFY"]:
        tracker.record(StateCostEntry(state, "anthropic/claude-sonnet-4-6", 10, 20, 0.002))
    # 3 * 0.002 = 0.006 > 0.005
    assert tracker.over_budget() is True
