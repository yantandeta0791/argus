"""Tests for argus.llm.config -- load_config() and ModelConfig dataclasses."""

import pytest


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

    raw = {"rbac": {"roles": {"analyst": {"allow": ["read_db"]}}}}
    config = load_rbac_config(raw)
    assert config is not None
    assert any(
        r.role == "analyst" and r.tool == "read_db" and r.effect == "allow"
        for r in config.rules
    )


def test_load_rbac_config_deny_list_produces_deny_rules():
    from argus.llm.config import load_rbac_config

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


# --- POLC-02: Secrets config loader tests ---


def test_load_secrets_config_returns_empty_patterns_when_no_section():
    from argus.llm.config import load_secrets_config

    result = load_secrets_config({})
    assert result is not None
    assert result.patterns == []


def test_load_secrets_config_populates_patterns():
    from argus.llm.config import load_secrets_config

    raw = {"secrets": {"patterns": ["MY_SECRET_[A-Z]+"]}}
    result = load_secrets_config(raw)
    assert "MY_SECRET_[A-Z]+" in result.patterns


# --- POLC-03: Egress config loader tests ---


def test_load_egress_config_returns_empty_list_when_no_section():
    from argus.llm.config import load_egress_config

    result = load_egress_config({})
    assert result == []


def test_load_egress_config_populates_allowlist():
    from argus.llm.config import load_egress_config

    raw = {"egress": {"allowlist": ["api.example.com"]}}
    result = load_egress_config(raw)
    assert result == ["api.example.com"]


# --- POLC-04: Spend profiles tests ---


def test_load_spend_profiles_flat_keys_when_no_profile():
    from argus.llm.config import load_spend_profiles

    raw = {"spend": {"per_task_usd": 0.10}}
    result = load_spend_profiles(raw)
    assert result.per_task_usd == 0.10


def test_load_spend_profiles_selects_named_profile():
    from argus.llm.config import load_spend_profiles

    raw = {"spend": {"profiles": {"dev": {"per_task_usd": 0.10}}}}
    result = load_spend_profiles(raw, active_profile="dev")
    assert result.per_task_usd == 0.10


def test_load_spend_profiles_env_var_selection(monkeypatch):
    from argus.llm.config import load_spend_profiles

    monkeypatch.setenv("ARGUS_SPEND_PROFILE", "staging")
    raw = {"spend": {"profiles": {"staging": {"per_task_usd": 0.50}}}}
    result = load_spend_profiles(raw)
    assert result.per_task_usd == 0.50


def test_load_spend_profiles_unknown_profile_raises(monkeypatch):
    from argus.llm.config import load_spend_profiles
    from argus.security.exceptions import ConfigValidationError

    monkeypatch.setenv("ARGUS_SPEND_PROFILE", "nonexistent")
    raw = {"spend": {"profiles": {"dev": {"per_task_usd": 0.10}}}}
    with pytest.raises(ConfigValidationError, match="nonexistent"):
        load_spend_profiles(raw)


# --- POLC-05: Validation tests ---


def test_config_validation_error_on_invalid_regex():
    from argus.llm.config import load_secrets_config
    from argus.security.exceptions import ConfigValidationError

    raw = {"secrets": {"patterns": ["[invalid"]}}
    with pytest.raises(ConfigValidationError, match=r"\[invalid"):
        load_secrets_config(raw)


def test_config_validation_error_is_value_error():
    from argus.security.exceptions import ConfigValidationError

    assert issubclass(ConfigValidationError, ValueError)


# --- Integration: load_gateway_config tests ---


def test_load_gateway_config_returns_gateway_config():
    from argus.llm.config import load_gateway_config
    from argus.security.gateway import GatewayConfig

    raw = {
        "rbac": {"roles": {"analyst": {"allow": ["read_db"]}}},
        "secrets": {"patterns": ["MY_SECRET_[A-Z]+"]},
        "egress": {"allowlist": ["api.example.com"]},
        "hitl": {"timeout_seconds": 30},
        "tools": {"read_db": {"require_approval": True}},
    }
    result = load_gateway_config(raw)
    assert isinstance(result, GatewayConfig)
    assert result.permissions is not None
    assert result.prompt_shield_patterns == ["MY_SECRET_[A-Z]+"]
    assert result.egress_allowlist == ["api.example.com"]
    assert result.hitl is not None


def test_load_gateway_config_permissive_without_rbac():
    from argus.llm.config import load_gateway_config
    from argus.security.gateway import GatewayConfig

    raw = {"secrets": {"patterns": []}}
    result = load_gateway_config(raw)
    assert isinstance(result, GatewayConfig)
    assert result.permissions is None


def test_load_gateway_config_empty_raw():
    from argus.llm.config import load_gateway_config
    from argus.security.gateway import GatewayConfig

    result = load_gateway_config({})
    assert isinstance(result, GatewayConfig)
    assert result.permissions is None
    assert result.prompt_shield_patterns == []
    assert result.egress_allowlist == []
    assert result.hitl is None


# ---------------------------------------------------------------------------
# OPS-03: OTel config loader tests (load_otel_config)
# ---------------------------------------------------------------------------


def test_load_otel_config_returns_none_when_absent():
    """OPS-03: load_otel_config({}) returns None when otel section is absent."""
    from argus.llm.config import load_otel_config

    result = load_otel_config({})
    assert result is None


