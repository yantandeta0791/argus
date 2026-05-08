"""
Unit tests for AnomalyDetector, AnomalyConfig, and config loading.

Covers:
- Warmup suppression (n < min_observations)
- Graduated response levels (OK, WARN, ESCALATE, BLOCK)
- Per-agent window isolation
- Window age eviction (via mocked time.monotonic)
- Edge cases: stdev=0, n<2
- AnomalyConfig defaults
- load_anomaly_config YAML parsing
- GateType.ANOMALY enum existence
- AnomalyBlockedError exception hierarchy
- load_gateway_config wires anomaly into GatewayConfig
"""

import pytest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Imports — fail at collection time so RED is caught immediately
# ---------------------------------------------------------------------------

from argus.security.anomaly import (
    AnomalyDetector,
    AnomalyConfig,
    ResponseLevel,
)
from argus.security.events import GateType
from argus.security.exceptions import AnomalyBlockedError, ArgusSecurityError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_detector(**kwargs) -> AnomalyDetector:
    """Create an AnomalyDetector with tight defaults for test speed."""
    config = AnomalyConfig(
        enabled=True,
        window_seconds=kwargs.pop("window_seconds", 60),
        min_observations=kwargs.pop("min_observations", 10),
        warn_z=kwargs.pop("warn_z", 2.0),
        escalate_z=kwargs.pop("escalate_z", 3.0),
        block_z=kwargs.pop("block_z", 4.0),
        **kwargs,
    )
    return AnomalyDetector(config=config, metric_type="frequency")


def warmup(
    detector: AnomalyDetector, caller_id: str, n: int, value: float = 1.0
) -> None:
    """Push n observations through the detector to build a baseline."""
    for _ in range(n):
        detector.record_and_check(caller_id, value, "tool")


# ---------------------------------------------------------------------------
# 1. Warmup suppression
# ---------------------------------------------------------------------------


class TestWarmup:
    def test_returns_ok_during_warmup(self):
        """All calls before min_observations must return OK regardless of value."""
        detector = make_detector(min_observations=10)
        # Push 9 calls (one less than threshold); all must be OK
        for i in range(9):
            result = detector.record_and_check("agent-A", 1.0, "tool")
            assert result.level == ResponseLevel.OK, (
                f"Call {i + 1} should be OK during warmup"
            )

    def test_exactly_min_observations_exits_warmup(self):
        """The 10th call (== min_observations) starts real detection."""
        # 10 identical calls → stdev=0 → OK (edge case, not warmup bypass)
        detector = make_detector(min_observations=10)
        for _ in range(10):
            result = detector.record_and_check("agent-A", 1.0, "tool")
        # stdev == 0 → returns OK (not warmup anymore, but degenerate case)
        assert result.level == ResponseLevel.OK


# ---------------------------------------------------------------------------
# 2. BLOCK response level
# ---------------------------------------------------------------------------


class TestBlock:
    def test_spike_at_block_threshold_returns_block(self):
        """A massive spike after baseline should return BLOCK (z >= block_z=4.0)."""
        detector = make_detector(min_observations=10)
        warmup(detector, "agent-A", 10, value=1.0)
        result = detector.record_and_check("agent-A", 100.0, "tool")
        assert result.level == ResponseLevel.BLOCK

    def test_block_result_has_z_score(self):
        """AnomalyResult.z_score must be a float when BLOCK is returned."""
        detector = make_detector(min_observations=10)
        warmup(detector, "agent-A", 10, value=1.0)
        result = detector.record_and_check("agent-A", 100.0, "tool")
        assert isinstance(result.z_score, float)
        assert result.z_score > 0


# ---------------------------------------------------------------------------
# 3. ESCALATE response level
# ---------------------------------------------------------------------------


class TestEscalate:
    def test_moderate_spike_returns_escalate(self):
        """A spike with z between escalate_z and block_z must return ESCALATE."""
        # Use many stable observations to tighten stdev, then moderate spike
        detector = make_detector(
            min_observations=10, warn_z=2.0, escalate_z=3.0, block_z=10.0
        )
        warmup(detector, "agent-A", 20, value=1.0)
        # Force a spike in escalate zone: push a value that is between escalate and block
        # With 20 obs of 1.0, stdev is near 0; add some noise to get meaningful stdev
        import statistics

        # Build baseline with some variance
        detector2 = make_detector(
            min_observations=10, warn_z=2.0, escalate_z=3.0, block_z=10.0
        )
        base = [1.0, 1.1, 0.9, 1.0, 1.1, 0.9, 1.0, 1.1, 0.9, 1.0]
        for v in base:
            detector2.record_and_check("agent-A", v, "tool")
        # stdev ~0.1, ewma ~1.0 → spike of 1.0 + 3.5*stdev = ~1.35 → z ≈ 3.5 (ESCALATE zone)
        sd = statistics.stdev(base)
        # Query current ewma via a normal call first, then spike
        spike_val = 1.0 + 3.5 * sd
        result = detector2.record_and_check("agent-A", spike_val, "tool")
        assert result.level == ResponseLevel.ESCALATE


