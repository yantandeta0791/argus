"""Security Audit skill — manifest checker implementing SA-001..SA-007 rules.

SA-001: ERROR when pydantic ValidationError or FileNotFoundError loading manifest.
SA-002: ERROR when trust_tier==BUILTIN but skill directory is outside argus/skills/.
SA-003: WARNING when blast_radius in {SYSTEM, NETWORK} and egress_allowlist is empty.
SA-004: ERROR when "*" in permissions list.
SA-005: Subsumed by SA-001 — pydantic's content_hash field_validator enforces the
        sha256: prefix pattern; an invalid hash triggers SA-001 before SA-005 fires.
SA-006: WARNING when idempotent==False and blast_radius==NETWORK.
SA-007: WARNING when timeout_s > 300.

Rules execute in order SA-001..SA-007; SA-001 short-circuits if the manifest
cannot be loaded (no further rules run on a broken manifest).
"""
from __future__ import annotations

from pathlib import Path

import pydantic

from argus.skills.manifest import (
    ARGUS_SKILLS_DIR,
    BlastRadius,
    TrustTier,
    load_manifest,
)
from argus.skills.security_audit.findings import Finding, Severity


def check_manifest(target: Path) -> list[Finding]:
    """Run SA-001..SA-007 rules against a skill directory manifest.

    Args:
        target: Path to a skill directory containing skill.yaml.

    Returns:
        List of Finding objects. Empty list means no rule violations.
        SA-001 short-circuits: if the manifest fails to load, only SA-001 is returned.
    """
    findings: list[Finding] = []

    # ------------------------------------------------------------------ SA-001 / SA-005
    # SA-005 is triggered when pydantic rejects content_hash for invalid format.
    # We detect it by inspecting the ValidationError field errors before falling
    # back to the generic SA-001 finding.
    try:
        manifest = load_manifest(target)
    except pydantic.ValidationError as exc:
        # Check if the error is specifically about content_hash (SA-005)
        err_fields = {err["loc"][0] for err in exc.errors() if err.get("loc")}
        if err_fields == {"content_hash"}:
            findings.append(
                Finding(
                    rule_id="SA-005",
                    severity=Severity.ERROR,
                    message=(
                        "content_hash format is invalid; expected 'sha256:' "
                        f"followed by 64 hex characters"
                    ),
                    location="skill.yaml:content_hash",
                    remediation=(
                        "Set content_hash to the SHA-256 digest of the skill "
                        "source files, prefixed with 'sha256:'"
                    ),
                )
            )
        else:
            findings.append(
                Finding(
                    rule_id="SA-001",
                    severity=Severity.ERROR,
                    message=str(exc),
                    location="skill.yaml",
                    remediation="Ensure all required manifest fields are present and valid",
                )
            )
        return findings  # short-circuit
    except FileNotFoundError as exc:
        findings.append(
            Finding(
                rule_id="SA-001",
                severity=Severity.ERROR,
                message=str(exc),
                location="skill.yaml",
                remediation="Ensure all required manifest fields are present and valid",
            )
        )
        return findings  # short-circuit — remaining rules require a valid manifest

    # ------------------------------------------------------------------ SA-002
    if manifest.trust_tier == TrustTier.BUILTIN:
        try:
            target.resolve().relative_to(ARGUS_SKILLS_DIR.resolve())
        except ValueError:
            findings.append(
                Finding(
                    rule_id="SA-002",
                    severity=Severity.ERROR,
                    message=(
                        f"Skill declares trust_tier=builtin but its directory "
                        f"'{target}' is outside the argus/skills/ source tree"
                    ),
                    location="skill.yaml:trust_tier",
                    remediation=(
                        "Use trust_tier=community or move the skill inside argus/skills/"
                    ),
                )
            )

    # ------------------------------------------------------------------ SA-003
    if manifest.blast_radius in {BlastRadius.SYSTEM, BlastRadius.NETWORK} and not manifest.egress_allowlist:
        findings.append(
            Finding(
                rule_id="SA-003",
                severity=Severity.WARNING,
                message=(
                    f"Skill has blast_radius={manifest.blast_radius} "
                    f"but declares no egress_allowlist"
                ),
                location="skill.yaml:egress_allowlist",
                remediation="Declare egress_allowlist for high blast-radius skills",
            )
        )

    # ------------------------------------------------------------------ SA-004
    if "*" in manifest.permissions:
        findings.append(
            Finding(
                rule_id="SA-004",
                severity=Severity.ERROR,
                message="Skill permissions contain wildcard '*'",
                location="skill.yaml:permissions",
                remediation="Replace wildcard with explicit permission declarations",
            )
        )

    # ------------------------------------------------------------------ SA-006
    if not manifest.idempotent and manifest.blast_radius == BlastRadius.NETWORK:
        findings.append(
            Finding(
                rule_id="SA-006",
                severity=Severity.WARNING,
                message=(
                    "Skill is non-idempotent with blast_radius=network — "
                    "repeated execution may cause unintended side effects"
                ),
                location="skill.yaml:idempotent",
                remediation=(
                    "Set idempotent=true or reduce blast_radius to local/none"
                ),
            )
        )

    # ------------------------------------------------------------------ SA-007
    if manifest.timeout_s > 300:
        findings.append(
            Finding(
                rule_id="SA-007",
                severity=Severity.WARNING,
                message=f"Skill timeout_s={manifest.timeout_s} exceeds 300 seconds",
                location="skill.yaml:timeout_s",
                remediation="Set timeout_s <= 300 to prevent runaway skill execution",
            )
        )

    return findings
