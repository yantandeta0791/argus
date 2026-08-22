"""Tests for v0.6: egress enforcement, policy metadata, adversarial corpus."""

from __future__ import annotations

import pytest

from argus.security.adversarial import build_corpus, run_corpus
from argus.security.exceptions import EgressViolationError
from argus.security.gateway import GatewayConfig, SecurityGateway


class _CaptureAudit:
    def __init__(self):
        self.sent = []

    def send(self, payload):
        self.sent.append(payload)


class _SkillManifest:
    def __init__(self, name="web_scraper", egress_allowlist=None):
        self.name = name
        self.egress_allowlist = egress_allowlist or []


# ------------------------------------------------------------ egress modes


def _events_gateway(allowlist, enforce):
    config = GatewayConfig(egress_allowlist=allowlist, egress_enforce=enforce)
    gw = SecurityGateway(config=config, audit_logger=_CaptureAudit())
    return gw


def test_egress_log_only_mode_does_not_raise():
    gw = _events_gateway(["api.safe.com"], enforce=False)
    out = gw.post_tool_call(
        "ok", skill_manifest=_SkillManifest(egress_allowlist=["api.evil.com"])
    )
    assert out == "ok"  # v0.x behavior preserved


def test_egress_enforce_mode_raises_violation():
    gw = _events_gateway(["api.safe.com"], enforce=True)
    with pytest.raises(EgressViolationError):
        gw.post_tool_call(
            "ok", skill_manifest=_SkillManifest(egress_allowlist=["evil.com"])
        )
    # violation was also recorded in the security event stream
    assert any(e.gate.value == "egress" for e in gw.security_events)


def test_egress_enforce_allows_allowlisted_host():
    gw = _events_gateway(["api.safe.com"], enforce=True)
    out = gw.post_tool_call(
        "ok", skill_manifest=_SkillManifest(egress_allowlist=["api.safe.com"])
    )
    assert out == "ok"


def test_load_gateway_config_parses_egress_enforce_flag():
    from argus.llm.config import load_gateway_config

    cfg = load_gateway_config({"egress": {"allowlist": ["a.com"], "enforce": True}})
    assert cfg.egress_enforce is True
    assert cfg.egress_allowlist == ["a.com"]


def test_egress_enforce_defaults_false():
    from argus.llm.config import load_gateway_config

    assert load_gateway_config({}).egress_enforce is False


# ------------------------------------------------------------ policy metadata


def test_policy_metadata_stamped_into_audit_events():
    from argus.llm.config import load_gateway_config

    raw = {"policy": {"name": "prod-baseline", "version": "1.2.0"}}
    gw = SecurityGateway(config=load_gateway_config(raw), audit_logger=_CaptureAudit())
    gw.pre_tool_call("agent", "search", {})
    payload = gw._audit.sent[-1]
    assert payload["policy_name"] == "prod-baseline"
    assert payload["policy_version"] == "1.2.0"
    assert len(payload["policy_hash"]) == 64  # sha256 hex of full raw config


def test_policy_hash_changes_when_config_changes():
    from argus.llm.config import load_gateway_config

    h1 = load_gateway_config({"policy": {"name": "x"}}).policy_metadata["policy_hash"]
    h2 = load_gateway_config({"policy": {"name": "x"}, "spend": {}}).policy_metadata[
        "policy_hash"
    ]
    assert h1 != h2


def test_no_policy_section_means_no_stamp():
    from argus.llm.config import load_gateway_config

    gw = SecurityGateway(config=load_gateway_config({}), audit_logger=_CaptureAudit())
    gw.pre_tool_call("agent", "search", {})
    assert "policy_name" not in gw._audit.sent[-1]


# ------------------------------------------------------------ adversarial corpus


def test_corpus_builds_with_stable_ids():
    cases = build_corpus()
    ids = [c.id for c in cases]
    assert len(ids) == len(set(ids)), "duplicate corpus IDs"
    assert all(c.id.startswith(("INJ-", "SEC-")) for c in cases)


def test_full_corpus_detected_by_live_gates():
    """The published invariant: current gates catch every corpus case."""
    report = run_corpus()
    assert report["failed"] == 0, f"regressions: {report['failures']}"
    assert report["passed"] == report["total"]
    assert report["detection_rate_by_category"]["injection"] == 1.0
    assert report["detection_rate_by_category"]["secret"] == 1.0


def test_runner_reports_misses_not_crashes():
    """A broken detector surfaces as a failure entry, never an exception."""

    def blind_shield(text):
        pass  # detects nothing

    def broken_redactor(text):
        return text  # redacts nothing

    report = run_corpus(shield=blind_shield, redactor=broken_redactor)
    assert report["failed"] == report["total"]
