"""
Public API surface for argus.skills.

Re-exports all 11 symbols that Phase 6 and downstream consumers use via
`from argus.skills import ...`. Implementation details live in sub-modules;
only these 11 names are the public contract.
"""

from argus.skills.manifest import (
    BlastRadius,
    SkillManifest,
    TrustTier,
    load_manifest,
    validate_trust_tier,
)
from argus.skills.hasher import compute_content_hash, verify_content_hash
from argus.skills.lifecycle import (
    LIFECYCLE_SEQUENCE,
    SkillLifecycleManager,
    SkillStage,
)
from argus.skills.registry import SkillRegistry

__all__ = [
    "BlastRadius",
    "LIFECYCLE_SEQUENCE",
    "SkillLifecycleManager",
    "SkillManifest",
    "SkillRegistry",
    "SkillStage",
    "TrustTier",
    "compute_content_hash",
    "load_manifest",
    "validate_trust_tier",
    "verify_content_hash",
]
