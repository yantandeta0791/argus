"""Shared fixtures for tests/llm/."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from pathlib import Path

from argus.llm.config import ModelConfig, SpendConfig


@pytest.fixture
def mock_litellm_response():
    """Controlled LiteLLM response for cost-extraction tests.
    Do NOT use litellm's built-in mock_response -- it returns null usage fields."""
    resp = MagicMock()
    resp.usage.prompt_tokens = 10
    resp.usage.completion_tokens = 20
    resp._hidden_params = {"response_cost": 0.00015}
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = "stub response"
    return resp


@pytest.fixture
def sample_config():
    return ModelConfig(
        default="anthropic/claude-sonnet-4-6",
        states={
            "PLAN": "anthropic/claude-opus-4-6",
            "EXECUTE": "anthropic/claude-sonnet-4-6",
            "VERIFY": "anthropic/claude-sonnet-4-6",
            "REFLECT": "anthropic/claude-opus-4-6",
            "COMMIT": None,
        },
        tasks={"summarize": "anthropic/claude-haiku-3-5"},
        spend=SpendConfig(per_task_usd=0.10),
    )


@pytest.fixture
def tmp_argus_yaml(tmp_path: Path) -> Path:
    content = """\
models:
  default: "anthropic/claude-sonnet-4-6"
  states:
    PLAN: "anthropic/claude-opus-4-6"
    EXECUTE: "anthropic/claude-sonnet-4-6"
    VERIFY: "anthropic/claude-sonnet-4-6"
    REFLECT: "anthropic/claude-opus-4-6"
    COMMIT: null
  tasks:
    summarize: "anthropic/claude-haiku-3-5"
spend:
  per_task_usd: 0.10
  per_session_usd: null
  per_day_usd: null
"""
    yaml_file = tmp_path / "argus.yaml"
    yaml_file.write_text(content)
    return yaml_file
