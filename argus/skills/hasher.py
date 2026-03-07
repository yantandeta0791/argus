"""
Deterministic SHA-256 content hashing for skill package verification.

compute_content_hash  -- hash all files in a skill directory (deterministic order)
verify_content_hash   -- compare computed hash against expected value

Phase 5 (SKILL-03): Argus verifies the SHA-256 content hash of every skill
at install time and refuses to run skills whose hash does not match the manifest.

Hashing algorithm:
  1. Collect all files via rglob("*"), skip directories
  2. Exclude files where any path component is in {"__pycache__", ".git"} or suffix is ".pyc"
  3. Sort by relative path string for deterministic ordering
  4. For each file: update hasher with relative path (UTF-8) then file content (bytes)
  5. Return "sha256:<hex-digest>"

Hash format: "sha256:<64-char-hex-digest>"
Exclusions: __pycache__/, .git/, *.pyc, skill.yaml (manifest contains the hash)
"""
from __future__ import annotations

import hashlib
from pathlib import Path

HASH_EXCLUDE_PATTERNS: set[str] = {"__pycache__", ".git"}


def _should_exclude(rel_path: Path) -> bool:
    """Check if a file path should be excluded from hashing."""
    # Exclude if any path component is in the exclusion set
    for part in rel_path.parts:
        if part in HASH_EXCLUDE_PATTERNS:
            return True
    # Exclude .pyc files regardless of directory
    if rel_path.suffix == ".pyc":
        return True
    # Exclude the manifest itself -- it contains the hash (chicken-and-egg)
    if rel_path.name == "skill.yaml":
        return True
    return False


def compute_content_hash(skill_dir: Path) -> str:
    """Compute deterministic SHA-256 hash over skill directory contents.

    Args:
        skill_dir: Path to the skill package directory.

    Returns:
        Hash string in format "sha256:<64-char-hex-digest>".

    Raises:
        ValueError: If no hashable files are found in the directory.
    """
    # Collect all files, skip directories
    files: list[Path] = []
    for path in skill_dir.rglob("*"):
        if path.is_dir():
            continue
        rel_path = path.relative_to(skill_dir)
        if not _should_exclude(rel_path):
            files.append(rel_path)

    if not files:
        raise ValueError("No hashable files found in skill directory")

    # Sort for deterministic ordering
    files.sort(key=str)

    # Hash: for each file, feed relative path then content
    hasher = hashlib.sha256()
    for rel_path in files:
        hasher.update(str(rel_path).encode("utf-8"))
        full_path = skill_dir / rel_path
        hasher.update(full_path.read_bytes())

    return f"sha256:{hasher.hexdigest()}"


def verify_content_hash(skill_dir: Path, expected_hash: str) -> bool:
    """Verify that computed hash matches expected hash.

    Args:
        skill_dir: Path to the skill package directory.
        expected_hash: Expected hash string (e.g., "sha256:abcdef...").

    Returns:
        True if hashes match, False otherwise.
    """
    actual = compute_content_hash(skill_dir)
    return actual == expected_hash
