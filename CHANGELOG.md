# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-03-08

### Added
- Real AuditDaemon subprocess lifecycle manager (replaces MagicMock in `argus run` and `argus demo`)
- LangChain adapter with proxy-based security enforcement (`argus.adapters.langchain`)
- SkillLifecycleManager verification wired into `argus scan`
- Multi-stage Dockerfile (`python:3.12-slim` + `uv`) and `docker-compose.yml`
- GitHub Actions CI workflow (pytest matrix on 3.12/3.13 + ruff lint)
- Apache 2.0 LICENSE file
- CONTRIBUTING.md, SECURITY.md, issue templates, and PR template
- CHANGELOG.md

### Fixed
- `NO_COLOR` env var and tty detection respected in Rich output
- `socket.connect()` probe in `wait_for_socket` prevents CI race condition
- Pin `pytest-asyncio==0.24.0` to avoid deprecation warnings

### Changed
- Removed stale `xfail` markers from engine, security, and observability tests

## [0.1.0] - 2026-03-07

### Added
- Security foundation: permission enforcement (Casbin RBAC/ABAC), hash-chained audit log, secret redaction, process isolation, prompt injection detection (14 OWASP LLM01:2025 patterns), egress control
- Execution engine: 5-state machine (PLAN/EXECUTE/VERIFY/REFLECT/COMMIT), tool contracts with Pydantic validation, retry, and circuit breaker
- LLM router: per-state model selection, per-task overrides, LiteLLM integration
- Cost router: hard spend caps (per-task, per-session, per-day), real-time cost tracking with deterministic ABORT on budget exceeded
- Memory system: working memory, session persistence, structured SQLite store
- Skill architecture: YAML manifests, 7-stage lifecycle, SHA-256 content verification
- Tier 1 skills: Security Audit, OWASP Agentic Top 10, Credential Scanner
- Observability: JSONL execution trace, OpenTelemetry spans, cost reporting, security event stream
- CLI: `argus demo` (scripted benchmark), `argus run` (full runtime), `argus scan` (static analysis)

[Unreleased]: https://github.com/yantandeta0791/argus/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/yantandeta0791/argus/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/yantandeta0791/argus/releases/tag/v0.1.0
