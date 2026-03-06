"""
argus.memory -- SQLite-backed session persistence and structured state store.

Phase 4 provides three memory tiers:
  - Working memory: RunContext.artifacts (ephemeral per run, Phase 2)
  - Session memory: SessionStore (cross-run within session, Phase 4)
  - Structured state: global facts in SQLite (cross-session, Phase 4)

Public API populated in Plan 04.
"""
