"""
HITL (Human-in-the-Loop) gate for Argus.

HITLConfig -- per-tool approval requirements and global timeout setting.
HITLGate   -- interactive terminal gate that pauses execution for human review.

Design: fail-closed after one retry on invalid input. Timeout via select.select
when stdin is a real tty; threading.Timer fallback for CI/pipe environments.
Only stdlib used: select, threading, json, sys, dataclasses.
"""

from __future__ import annotations

import json
import select
import sys
import threading
from dataclasses import dataclass, field


@dataclass
class HITLConfig:
    """Configuration for the HITL approval gate.

    Attributes:
        require_approval: Mapping of tool names to True for tools requiring approval.
        timeout_seconds:  Seconds to wait for terminal input before auto-denying.
                          None means block indefinitely (no timeout).
    """

    require_approval: dict[str, bool] = field(default_factory=dict)
    timeout_seconds: int | None = None

    def needs_approval(self, tool_name: str) -> bool:
        """Return True if this tool requires human approval before execution."""
        return bool(self.require_approval.get(tool_name, False))


class HITLGate:
    """Interactive terminal gate that enforces HITL approval for flagged tools.

    Blocks execution by prompting the operator at the terminal. Supports:
    - Approve path: user types 'approve' → returns None
    - Deny path: user types 'deny' → raises ApprovalDeniedError(timed_out=False)
    - Timeout path: no input within timeout_seconds → raises ApprovalDeniedError(timed_out=True)
    - Retry path: one invalid input re-prompts; second invalid input auto-denies
    """

    def __init__(self, config: HITLConfig) -> None:
        self._config = config

    def check(
        self,
        tool_name: str,
        tool_input: dict,
        caller_id: str | None = None,
        hop_depth: int = 0,
        max_depth: int = 3,
        anomaly_context: dict | None = None,
    ) -> None:
        """Prompt for approval if this tool requires it.

        caller_id, hop_depth, and max_depth are optional MAGNT parameters for
        displaying sub-agent delegation context in the approval banner.

        anomaly_context: optional ANOM-01 dict from Gate 1.75/5.5. When provided,
        an [ARGUS ANOMALY] banner is printed before the tool input JSON. The gate
        fires even if tool is not in require_approval (anomaly-only escalation path).

        Returns None on approval.
        Raises ApprovalDeniedError on deny, timeout, or two invalid inputs.
        """
        from argus.security.exceptions import ApprovalDeniedError

        # Gate fires if tool requires approval OR if anomaly context forces escalation
        if not self._config.needs_approval(tool_name) and anomaly_context is None:
            return None

        # Print anomaly banner BEFORE the HITL tool banner and JSON input
        if anomaly_context is not None:
            metric_type = anomaly_context.get("metric_type", "frequency")
            z_score = anomaly_context.get("z_score", 0.0)
            baseline = anomaly_context.get("baseline", 0.0)
            observed = anomaly_context.get("observed", 0.0)
            recent_calls = anomaly_context.get("recent_calls", [])

            spike_label = (
                "Frequency spike"
                if metric_type == "frequency"
                else "Egress volume spike"
            )
            print(f"\n[ARGUS ANOMALY] {spike_label} detected")
            print(
                f"Rate: {observed} calls/window | Baseline: {baseline:.2f} | Z-score: {z_score:.2f}"
            )
            if recent_calls:
                import time as _time

                now = _time.monotonic()
                formatted = ", ".join(
                    f"{name} @ -{now - ts:.1f}s" for name, ts in recent_calls
                )
                print(f"Last {len(recent_calls)} calls: {formatted}")

        # Print the HITL banner so the operator can make an informed decision
        print(f"\n[ARGUS HITL] Approval required for tool '{tool_name}'")
        # Sub-agent delegation context — shown only when call is delegated (hop_depth > 0)
        if hop_depth > 0 and caller_id:
            print(f"Delegated by: {caller_id} (hop {hop_depth}/{max_depth})")
        print(json.dumps(tool_input, indent=2))
        print("Type 'approve' to allow or 'deny' to reject:")

        response = self._read_with_timeout()

        if response == "approve":
            return None
        if response == "deny":
            raise ApprovalDeniedError(
                gate="hitl",
                blocked=tool_name,
                rule="require_approval",
                timed_out=False,
            )
        if response is None:
            raise ApprovalDeniedError(
                gate="hitl",
                blocked=tool_name,
                rule="require_approval",
                timed_out=True,
            )

        # Invalid input — re-prompt once
        print("[ARGUS HITL] Invalid input. Type 'approve' or 'deny':")
        response2 = self._read_with_timeout()

        if response2 == "approve":
            return None
        if response2 == "deny":
            raise ApprovalDeniedError(
                gate="hitl",
                blocked=tool_name,
                rule="require_approval",
                timed_out=False,
            )
        if response2 is None:
            raise ApprovalDeniedError(
                gate="hitl",
                blocked=tool_name,
                rule="require_approval",
                timed_out=True,
            )

        # Second invalid input — auto-deny (fail-closed)
        raise ApprovalDeniedError(
            gate="hitl",
            blocked=tool_name,
            rule="require_approval",
            timed_out=False,
        )

    def _read_with_timeout(self) -> str | None:
        """Read a line from stdin, respecting the configured timeout.

        Returns the stripped input string, or None if the timeout expired.
        If timeout_seconds is None, blocks indefinitely via input().

        Primary path: select.select() for real tty environments.
        Fallback: threading.Timer for CI/pipe environments where select.select
        may raise ValueError (non-file-descriptor stdin).
        """
        if self._config.timeout_seconds is None:
            return input("").strip()

        try:
            ready, _, _ = select.select(
                [sys.stdin], [], [], self._config.timeout_seconds
            )
            if ready:
                return sys.stdin.readline().strip()
            return None  # timeout
        except (ValueError, OSError):
            # Fallback for CI/pipe environments: use threading.Timer
            result: list[str | None] = [None]
            timed_out = threading.Event()

            def _timeout_handler() -> None:
                timed_out.set()

            timer = threading.Timer(self._config.timeout_seconds, _timeout_handler)
            timer.start()
            try:
                line = input("").strip()
                if not timed_out.is_set():
                    result[0] = line
            except EOFError:
                pass
            finally:
                timer.cancel()

            return result[0]
