"""
RED test suite for HITLGate unit behaviors and load_hitl_config() parsing.

These tests import from modules that do NOT exist yet:
  - argus.security.hitl (HITLGate, HITLConfig)
  - argus.security.exceptions (ApprovalDeniedError)
  - argus.llm.config (load_hitl_config)

pytest will FAIL at collection time with ImportError until plan 02 implements
these modules. This confirms the RED state required by the TDD workflow.

Requirements covered: HITL-01, HITL-02, HITL-03, HITL-04, HITL-05
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from argus.security.hitl import HITLGate, HITLConfig
from argus.security.exceptions import ApprovalDeniedError
from argus.llm.config import load_hitl_config


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_config(**kwargs) -> HITLConfig:
    """Construct an HITLConfig with sensible defaults for unit tests."""
    defaults = {
        "require_approval": {"delete_file": True},
        "timeout_seconds": 30,
    }
    defaults.update(kwargs)
    return HITLConfig(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHITLGateApprove:
    def test_approve_returns_none(self):
        """HITL-01: HITLGate.check() returns None when human types 'approve'.

        Covers the happy path: an interactive user explicitly approves the
        pending tool call. The gate must return None (not raise).
        """
        config = _make_config()
        gate = HITLGate(config=config)

        with patch("builtins.input", return_value="approve"):
            result = gate.check(tool_name="delete_file", tool_input={"path": "/tmp/x"})

        assert result is None


class TestHITLGateDeny:
    def test_deny_raises_approval_denied_error(self):
        """HITL-02: HITLGate.check() raises ApprovalDeniedError when human types 'deny'.

        Covers the explicit-deny path: a human operator rejects the call.
        The error must be raised so the caller can handle it or propagate it.
        """
        config = _make_config()
        gate = HITLGate(config=config)

        with patch("builtins.input", return_value="deny"):
            with pytest.raises(ApprovalDeniedError):
                gate.check(tool_name="delete_file", tool_input={"path": "/tmp/x"})

    def test_deny_timed_out_is_false(self):
        """HITL-02/HITL-04: ApprovalDeniedError.timed_out is False on human-deny path.

        Distinguishes explicit human denial from a timeout-triggered denial.
        """
        config = _make_config()
        gate = HITLGate(config=config)

        with patch("builtins.input", return_value="deny"):
            with pytest.raises(ApprovalDeniedError) as exc_info:
                gate.check(tool_name="delete_file", tool_input={"path": "/tmp/x"})

        assert exc_info.value.timed_out is False


class TestHITLGateRetry:
    def test_invalid_input_twice_raises_approval_denied_error(self):
        """HITL-03: HITLGate.check() auto-denies after two invalid inputs.

        On the first invalid response the gate re-prompts. On the second
        invalid response it auto-denies by raising ApprovalDeniedError.
        The side_effect list simulates both inputs without touching stdin.
        """
        config = _make_config()
        gate = HITLGate(config=config)

        with patch("builtins.input", side_effect=["oops", "also_wrong"]):
            with pytest.raises(ApprovalDeniedError):
                gate.check(tool_name="delete_file", tool_input={"path": "/tmp/x"})


class TestHITLGateTimeout:
    def test_timeout_raises_approval_denied_error_with_timed_out_true(self):
        """HITL-04: HITLGate.check() raises ApprovalDeniedError(timed_out=True) on timeout.

        When _read_with_timeout returns None (the timeout sentinel) the gate
        must treat the call as denied and set timed_out=True on the error.
        """
        config = _make_config()
        gate = HITLGate(config=config)

        with patch.object(gate, "_read_with_timeout", return_value=None):
            with pytest.raises(ApprovalDeniedError) as exc_info:
                gate.check(tool_name="delete_file", tool_input={"path": "/tmp/x"})

        assert exc_info.value.timed_out is True


class TestHITLGateSkip:
    def test_skips_tool_not_in_require_approval(self):
        """HITL-05: HITLGate.check() returns None immediately for unlisted tools.

        Tools not in require_approval bypass the HITL prompt entirely. This
        ensures low-risk tools (e.g., read_file) are not gated.
        """
        config = _make_config(
            require_approval={"delete_file": True},
            timeout_seconds=None,
        )
        gate = HITLGate(config=config)

        # Should return immediately — no input() call should happen
        with patch("builtins.input", side_effect=RuntimeError("should not prompt")):
            result = gate.check(tool_name="read_file", tool_input={"path": "/tmp/x"})

        assert result is None


class TestApprovalDeniedErrorTimedOut:
    def test_timed_out_true_only_on_timeout_path(self):
        """HITL-04: timed_out distinguishes timeout denial from human denial.

        Verify that the timed_out attribute is True for timeout, False for
        an explicit human 'deny'. Both paths raise ApprovalDeniedError.
        """
        config = _make_config()
        gate = HITLGate(config=config)

        # Human-deny path
        with patch("builtins.input", return_value="deny"):
            with pytest.raises(ApprovalDeniedError) as human_exc:
                gate.check(tool_name="delete_file", tool_input={})
        assert human_exc.value.timed_out is False

        # Timeout path
        with patch.object(gate, "_read_with_timeout", return_value=None):
            with pytest.raises(ApprovalDeniedError) as timeout_exc:
                gate.check(tool_name="delete_file", tool_input={})
        assert timeout_exc.value.timed_out is True


class TestHITLGateBanner:
    def test_banner_printed_before_prompt(self, capsys):
        """HITL-01: HITLGate.check() prints [ARGUS HITL] banner to stdout before prompting.

        The banner must include the tool name and pretty-printed JSON arguments
        so the human operator can make an informed decision. Verified via
        capsys to avoid any real stdin interaction.
        """
        config = _make_config()
        gate = HITLGate(config=config)

        # Approve so check() returns normally after printing the banner
        with patch("builtins.input", return_value="approve"):
            gate.check(tool_name="delete_file", tool_input={"path": "/tmp/sensitive"})

        captured = capsys.readouterr()
        assert "[ARGUS HITL]" in captured.out
        assert "delete_file" in captured.out


# ---------------------------------------------------------------------------
# load_hitl_config tests
# ---------------------------------------------------------------------------


def test_load_hitl_config_parses_tools():
    """HITL-01: load_hitl_config parses tools section and filters by require_approval.

    The function receives the result of yaml.safe_load on argus.yaml.
    Only tools with require_approval: true appear in the returned HITLConfig.
    Tools with require_approval: false (or absent) are omitted.
    """
    raw = {
        "tools": {
            "delete_file": {"require_approval": True},
            "write_file": {"require_approval": True},
            "read_file": {"require_approval": False},
            "list_dir": {},  # omit — no require_approval key
        }
    }

    config = load_hitl_config(raw)

    assert config is not None
    assert config.require_approval == {
        "delete_file": True,
        "write_file": True,
    }
    # read_file has require_approval: False → excluded
    assert "read_file" not in config.require_approval
    # list_dir has no key → excluded
    assert "list_dir" not in config.require_approval


# ---------------------------------------------------------------------------
# Phase 9 Plan 02: Sub-agent delegation banner tests
# ---------------------------------------------------------------------------


class TestHITLSubAgentBanner:
    def test_sub_agent_banner_shown_when_hop_depth_greater_than_zero(self, capsys):
        """MAGNT: when hop_depth > 0 and caller_id is set, HITL banner includes
        'Delegated by: {name} (hop {depth}/{max})' line."""
        config = _make_config()
        gate = HITLGate(config=config)

        with patch("builtins.input", return_value="approve"):
            gate.check(
                tool_name="delete_file",
                tool_input={"path": "/tmp/x"},
                caller_id="supervisor",
                hop_depth=2,
                max_depth=3,
            )

        captured = capsys.readouterr()
        assert "Delegated by: supervisor (hop 2/3)" in captured.out

    def test_no_delegation_line_when_hop_depth_is_zero(self, capsys):
        """MAGNT: when hop_depth == 0, HITL banner does NOT include delegation line."""
        config = _make_config()
        gate = HITLGate(config=config)

        with patch("builtins.input", return_value="approve"):
            gate.check(
                tool_name="delete_file",
                tool_input={"path": "/tmp/x"},
                hop_depth=0,
            )

        captured = capsys.readouterr()
        assert "Delegated by" not in captured.out

    def test_backward_compat_no_new_params(self, capsys):
        """MAGNT: HITLGate.check() works unchanged without caller_id/hop_depth/max_depth."""
        config = _make_config()
        gate = HITLGate(config=config)

        with patch("builtins.input", return_value="approve"):
            gate.check(tool_name="delete_file", tool_input={"path": "/tmp/x"})

        captured = capsys.readouterr()
        assert "[ARGUS HITL]" in captured.out
        assert "Delegated by" not in captured.out


def test_load_hitl_config_parses_timeout():
    """HITL-01: load_hitl_config parses hitl.timeout_seconds; empty dict returns None.

    Passing a hitl section with timeout_seconds must produce an HITLConfig
    with that timeout. An empty dict (no relevant config) must return None.
    """
    raw_with_timeout = {"hitl": {"timeout_seconds": 60}}
    config = load_hitl_config(raw_with_timeout)

    assert config is not None
    assert config.timeout_seconds == 60

    # No tools or hitl sections → return None (no HITL config needed)
    assert load_hitl_config({}) is None


# ---------------------------------------------------------------------------
# Phase 10 Plan 02: HITLGate anomaly_context parameter tests
# ---------------------------------------------------------------------------


class TestHITLGateAnomalyContext:
    """Tests for anomaly_context parameter in HITLGate.check()."""

    def _make_anomaly_context(self, metric_type="frequency"):
        return {
            "metric_type": metric_type,
            "z_score": 3.5,
            "baseline": 2.0,
            "observed": 8.0,
            "recent_calls": [("search", 100.0), ("read_file", 95.0)],
        }

    def test_anomaly_context_banner_printed(self, capsys):
        """ANOM: when anomaly_context is provided, check() prints [ARGUS ANOMALY] banner
        with rate, baseline, z-score before the tool input JSON."""
        config = HITLConfig(
            require_approval={"delete_file": True}, timeout_seconds=None
        )
        gate = HITLGate(config=config)

        with patch("builtins.input", return_value="approve"):
            gate.check(
                tool_name="delete_file",
                tool_input={"path": "/tmp/x"},
                anomaly_context=self._make_anomaly_context(),
            )

        captured = capsys.readouterr()
        assert "[ARGUS ANOMALY]" in captured.out
        assert "3.5" in captured.out  # z_score
        assert "2.0" in captured.out  # baseline
        assert "8.0" in captured.out  # observed rate

    def test_anomaly_context_shows_recent_calls(self, capsys):
        """ANOM: anomaly banner includes last 5 calls (tool_name @ relative_time)."""
        config = HITLConfig(require_approval={"search": True}, timeout_seconds=None)
        gate = HITLGate(config=config)

        with patch("builtins.input", return_value="approve"):
            gate.check(
                tool_name="search",
                tool_input={"q": "test"},
                anomaly_context=self._make_anomaly_context(),
            )

        captured = capsys.readouterr()
        assert "search" in captured.out
        assert "read_file" in captured.out

    def test_anomaly_context_banner_before_tool_input(self, capsys):
        """ANOM: anomaly banner appears BEFORE tool input JSON in output."""
        config = HITLConfig(require_approval={"search": True}, timeout_seconds=None)
        gate = HITLGate(config=config)

        with patch("builtins.input", return_value="approve"):
            gate.check(
                tool_name="search",
                tool_input={"q": "my_query"},
                anomaly_context=self._make_anomaly_context(),
            )

        captured = capsys.readouterr()
        anomaly_pos = captured.out.find("[ARGUS ANOMALY]")
        input_pos = captured.out.find("my_query")
        assert anomaly_pos < input_pos, (
            "Anomaly banner must appear before tool input JSON"
        )

    def test_anomaly_context_fires_without_require_approval(self, capsys):
        """ANOM: when anomaly_context is provided but tool not in require_approval,
        HITL prompt still fires (anomaly-only escalation path)."""
        # Tool is NOT in require_approval
        config = HITLConfig(require_approval={}, timeout_seconds=None)
        gate = HITLGate(config=config)

        with patch("builtins.input", return_value="approve"):
            # Should not raise and should prompt (anomaly context forces prompt)
            result = gate.check(
                tool_name="search",
                tool_input={"q": "test"},
                anomaly_context=self._make_anomaly_context(),
            )

        assert result is None
        captured = capsys.readouterr()
        assert "[ARGUS ANOMALY]" in captured.out

    def test_anomaly_context_with_delegation_shows_delegation_line(self, capsys):
        """ANOM + MAGNT: when anomaly_context AND hop_depth > 0, banner includes delegation context."""
        config = HITLConfig(require_approval={"search": True}, timeout_seconds=None)
        gate = HITLGate(config=config)

        with patch("builtins.input", return_value="approve"):
            gate.check(
                tool_name="search",
                tool_input={"q": "test"},
                caller_id="supervisor",
                hop_depth=2,
                max_depth=3,
                anomaly_context=self._make_anomaly_context(),
            )

        captured = capsys.readouterr()
        assert "[ARGUS ANOMALY]" in captured.out
        assert "Delegated by: supervisor (hop 2/3)" in captured.out

    def test_no_anomaly_context_no_anomaly_banner(self, capsys):
        """ANOM: when anomaly_context is None (not provided), no [ARGUS ANOMALY] banner printed."""
        config = HITLConfig(
            require_approval={"delete_file": True}, timeout_seconds=None
        )
        gate = HITLGate(config=config)

        with patch("builtins.input", return_value="approve"):
            gate.check(tool_name="delete_file", tool_input={"path": "/tmp/x"})

        captured = capsys.readouterr()
        assert "[ARGUS ANOMALY]" not in captured.out

    def test_anomaly_context_deny_raises_approval_denied(self):
        """ANOM: when anomaly HITL prompt is denied, ApprovalDeniedError is raised."""
        config = HITLConfig(require_approval={}, timeout_seconds=None)
        gate = HITLGate(config=config)

        with patch("builtins.input", return_value="deny"):
            with pytest.raises(ApprovalDeniedError):
                gate.check(
                    tool_name="search",
                    tool_input={},
                    anomaly_context=self._make_anomaly_context(),
                )