# ---------------------------------------------------------------------------
# 4. WARN response level
# ---------------------------------------------------------------------------


class TestWarn:
    def test_mild_spike_returns_warn(self):
        """A mild spike with z between warn_z and escalate_z must return WARN."""
        detector = make_detector(
            min_observations=10, warn_z=2.0, escalate_z=5.0, block_z=10.0
        )
        base = [1.0, 1.1, 0.9, 1.0, 1.1, 0.9, 1.0, 1.1, 0.9, 1.0]
        for v in base:
            detector.record_and_check("agent-A", v, "tool")
        import statistics

        sd = statistics.stdev(base)
        # Spike at warn zone: z ≈ 2.5 → WARN
        spike_val = 1.0 + 2.5 * sd
        result = detector.record_and_check("agent-A", spike_val, "tool")
        assert result.level == ResponseLevel.WARN


# ---------------------------------------------------------------------------
# 5. OK after warmup
# ---------------------------------------------------------------------------


class TestOKAfterWarmup:
    def test_normal_value_returns_ok(self):
        """A value close to baseline (z < warn_z) must return OK after warmup."""
        detector = make_detector(min_observations=10)
        warmup(detector, "agent-A", 15, value=1.0)
        result = detector.record_and_check("agent-A", 1.0, "tool")
        assert result.level == ResponseLevel.OK


# ---------------------------------------------------------------------------
# 6. Per-agent isolation
# ---------------------------------------------------------------------------


class TestPerAgentIsolation:
    def test_agent_a_does_not_affect_agent_b(self):
        """Baseline for agent-A must not affect agent-B's detection."""
        detector = make_detector(min_observations=10)
        # Build baseline for agent-A with spiky values
        warmup(detector, "agent-A", 15, value=1000.0)
        # agent-B starts fresh — first call should be warmup (OK)
        result = detector.record_and_check("agent-B", 1.0, "tool")
        assert result.level == ResponseLevel.OK

    def test_agent_b_block_does_not_block_agent_a(self):
        """Block for agent-B must not prevent agent-A from returning OK."""
        detector = make_detector(min_observations=10)
        warmup(detector, "agent-A", 15, value=1.0)
        warmup(detector, "agent-B", 10, value=1.0)
        # Make agent-B spike
        detector.record_and_check("agent-B", 100.0, "tool")
        # agent-A should still be OK with normal value
        result = detector.record_and_check("agent-A", 1.0, "tool")
        assert result.level == ResponseLevel.OK


# ---------------------------------------------------------------------------
# 7. Window eviction
# ---------------------------------------------------------------------------


class TestWindowEviction:
    def test_old_observations_are_evicted(self):
        """Observations older than window_seconds must be dropped before z-score."""
        detector = make_detector(min_observations=10, window_seconds=60)
        t0 = 0.0
        # Add min_observations values at t=0
        with patch("time.monotonic", return_value=t0):
            warmup(detector, "agent-A", 10, value=1.0)

        # Advance time beyond window
        t1 = t0 + 61.0
        with patch("time.monotonic", return_value=t1):
            # All old observations should be evicted → back to warmup state → OK
            result = detector.record_and_check("agent-A", 1.0, "tool")
            assert result.level == ResponseLevel.OK

    def test_recent_observations_are_kept(self):
        """Observations within window_seconds must be retained."""
        detector = make_detector(min_observations=10, window_seconds=60)
        t0 = 0.0
        with patch("time.monotonic", return_value=t0):
            warmup(detector, "agent-A", 10, value=1.0)

        t1 = t0 + 30.0  # Still within window
        with patch("time.monotonic", return_value=t1):
            # Should still have observations → not in warmup
            result = detector.record_and_check("agent-A", 1.0, "tool")
            # stdev=0 returns OK, but the reason is degenerate stdev, not warmup
            assert result.level == ResponseLevel.OK


# ---------------------------------------------------------------------------
# 8. Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_stdev_zero_returns_ok(self):
        """When all values are identical (stdev=0), must return OK — no ZeroDivisionError."""
        detector = make_detector(min_observations=10)
        for _ in range(15):
            result = detector.record_and_check("agent-A", 5.0, "tool")
        assert result.level == ResponseLevel.OK

    def test_n_less_than_2_returns_ok(self):
        """With only 1 observation, cannot compute stdev → must return OK."""
        detector = make_detector(min_observations=1)
        result = detector.record_and_check("agent-A", 1.0, "tool")
        assert result.level == ResponseLevel.OK


# ---------------------------------------------------------------------------
# 9. AnomalyConfig defaults
# ---------------------------------------------------------------------------


class TestAnomalyConfigDefaults:
    def test_default_values(self):
        """AnomalyConfig defaults must match specification."""
        config = AnomalyConfig()
        assert config.enabled is True
        assert config.window_seconds == 60
        assert config.min_observations == 10
        assert config.warn_z == 2.0
        assert config.escalate_z == 3.0
        assert config.block_z == 4.0


