"""Daily spend enforcement tests -- COST-03 extension.

Phase 4 extends SpendTracker with daily_spend_usd parameter loaded
from SQLite at construction time.
"""


async def test_daily_spend_enforcement():
    """COST-03: per_day_usd=0.50, daily_spend_usd=0.49 -> not over budget; 0.50 -> over."""
    from argus.llm.config import SpendConfig
    from argus.llm.tracker import SpendTracker

    config = SpendConfig(per_day_usd=0.50)
    # Under budget
    t1 = SpendTracker(config, daily_spend_usd=0.49)
    assert t1.over_budget() is False
    # At budget (>= triggers)
    t2 = SpendTracker(config, daily_spend_usd=0.50)
    assert t2.over_budget() is True


async def test_over_budget_daily_combined():
    """COST-03: daily=0.40 + session record of 0.11 exceeds daily cap of 0.50."""
    from argus.llm.config import SpendConfig
    from argus.llm.tracker import SpendTracker, StateCostEntry

    config = SpendConfig(per_day_usd=0.50)
    tracker = SpendTracker(config, daily_spend_usd=0.40)
    tracker.record(
        StateCostEntry(
            state="PLAN",
            model="test",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.11,
        )
    )
    assert tracker.over_budget() is True  # 0.40 + 0.11 >= 0.50


async def test_daily_spend_zero_when_no_store():
    """COST-03: SpendTracker without daily_spend_usd defaults to 0.0."""
    from argus.llm.config import SpendConfig
    from argus.llm.tracker import SpendTracker

    config = SpendConfig(per_day_usd=0.50)
    tracker = SpendTracker(config)
    assert tracker.over_budget() is False  # daily=0.0 + session=0.0 < 0.50
