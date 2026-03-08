# Contributing to Argus

Thank you for your interest in contributing to Argus. This guide covers the essentials for getting started.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Setup

```bash
git clone https://github.com/yantandeta0791/argus.git
cd argus
uv pip install -e ".[dev]"
```

## Running Tests

```bash
python -m pytest -v
```

Run a specific test module:

```bash
python -m pytest tests/security/ -v
```

## Code Style

Argus uses [ruff](https://docs.astral.sh/ruff/) for formatting and linting. Before committing, run:

```bash
ruff format .
ruff check .
```

CI will reject PRs that fail either check.

## Pull Request Process

1. Fork the repository and create a feature branch from `master`.
2. Make your changes in focused, well-scoped commits.
3. Add or update tests for any changed behavior.
4. Ensure the full test suite passes: `python -m pytest -v`
5. Ensure code passes formatting and lint checks: `ruff format --check . && ruff check .`
6. Open a PR against `master` with a clear description of the change.

## Commit Conventions

We use [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix   | Use for                          |
|----------|----------------------------------|
| `feat:`  | New features                     |
| `fix:`   | Bug fixes                        |
| `docs:`  | Documentation changes            |
| `test:`  | Adding or updating tests         |
| `ci:`    | CI/CD changes                    |
| `chore:` | Maintenance, dependencies, etc.  |

Examples:

```
feat: add egress enforcement to sandbox runtime
fix: correct hash chain verification for empty logs
docs: update configuration reference for spend caps
```

## Reporting Issues

- **Bugs**: Use the [Bug Report](https://github.com/yantandeta0791/argus/issues/new?template=bug_report.yml) template.
- **Features**: Use the [Feature Request](https://github.com/yantandeta0791/argus/issues/new?template=feature_request.yml) template.
- **Security vulnerabilities**: See [SECURITY.md](SECURITY.md). Do **not** open public issues.

## Code of Conduct

This project follows the [Contributor Covenant 2.1](CODE_OF_CONDUCT.md). By participating, you agree to uphold it.