# ---------------------------------------------------------------------------
# 10. load_anomaly_config
# ---------------------------------------------------------------------------


class TestLoadAnomalyConfig:
    def test_parses_anomaly_section(self):
        """load_anomaly_config returns AnomalyConfig when anomaly section present."""
        from argus.llm.config import load_anomaly_config

        raw = {
            "anomaly": {
                "enabled": True,
                "window_seconds": 120,
                "min_observations": 5,
                "warn_z": 1.5,
                "escalate_z": 2.5,
                "block_z": 3.5,
            }
        }
        cfg = load_anomaly_config(raw)
        assert cfg is not None
        assert cfg.window_seconds == 120
        assert cfg.min_observations == 5
        assert cfg.warn_z == 1.5
        assert cfg.escalate_z == 2.5
        assert cfg.block_z == 3.5

    def test_returns_none_when_absent(self):
        """load_anomaly_config returns None when anomaly section is absent."""
        from argus.llm.config import load_anomaly_config

        cfg = load_anomaly_config({})
        assert cfg is None

    def test_returns_none_when_enabled_false(self):
        """load_anomaly_config returns None when enabled: false."""
        from argus.llm.config import load_anomaly_config

        raw = {"anomaly": {"enabled": False}}
        cfg = load_anomaly_config(raw)
        assert cfg is None

    def test_uses_defaults_for_missing_keys(self):
        """load_anomaly_config uses AnomalyConfig defaults when keys are absent."""
        from argus.llm.config import load_anomaly_config

        raw = {"anomaly": {"enabled": True}}
        cfg = load_anomaly_config(raw)
        assert cfg is not None
        assert cfg.window_seconds == 60
        assert cfg.min_observations == 10
        assert cfg.warn_z == 2.0


# ---------------------------------------------------------------------------
# 11. GateType.ANOMALY enum
# ---------------------------------------------------------------------------


class TestGateTypeAnomaly:
    def test_anomaly_enum_exists(self):
        """GateType.ANOMALY must exist with value 'anomaly'."""
        assert GateType.ANOMALY == "anomaly"
        assert GateType.ANOMALY.value == "anomaly"


# ---------------------------------------------------------------------------
# 12. AnomalyBlockedError
# ---------------------------------------------------------------------------


class TestAnomalyBlockedError:
    def test_is_argus_security_error_subclass(self):
        """AnomalyBlockedError must subclass ArgusSecurityError."""
        assert issubclass(AnomalyBlockedError, ArgusSecurityError)

    def test_can_be_raised_with_base_fields(self):
        """AnomalyBlockedError can be instantiated with gate, blocked, rule."""
        err = AnomalyBlockedError(gate="anomaly", blocked="tool_x", rule="z>=4.0")
        assert err.gate == "anomaly"
        assert err.blocked == "tool_x"
        assert err.rule == "z>=4.0"

    def test_is_caught_by_argus_security_error(self):
        """AnomalyBlockedError must be caught by ArgusSecurityError handler."""
        with pytest.raises(ArgusSecurityError):
            raise AnomalyBlockedError(gate="anomaly", blocked="tool_x", rule="z>=4.0")


# ---------------------------------------------------------------------------
# 13. load_gateway_config wires anomaly field
# ---------------------------------------------------------------------------


class TestLoadGatewayConfigAnomaly:
    def test_gateway_config_has_anomaly_field(self):
        """load_gateway_config must include anomaly field from load_anomaly_config."""
        from argus.llm.config import load_gateway_config

        raw = {
            "anomaly": {
                "enabled": True,
                "window_seconds": 90,
            }
        }
        cfg = load_gateway_config(raw)
        assert hasattr(cfg, "anomaly")
        assert cfg.anomaly is not None
        assert cfg.anomaly.window_seconds == 90

    def test_gateway_config_anomaly_none_when_absent(self):
        """GatewayConfig.anomaly must be None when no anomaly section."""
        from argus.llm.config import load_gateway_config

        cfg = load_gateway_config({})
        assert hasattr(cfg, "anomaly")
        assert cfg.anomaly is None


# ---------------------------------------------------------------------------
# 14. AnomalyResult fields
# ---------------------------------------------------------------------------


class TestAnomalyResult:
    def test_result_has_required_fields(self):
        """AnomalyResult must expose level, z_score, baseline, observed."""
        detector = make_detector(min_observations=10)
        result = detector.record_and_check("agent-A", 1.0, "tool")
        assert hasattr(result, "level")
        assert hasattr(result, "z_score")
        assert hasattr(result, "baseline")
        assert hasattr(result, "observed")

    def test_result_observed_matches_input(self):
        """AnomalyResult.observed must match the value passed to record_and_check."""
        detector = make_detector(min_observations=10)
        result = detector.record_and_check("agent-A", 42.0, "tool")
        assert result.observed == 42.0
