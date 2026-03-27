"""Tests for argus.llm.config -- load_config() and ModelConfig dataclasses."""


def test_load_config_reads_yaml(tmp_argus_yaml):
    from argus.llm.config import load_config

    config = load_config(tmp_argus_yaml)
    assert config.default == "anthropic/claude-sonnet-4-6"


def test_load_config_per_state_mapping(tmp_argus_yaml):
    from argus.llm.config import load_config

    config = load_config(tmp_argus_yaml)
    assert config.states["PLAN"] == "anthropic/claude-opus-4-6"
    assert config.states["COMMIT"] is None


def test_load_config_per_task_override(tmp_argus_yaml):
    from argus.llm.config import load_config

    config = load_config(tmp_argus_yaml)
    assert config.tasks["summarize"] == "anthropic/claude-haiku-3-5"


def test_load_config_spend_caps(tmp_argus_yaml):
    from argus.llm.config import load_config

    config = load_config(tmp_argus_yaml)
    assert config.spend.per_task_usd == 0.10
    assert config.spend.per_session_usd is None


def test_load_config_defaults_without_optional_keys(tmp_path):
    from argus.llm.config import load_config

    yaml_file = tmp_path / "argus.yaml"
    yaml_file.write_text("models:\n  default: anthropic/claude-sonnet-4-6\n")
    config = load_config(yaml_file)
    assert config.states == {}
    assert config.tasks == {}


# --- POLC-01: RBAC config loader tests ---


def test_load_rbac_config_returns_none_when_no_rbac_section():
    from argus.llm.config import load_rbac_config

    result = load_rbac_config({})
    assert result is None


def test_load_rbac_config_allow_list_produces_policy_rules():
    from argus.llm.config import load_rbac_config
    from argus.security.permission.policy import PolicyRule

    raw = {"rbac": {"roles": {"analyst": {"allow": ["read_db"]}}}}
    config = load_rbac_config(raw)
    assert config is not None
    assert any(
        r.role == "analyst" and r.tool == "read_db" and r.effect == "allow"
        for r in config.rules
    )


def test_load_rbac_config_deny_list_produces_deny_rules():
    from argus.llm.config import load_rbac_config
    from argus.security.permission.policy import PolicyRule

    raw = {"rbac": {"roles": {"analyst": {"deny": ["delete_records"]}}}}
    config = load_rbac_config(raw)
    assert config is not None
    assert any(
        r.role == "analyst" and r.tool == "delete_records" and r.effect == "deny"
        for r in config.rules
    )


def test_load_rbac_config_wildcard_allow():
    from argus.llm.config import load_rbac_config

    raw = {"rbac": {"roles": {"admin": {"allow": ["*"]}}}}
    config = load_rbac_config(raw)
    assert config is not None
    assert any(
        r.role == "admin" and r.tool == "*" and r.effect == "allow"
        for r in config.rules
    )


def test_load_rbac_config_multiple_roles():
    from argus.llm.config import load_rbac_config

    raw = {
        "rbac": {
            "roles": {
                "analyst": {"allow": ["read_db", "search_web"]},
                "editor": {"allow": ["write_file"]},
            }
        }
    }
    config = load_rbac_config(raw)
    assert config is not None
    roles_in_rules = {r.role for r in config.rules}
    assert "analyst" in roles_in_rules
    assert "editor" in roles_in_rules
    tools_for_analyst = {r.tool for r in config.rules if r.role == "analyst"}
    assert "read_db" in tools_for_analyst
    assert "search_web" in tools_for_analyst