def test_load_otel_config_parses_endpoint_and_exporter():
    """OPS-03: load_otel_config parses exporter and endpoint from otel section."""
    from argus.llm.config import load_otel_config

    raw = {"otel": {"exporter": "otlp", "endpoint": "http://localhost:4317"}}
    result = load_otel_config(raw)
    assert result.exporter == "otlp"
    assert result.endpoint == "http://localhost:4317"


def test_load_otel_config_substitutes_env_vars(monkeypatch):
    """OPS-03: load_otel_config substitutes ${VAR} placeholders from environment."""
    from argus.llm.config import load_otel_config

    monkeypatch.setenv("DD_API_KEY", "test-key-123")
    raw = {
        "otel": {
            "exporter": "datadog",
            "endpoint": "http://dd:4317",
            "headers": {"api-key": "${DD_API_KEY}"},
        }
    }
    result = load_otel_config(raw)
    assert result.headers["api-key"] == "test-key-123"


def test_load_otel_config_defaults():
    """OPS-03: load_otel_config with empty otel section uses safe defaults."""
    from argus.llm.config import load_otel_config

    result = load_otel_config({"otel": {}})
    assert result.exporter == "otlp"
    assert result.endpoint == "http://localhost:4317"
    assert result.headers == {}


# ---------------------------------------------------------------------------
# OPS-03 + OPS-04: Config-to-gateway wiring test
# ---------------------------------------------------------------------------


def test_load_gateway_config_with_otel_builds_emitter():
    """OPS-03 + OPS-04: Full config-to-gateway wiring: YAML otel section ->
    load_gateway_config -> GatewayConfig.otel -> build_security_otel_emitter ->
    SecurityGateway(security_otel=emitter).

    This test is RED for three reasons:
    (a) GatewayConfig has no otel field yet
    (b) build_security_otel_emitter does not exist yet
    (c) SecurityGateway does not accept security_otel parameter yet
    """
    from unittest.mock import MagicMock
    from argus.llm.config import load_gateway_config
    from argus.observability.otel import build_security_otel_emitter
    from argus.security.gateway import SecurityGateway

    raw = {
        "otel": {"exporter": "otlp", "endpoint": "http://localhost:4317"},
        "rbac": {"roles": {"analyst": {"allow": ["read_file"]}}},
    }

    config = load_gateway_config(raw)
    assert config.otel is not None

    emitter = build_security_otel_emitter(config.otel)
    assert emitter is not None
    assert hasattr(emitter, "emit_security_violation")

    gateway = SecurityGateway(
        config=config,
        audit_logger=MagicMock(),
        security_otel=emitter,
    )
    assert gateway._security_otel is emitter


# ---------------------------------------------------------------------------
# MAGNT-01 / MAGNT-05: Agents config loader tests (load_agents_config)
# ---------------------------------------------------------------------------


def test_load_agents_config_returns_none_when_no_agents_section():
    def _load():
        from argus.llm.config import load_agents_config

        return load_agents_config({})

    result = _load()
    assert result is None


def test_load_agents_config_returns_none_when_empty_agents_section():
    def _load():
        from argus.llm.config import load_agents_config

        return load_agents_config({"agents": {}})

    result = _load()
    assert result is None


def test_load_agents_config_parses_registry_and_depth():
    def _load():
        from argus.llm.config import load_agents_config

        raw = {
            "agents": {
                "max_delegation_depth": 5,
                "registry": {
                    "supervisor": {"role": "admin"},
                    "worker": {"role": "reader"},
                },
            }
        }
        return load_agents_config(raw)

    result = _load()
    assert result is not None
    assert result.agents == {"supervisor": "admin", "worker": "reader"}
    assert result.max_delegation_depth == 5


def test_load_agents_config_missing_role_uses_agent_name():
    def _load():
        from argus.llm.config import load_agents_config

        raw = {
            "agents": {
                "registry": {
                    "worker": {},  # no role key
                },
            }
        }
        return load_agents_config(raw)

    result = _load()
    assert result is not None
    assert result.agents["worker"] == "worker"


def test_load_agents_config_default_max_depth_when_not_specified():
    def _load():
        from argus.llm.config import load_agents_config

        raw = {
            "agents": {
                "registry": {"supervisor": {"role": "admin"}},
            }
        }
        return load_agents_config(raw)

    result = _load()
    assert result is not None
    assert result.max_delegation_depth == 3


def test_gateway_config_has_agents_field():
    from argus.security.gateway import GatewayConfig

    config = GatewayConfig()
    assert config.agents is None


def test_gateway_config_has_max_delegation_depth_field():
    from argus.security.gateway import GatewayConfig

    config = GatewayConfig()
    assert config.max_delegation_depth == 3


def test_load_gateway_config_populates_agents():
    def _load():
        from argus.llm.config import load_gateway_config

        raw = {
            "agents": {
                "max_delegation_depth": 4,
                "registry": {"supervisor": {"role": "admin"}},
            }
        }
        return load_gateway_config(raw)

    result = _load()
    assert result.agents is not None
    assert result.agents.agents == {"supervisor": "admin"}
    assert result.max_delegation_depth == 4


def test_load_gateway_config_agents_none_when_absent():
    def _load():
        from argus.llm.config import load_gateway_config

        return load_gateway_config({})

    result = _load()
    assert result.agents is None
    assert result.max_delegation_depth == 3
