# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.x     | Yes (current development) |

## Reporting a Vulnerability

**Do NOT open public issues for security vulnerabilities.**

Please report security vulnerabilities through GitHub Security Advisories:

1. Go to the [Security tab](https://github.com/yantandeta0791/argus/security) of the repository.
2. Click **Report a vulnerability**.
3. Fill in the details and submit.

This ensures the report is private and only visible to maintainers.

## Response Timeline

- **Acknowledgment**: Within 72 hours of report submission.
- **Fix target**: Within 30 days of acknowledgment, depending on severity and complexity.
- **Disclosure**: Coordinated disclosure after a fix is available.

## Scope

- **In scope**: Argus core code (security gateway, prompt shield, audit logger, permission enforcer, secret redactor, egress checker, state machine, CLI).
- **Out of scope**: Third-party dependencies. Issues in upstream libraries (LiteLLM, Casbin, Pydantic, etc.) should be reported directly to those projects.

## Credit

We will credit reporters in the release notes and CHANGELOG unless they prefer to remain anonymous.
