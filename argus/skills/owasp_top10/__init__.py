"""OWASP Agentic Top 10 skill — tests agent config against ASI01-ASI10."""
from __future__ import annotations
from datetime import datetime, timezone

from argus.skills.owasp_top10.categories import check_all
from argus.skills.owasp_top10.report import OwaspReport


def run(agent_config: dict) -> OwaspReport:
    """Test an agent config against all 10 OWASP Agentic Top 10 categories.

    Args:
        agent_config: Agent configuration dict. Sparse dicts are safe (all
            key accesses use .get() with safe defaults).

    Returns:
        OwaspReport with CategoryResult per ASI category and aggregate counts.
    """
    categories = check_all(agent_config)
    passed_count = sum(1 for c in categories if c.passed)
    failed_count = len(categories) - passed_count
    coverage_pct = round(passed_count / 10 * 100, 1)
    return OwaspReport(
        categories=categories,
        passed_count=passed_count,
        failed_count=failed_count,
        coverage_pct=coverage_pct,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
