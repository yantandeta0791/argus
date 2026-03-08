"""
Skill lifecycle management for Argus.

SkillStage              -- 7-stage lifecycle enum
LIFECYCLE_SEQUENCE      -- ordered list of all stages
SkillLifecycleManager   -- drives skills through the complete lifecycle

Phase 5 (SKILL-02): Argus enforces the full skill lifecycle:
Install -> Verify -> Sandbox -> Execute -> Monitor -> Report -> Revoke

Design invariant: all stage transitions are deterministic code.
No LLM output drives a lifecycle transition (consistent with STM-02).

Cleanup guarantee: if any stage fails, REVOKE runs to clean up registry state.
No partial installs are left behind.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable

from argus.security.events import GateType, SecurityEvent
from argus.security.exceptions import SkillIntegrityError
from argus.security.sandbox.isolator import SkillIsolator
from argus.skills.hasher import verify_content_hash
from argus.skills.manifest import SkillManifest, load_manifest, validate_trust_tier
from argus.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class SkillStage(StrEnum):
    """Lifecycle stages for skill execution."""
    INSTALL = "install"
    VERIFY = "verify"
    SANDBOX = "sandbox"
    EXECUTE = "execute"
    MONITOR = "monitor"
    REPORT = "report"
    REVOKE = "revoke"


LIFECYCLE_SEQUENCE: list[SkillStage] = [
    SkillStage.INSTALL,
    SkillStage.VERIFY,
    SkillStage.SANDBOX,
    SkillStage.EXECUTE,
    SkillStage.MONITOR,
    SkillStage.REPORT,
    SkillStage.REVOKE,
]


class SkillLifecycleManager:
    """Drives skills through the 7-stage lifecycle.

    Each stage transition is deterministic — no LLM output drives transitions.
    SecurityEvents are emitted at each stage via the event_sink callback.

    Args:
        isolator: SkillIsolator for subprocess execution. Defaults to SkillIsolator().
        registry: SkillRegistry for tracking installed skills. Defaults to SkillRegistry().
        event_sink: Optional callback for SecurityEvent emission.
    """

    def __init__(
        self,
        isolator: SkillIsolator | None = None,
        registry: SkillRegistry | None = None,
        event_sink: Callable[[SecurityEvent], None] | None = None,
    ) -> None:
        self._isolator = isolator or SkillIsolator()
        self._registry = registry or SkillRegistry()
        self._event_sink = event_sink

    def verify_skill(self, skill_dir: Path) -> SkillManifest:
        """Run INSTALL + VERIFY stages only. Returns validated manifest.

        Use for static analysis where full lifecycle (subprocess execution) is not needed.
        The skill's content hash is verified against its manifest before any analysis runs.

        Args:
            skill_dir: Path to the skill package directory containing skill.yaml.

        Returns:
            Validated SkillManifest with integrity verified.

        Raises:
            SkillIntegrityError: If content hash does not match manifest.
            FileNotFoundError: If skill.yaml is missing.
            pydantic.ValidationError: If manifest is invalid.
        """
        manifest = self._do_install(skill_dir)
        self._do_verify(skill_dir, manifest)
        return manifest

    def run_lifecycle(self, skill_dir: Path) -> dict:
        """Run a skill through the complete 7-stage lifecycle.

        Args:
            skill_dir: Path to the skill package directory containing skill.yaml.

        Returns:
            Structured result dict with keys: skill_name, success, trust_tier,
            stages_completed, execution_result, metrics.

        Raises:
            SkillIntegrityError: If content hash does not match manifest.
            FileNotFoundError: If skill.yaml is missing.
            pydantic.ValidationError: If manifest is invalid.
            RuntimeError: If skill execution fails.
        """
        manifest: SkillManifest | None = None
        failed_stage: str | None = None

        try:
            # Stage 1: INSTALL
            manifest = self._do_install(skill_dir)

            # Stage 2: VERIFY
            self._do_verify(skill_dir, manifest)

            # Stage 3: SANDBOX
            self._do_sandbox(manifest)

            # Stage 4: EXECUTE
            exec_result = self._do_execute(skill_dir, manifest)

            # Stage 5: MONITOR
            monitor_data = self._do_monitor(manifest, exec_result)

            # Stage 6: REPORT
            report = self._do_report(manifest, monitor_data)

            # Stage 7: REVOKE (explicit, end of lifecycle)
            self._do_revoke(manifest.name, trigger="explicit")

            return report

        except Exception as exc:
            # Determine which stage failed
            failed_stage = getattr(exc, "_failed_stage", "unknown")
            # Cleanup: revoke on failure
            skill_name = manifest.name if manifest else "unknown"
            self._do_revoke(skill_name, trigger="failure", failed_stage=failed_stage)
            raise

    # ── Stage implementations ──────────────────────────────────────────

    def _do_install(self, skill_dir: Path) -> SkillManifest:
        """INSTALL: Load manifest, validate trust tier, register skill."""
        self._emit(SkillStage.INSTALL, "pending", "entered")

        manifest = load_manifest(skill_dir)
        validate_trust_tier(manifest, skill_dir)
        self._registry.install(manifest)

        self._emit(
            SkillStage.INSTALL, manifest.name, "completed",
            trust_tier=str(manifest.trust_tier),
        )
        return manifest

    def _do_verify(self, skill_dir: Path, manifest: SkillManifest) -> None:
        """VERIFY: Check SHA-256 content hash against manifest."""
        self._emit(SkillStage.VERIFY, manifest.name, "entered",
                   trust_tier=str(manifest.trust_tier))

        if not verify_content_hash(skill_dir, manifest.content_hash):
            exc = SkillIntegrityError(
                gate="skill_lifecycle",
                blocked=manifest.name,
                rule=f"hash mismatch: expected={manifest.content_hash}",
            )
            exc._failed_stage = SkillStage.VERIFY  # type: ignore[attr-defined]
            self._emit(SkillStage.VERIFY, manifest.name, "blocked",
                       trust_tier=str(manifest.trust_tier))
            raise exc

        self._emit(SkillStage.VERIFY, manifest.name, "completed",
                   trust_tier=str(manifest.trust_tier))

    def _do_sandbox(self, manifest: SkillManifest) -> None:
        """SANDBOX: Configure isolation based on trust tier.

        v1: Log sandbox configuration. Actual isolation is provided by
        SkillIsolator's subprocess env stripping. v1.1 adds Docker.
        """
        self._emit(SkillStage.SANDBOX, manifest.name, "entered",
                   trust_tier=str(manifest.trust_tier))

        logger.debug(
            "Sandbox configured for %s (tier=%s, blast_radius=%s)",
            manifest.name, manifest.trust_tier, manifest.blast_radius,
        )

        self._emit(SkillStage.SANDBOX, manifest.name, "completed",
                   trust_tier=str(manifest.trust_tier))

    def _do_execute(self, skill_dir: Path, manifest: SkillManifest) -> dict:
        """EXECUTE: Run skill via SkillIsolator."""
        self._emit(SkillStage.EXECUTE, manifest.name, "entered",
                   trust_tier=str(manifest.trust_tier))

        stdout = self._isolator.run(
            skill_cmd=["-m", manifest.name],
            skill_package_path=str(skill_dir),
            timeout_s=manifest.timeout_s,
        )

        exec_result = {"stdout": stdout, "exit_code": 0}

        self._emit(SkillStage.EXECUTE, manifest.name, "completed",
                   trust_tier=str(manifest.trust_tier))
        return exec_result

    def _do_monitor(self, manifest: SkillManifest, exec_result: dict) -> dict:
        """MONITOR: Passive metadata collection."""
        self._emit(SkillStage.MONITOR, manifest.name, "entered",
                   trust_tier=str(manifest.trust_tier))

        monitor_data = {
            "skill_name": manifest.name,
            "trust_tier": str(manifest.trust_tier),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "execution_result": exec_result,
        }

        self._emit(SkillStage.MONITOR, manifest.name, "completed",
                   trust_tier=str(manifest.trust_tier))
        return monitor_data

    def _do_report(self, manifest: SkillManifest, monitor_data: dict) -> dict:
        """REPORT: Produce structured execution result."""
        self._emit(SkillStage.REPORT, manifest.name, "entered",
                   trust_tier=str(manifest.trust_tier))

        report = {
            "skill_name": manifest.name,
            "success": True,
            "trust_tier": str(manifest.trust_tier),
            "stages_completed": [str(s) for s in LIFECYCLE_SEQUENCE],
            "metrics": monitor_data,
        }

        self._emit(SkillStage.REPORT, manifest.name, "completed",
                   trust_tier=str(manifest.trust_tier))
        return report

    def _do_revoke(
        self,
        skill_name: str,
        trigger: str = "explicit",
        failed_stage: str | None = None,
    ) -> None:
        """REVOKE: Remove skill from registry and emit cleanup event."""
        extra: dict[str, Any] = {"trigger": trigger}
        if failed_stage:
            extra["failed_stage"] = failed_stage

        self._emit(SkillStage.REVOKE, skill_name, "entered", **extra)
        self._registry.revoke(skill_name)
        self._emit(SkillStage.REVOKE, skill_name, "completed", **extra)

    # ── Event emission ─────────────────────────────────────────────────

    def _emit(
        self,
        stage: SkillStage,
        skill_name: str,
        outcome: str,
        trust_tier: str | None = None,
        **extra_metadata: Any,
    ) -> None:
        """Emit a SecurityEvent for a lifecycle stage transition."""
        if self._event_sink is None:
            return

        metadata: dict[str, Any] = {"stage": str(stage)}
        if trust_tier:
            metadata["trust_tier"] = trust_tier
        metadata.update(extra_metadata)

        event = SecurityEvent(
            gate=GateType.SKILL_LIFECYCLE,
            outcome=outcome,
            tool_name=skill_name,
            metadata=metadata,
        )
        self._event_sink(event)
