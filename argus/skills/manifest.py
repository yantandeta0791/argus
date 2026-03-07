"""
Skill manifest schema and validation for Argus.

SkillManifest   -- Pydantic v2 model for untrusted YAML skill manifests
TrustTier       -- 4-tier trust classification: builtin, verified, community, untrusted
BlastRadius     -- maximum impact scope: none, local, network, system
load_manifest   -- load and validate skill.yaml from a skill directory
validate_trust_tier -- enforce builtin tier restriction to argus/skills/ source tree

Phase 5 (SKILL-01): Every skill ships with a YAML manifest declaring
permissions, blast radius, data access, trust tier, and signing requirements.

Validation rules:
  - content_hash must start with "sha256:" followed by 64 hex chars
  - trust_tier and blast_radius are enum-validated (StrEnum)
  - builtin tier is only valid for skills inside argus/skills/ source tree
  - All required fields must be present; Pydantic rejects partial manifests
"""
from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator

from argus.security.exceptions import SkillIntegrityError

# Path to argus/skills/ source directory -- builtin tier validation anchor
ARGUS_SKILLS_DIR = Path(__file__).parent


class TrustTier(StrEnum):
    """Trust classification for skills. Determines permission ceiling and sandbox strictness."""
    BUILTIN = "builtin"
    VERIFIED = "verified"
    COMMUNITY = "community"
    UNTRUSTED = "untrusted"


class BlastRadius(StrEnum):
    """Maximum impact scope declared by a skill."""
    NONE = "none"
    LOCAL = "local"
    NETWORK = "network"
    SYSTEM = "system"


# Regex for content_hash: "sha256:" followed by exactly 64 hex characters
_HASH_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


class SkillManifest(BaseModel):
    """Pydantic v2 model for skill YAML manifests.

    Required fields: name, version, description, trust_tier, permissions, content_hash.
    Optional fields: blast_radius, data_access, egress_allowlist, timeout_s, idempotent.
    """

    # Required fields
    name: str
    version: str
    description: str
    trust_tier: TrustTier
    permissions: list[str]
    content_hash: str

    # Optional fields with defaults
    blast_radius: BlastRadius = BlastRadius.NONE
    data_access: list[str] = Field(default_factory=list)
    egress_allowlist: list[str] = Field(default_factory=list)
    timeout_s: float = 30.0
    idempotent: bool = True

    @field_validator("content_hash")
    @classmethod
    def validate_content_hash(cls, v: str) -> str:
        """Validate sha256: prefix and 64-char hex digest."""
        if not _HASH_PATTERN.match(v):
            raise ValueError(
                "content_hash must be 'sha256:' followed by 64 hex characters, "
                f"got: {v!r}"
            )
        return v


def load_manifest(skill_dir: Path) -> SkillManifest:
    """Load and validate skill.yaml from a skill directory.

    Args:
        skill_dir: Path to the skill package directory containing skill.yaml.

    Returns:
        Validated SkillManifest instance.

    Raises:
        FileNotFoundError: If skill.yaml does not exist in skill_dir.
        pydantic.ValidationError: If manifest YAML is invalid or missing required fields.
    """
    yaml_path = skill_dir / "skill.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"skill.yaml not found in {skill_dir}")

    with open(yaml_path) as f:
        raw = yaml.safe_load(f)

    return SkillManifest.model_validate(raw or {})


def validate_trust_tier(manifest: SkillManifest, skill_dir: Path) -> None:
    """Enforce that builtin tier is only valid for skills inside argus/skills/.

    Args:
        manifest: Validated SkillManifest instance.
        skill_dir: Path to the skill package directory.

    Raises:
        SkillIntegrityError: If skill declares builtin tier but is outside argus/skills/.
    """
    if manifest.trust_tier == TrustTier.BUILTIN:
        try:
            skill_dir.resolve().relative_to(ARGUS_SKILLS_DIR.resolve())
        except ValueError:
            raise SkillIntegrityError(
                gate="skill_lifecycle",
                blocked=manifest.name,
                rule="builtin tier requires skill inside argus/skills/",
            )
