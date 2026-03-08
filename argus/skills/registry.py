"""
In-memory skill registry for Argus.

SkillRegistry -- tracks installed skills with install/get/list/revoke operations.

v1: In-memory dict. All state is lost when the process exits.
Upgrade path: persist_to(store: SessionStore) for cross-session skill state
if Phase 6 requires it.

Design:
  - install() overwrites if skill already exists (duplicate = update)
  - get() returns a copy to prevent external mutation (list-copy pattern)
  - revoke() is idempotent -- does not raise on missing skill
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class SkillRegistry:
    """Tracks installed skills in-memory.

    Maps skill name to metadata dict containing manifest fields,
    install timestamp, and current lifecycle stage.
    """

    def __init__(self) -> None:
        self._skills: dict[str, dict[str, Any]] = {}

    def install(self, manifest: Any) -> None:
        """Register a skill from its validated manifest.

        Overwrites if skill already exists (duplicate install = update).

        Args:
            manifest: SkillManifest instance (or any object with model_dump()).
        """
        data = (
            manifest.model_dump()
            if hasattr(manifest, "model_dump")
            else {"name": str(manifest)}
        )
        data["installed_at"] = datetime.now(timezone.utc).isoformat()
        data["current_stage"] = "INSTALL"
        self._skills[data["name"]] = data

    def get(self, name: str) -> dict[str, Any] | None:
        """Retrieve skill metadata by name.

        Returns a copy to prevent external mutation (consistent with
        security_events and entries() list-copy pattern).

        Returns:
            Copy of skill metadata dict, or None if not found.
        """
        entry = self._skills.get(name)
        return dict(entry) if entry else None

    def list_skills(self) -> list[str]:
        """Return list of all installed skill names.

        Returns fresh list copy.
        """
        return list(self._skills.keys())

    def revoke(self, name: str) -> None:
        """Remove a skill from the registry.

        Idempotent -- does not raise if skill is not found.
        """
        self._skills.pop(name, None)

    def update_stage(self, name: str, stage: str) -> None:
        """Update the current lifecycle stage for a skill.

        Used by SkillLifecycleManager to track progress.
        No-op if skill not found.
        """
        if name in self._skills:
            self._skills[name]["current_stage"] = stage
