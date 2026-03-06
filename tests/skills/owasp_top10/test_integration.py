"""Integration tests for OWASP Top 10 skill."""
import pytest


def test_clean_config_all_pass():
    from argus.skills.owasp_top10 import run

    # A well-formed agent config should pass all 10 OWASP categories
    agent_config = {
        "system_prompt": "You are a helpful assistant.",
        "permissions": ["read_files"],
        "data_access": [],
        "skills": [{"name": "builtin-skill", "trust_tier": "builtin"}],
        "tools": [
            {
                "name": "safe_tool",
                "idempotent": True,
                "confirmation_gate": True,
                "llm_output_verified": True,
                "validated": True,
            }
        ],
        "cost_cap": {"per_session_usd": 1.0},
        "audit_log_path": "/var/log/argus/audit.log",
        "blast_radius": "local",
        "human_in_loop": True,
        "redaction_enabled": True,
    }
    report = run(agent_config)
    assert report.passed_count == 10
    assert report.failed_count == 0
    assert report.coverage_pct == 100.0


def test_dirty_config_multiple_failures():
    from argus.skills.owasp_top10 import run

    # Config with 3+ violations: wildcard perms + no cost cap + no audit log
    agent_config = {
        "system_prompt": "You are a helpful assistant.",
        "permissions": ["*"],
        # no cost_cap
        # no audit_log_path
        "tools": [],
        "blast_radius": "local",
    }
    report = run(agent_config)
    assert report.failed_count >= 3
