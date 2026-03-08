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
