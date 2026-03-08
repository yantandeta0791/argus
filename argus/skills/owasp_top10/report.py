"""OWASP report dataclasses — stub."""

from dataclasses import dataclass


@dataclass
class CategoryResult:
    category_id: str
    name: str
    passed: bool
    details: str


@dataclass
class OwaspReport:
    categories: list[CategoryResult]
    passed_count: int
    failed_count: int
    coverage_pct: float
    generated_at: str
