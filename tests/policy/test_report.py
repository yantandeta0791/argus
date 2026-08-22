"""Tests for streaming policy-decision rollout summaries."""

from argus.policy.report import summarize_decisions


def _decision(policy_hash: str, outcome: str, gate: str = "permission") -> dict:
    return {
        "event_type": "policy_decision",
        "policy_hash": policy_hash,
        "outcome": outcome,
        "gate": gate,
        "tool_name": "export_data",
        "rule": "role=analyst tool=export_data",
    }


def test_summarize_decisions_aggregates_known_literal_events():
    summary = summarize_decisions(
        [
            _decision("hash-a", "allow"),
            _decision("hash-a", "would_block"),
            _decision("hash-a", "would_block"),
        ]
    )
    assert summary.total_decisions == 3
    assert summary.total_would_blocks == 2
    assert summary.policy_hashes == ("hash-a",)
    assert (
        summary.groups["hash-a"][
            ("permission", "export_data", "role=analyst tool=export_data")
        ]
        == 2
    )


def test_summarize_decisions_empty_input_is_zero_valued():
    summary = summarize_decisions([])
    assert summary.total_decisions == 0
    assert summary.total_would_blocks == 0
    assert summary.policy_hashes == ()
    assert summary.groups == {}


def test_summarize_decisions_groups_mixed_policy_hashes_without_merging():
    summary = summarize_decisions(
        [_decision("hash-a", "would_block"), _decision("hash-b", "would_block")]
    )
    assert summary.policy_hashes == ("hash-a", "hash-b")
    assert (
        summary.warning
        == "Multiple policy hashes observed; results are grouped by policy hash."
    )
    assert (
        summary.groups["hash-a"][
            ("permission", "export_data", "role=analyst tool=export_data")
        ]
        == 1
    )
    assert (
        summary.groups["hash-b"][
            ("permission", "export_data", "role=analyst tool=export_data")
        ]
        == 1
    )
