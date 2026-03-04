import hashlib
import json
from typing import Any

GENESIS_HASH = "0" * 64  # Sentinel for the first entry


def build_entry(event: dict[str, Any], prev_hash: str) -> tuple[str, str]:
    """
    Build a hash-chained JSONL entry.
    Returns (json_line, entry_hash) where entry_hash becomes prev_hash for the next entry.

    CRITICAL: sort_keys=True is mandatory for canonical form.
    Different key insertion orders must produce identical hashes for identical logical entries.
    """
    entry = {**event, "prev_hash": prev_hash}
    canonical = json.dumps(entry, sort_keys=True, separators=(",", ":"))
    entry_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return canonical, entry_hash


def verify_chain(jsonl_path: str) -> list[int]:
    """
    Read the JSONL audit log and verify hash chain integrity.
    Returns list of 1-indexed line numbers where the chain is broken (empty = intact).
    """
    broken_lines = []
    prev_hash = GENESIS_HASH

    with open(jsonl_path, "r") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            stored_prev = entry.get("prev_hash")

            if stored_prev != prev_hash:
                broken_lines.append(lineno)

            # Recompute hash of this entry (canonical form) for next iteration
            canonical = json.dumps(entry, sort_keys=True, separators=(",", ":"))
            prev_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    return broken_lines
