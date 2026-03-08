"""ASI01-ASI10 check implementations for OWASP Agentic Top 10."""

from __future__ import annotations

from argus.skills.owasp_top10.report import CategoryResult

# ASI01 injection patterns — case-insensitive substring match
_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all previous",
    "disregard",
    "jailbreak",
    "you are now",
    "forget your instructions",
]


def _check_asi01(config: dict) -> CategoryResult:
    """Prompt Injection — detect injection patterns in system_prompt or tool descriptions."""
    texts: list[str] = []
    system_prompt = config.get("system_prompt", "")
    if system_prompt:
        texts.append(system_prompt.lower())
    for tool in config.get("tools", []):
        desc = tool.get("description", "")
        if desc:
            texts.append(desc.lower())

    for text in texts:
        for pattern in _INJECTION_PATTERNS:
            if pattern in text:
                return CategoryResult(
                    category_id="ASI01",
                    name="Prompt Injection",
                    passed=False,
                    details=f"Injection pattern found: '{pattern}'",
                )
    return CategoryResult(
        category_id="ASI01",
        name="Prompt Injection",
        passed=True,
        details="No injection patterns detected.",
    )


def _check_asi02(config: dict) -> CategoryResult:
    """Excessive Permissions — wildcard permission check."""
    permissions = config.get("permissions", [])
    if "*" in permissions:
        return CategoryResult(
            category_id="ASI02",
            name="Excessive Permissions",
            passed=False,
            details="Wildcard permission '*' found in permissions list.",
        )
    return CategoryResult(
        category_id="ASI02",
        name="Excessive Permissions",
        passed=True,
        details="No wildcard permissions detected.",
    )


def _check_asi03(config: dict) -> CategoryResult:
    """Sensitive Data Exposure — PII/secret data access without redaction."""
    _SENSITIVE_KEYWORDS = {"pii", "password", "secret"}
    data_access = config.get("data_access", [])
    redaction_enabled = config.get("redaction_enabled", False)
    if not redaction_enabled:
        for entry in data_access:
            entry_lower = entry.lower()
            for keyword in _SENSITIVE_KEYWORDS:
                if keyword in entry_lower:
                    return CategoryResult(
                        category_id="ASI03",
                        name="Sensitive Data Exposure",
                        passed=False,
                        details=(
                            f"Sensitive data key '{entry}' in data_access without "
                            "redaction_enabled."
                        ),
                    )
    return CategoryResult(
        category_id="ASI03",
        name="Sensitive Data Exposure",
        passed=True,
        details="No unprotected sensitive data access detected.",
    )


def _check_asi04(config: dict) -> CategoryResult:
    """Data and Model Poisoning — unvalidated external data sources."""
    # Check tool_config level first (plan spec)
    tool_config = config.get("tool_config", {})
    if tool_config.get("validated", True) is False:
        return CategoryResult(
            category_id="ASI04",
            name="Data and Model Poisoning",
            passed=False,
            details="tool_config has unvalidated external data source.",
        )
    # Also check tool-level validated flag (test spec: tools[*].validated)
    for tool in config.get("tools", []):
        if tool.get("validated", True) is False:
            return CategoryResult(
                category_id="ASI04",
                name="Data and Model Poisoning",
                passed=False,
                details=f"Tool '{tool.get('name', 'unknown')}' has validated=False.",
            )
    return CategoryResult(
        category_id="ASI04",
        name="Data and Model Poisoning",
        passed=True,
        details="No unvalidated external data sources detected.",
    )


def _check_asi05(config: dict) -> CategoryResult:
    """Supply Chain Risk — community or untrusted skill trust tiers."""
    _RISKY_TIERS = {"community", "untrusted"}
    for skill in config.get("skills", []):
        tier = skill.get("trust_tier", "builtin")
        if tier in _RISKY_TIERS:
            return CategoryResult(
                category_id="ASI05",
                name="Supply Chain Risk",
                passed=False,
                details=(
                    f"Skill '{skill.get('name', 'unknown')}' has trust_tier='{tier}'."
                ),
            )
    return CategoryResult(
        category_id="ASI05",
        name="Supply Chain Risk",
        passed=True,
        details="All skills have acceptable trust tiers.",
    )


def _check_asi06(config: dict) -> CategoryResult:
    """Unsafe Action Execution — non-idempotent tools without confirmation gate."""
    for tool in config.get("tools", []):
        idempotent = tool.get("idempotent", True)
        confirmation_gate = tool.get("confirmation_gate")
        if idempotent is False and not confirmation_gate:
            return CategoryResult(
                category_id="ASI06",
                name="Unsafe Action Execution",
                passed=False,
                details=(
                    f"Tool '{tool.get('name', 'unknown')}' is non-idempotent "
                    "without a confirmation_gate."
                ),
            )
    return CategoryResult(
        category_id="ASI06",
        name="Unsafe Action Execution",
        passed=True,
        details="All non-idempotent tools have confirmation gates.",
    )


def _check_asi07(config: dict) -> CategoryResult:
    """Resource Exhaustion — missing cost cap."""
    if config.get("cost_cap") is None:
        return CategoryResult(
            category_id="ASI07",
            name="Resource Exhaustion",
            passed=False,
            details="No cost_cap configured.",
        )
    return CategoryResult(
        category_id="ASI07",
        name="Resource Exhaustion",
        passed=True,
        details="cost_cap is configured.",
    )


def _check_asi08(config: dict) -> CategoryResult:
    """Inadequate Monitoring — missing audit log path."""
    if config.get("audit_log_path") is None:
        return CategoryResult(
            category_id="ASI08",
            name="Inadequate Monitoring",
            passed=False,
            details="No audit_log_path configured.",
        )
    return CategoryResult(
        category_id="ASI08",
        name="Inadequate Monitoring",
        passed=True,
        details="audit_log_path is configured.",
    )


def _check_asi09(config: dict) -> CategoryResult:
    """Excessive Agency — system blast radius without human-in-the-loop."""
    blast_radius = config.get("blast_radius")
    human_in_loop = config.get("human_in_loop", False)
    if blast_radius == "system" and not human_in_loop:
        return CategoryResult(
            category_id="ASI09",
            name="Excessive Agency",
            passed=False,
            details="blast_radius='system' without human_in_loop=True.",
        )
    return CategoryResult(
        category_id="ASI09",
        name="Excessive Agency",
        passed=True,
        details="Acceptable agency configuration.",
    )


def _check_asi10(config: dict) -> CategoryResult:
    """Misinformation Risk — LLM output passed to action without verification."""
    # Check pipeline-based spec: llm_output -> action without verify in between
    pipeline = config.get("pipeline", [])
    if pipeline:
        steps = [s.get("step", "") if isinstance(s, dict) else str(s) for s in pipeline]
        for i, step in enumerate(steps):
            if step == "llm_output":
                # Look for "action" after this step without "verify" between
                remaining = steps[i + 1 :]
                verify_found = False
                for subsequent in remaining:
                    if subsequent == "verify":
                        verify_found = True
                        break
                    if subsequent == "action":
                        if not verify_found:
                            return CategoryResult(
                                category_id="ASI10",
                                name="Misinformation Risk",
                                passed=False,
                                details=(
                                    "LLM output passed directly to action step "
                                    "without a verify step in between."
                                ),
                            )
                        break

    # Check tool-level llm_output_verified flag (test spec: tools[*].llm_output_verified)
    for tool in config.get("tools", []):
        if tool.get("llm_output_verified", True) is False:
            return CategoryResult(
                category_id="ASI10",
                name="Misinformation Risk",
                passed=False,
                details=(
                    f"Tool '{tool.get('name', 'unknown')}' has "
                    "llm_output_verified=False."
                ),
            )

    return CategoryResult(
        category_id="ASI10",
        name="Misinformation Risk",
        passed=True,
        details="No unverified LLM output pipelines detected.",
    )


def check_all(agent_config: dict) -> list[CategoryResult]:
    """Run all 10 ASI checks against agent_config.

    Args:
        agent_config: Agent configuration dict. Sparse dicts are safe (all
            key accesses use .get() with safe defaults).

    Returns:
        list of exactly 10 CategoryResult objects, one per ASI category.
    """
    return [
        _check_asi01(agent_config),
        _check_asi02(agent_config),
        _check_asi03(agent_config),
        _check_asi04(agent_config),
        _check_asi05(agent_config),
        _check_asi06(agent_config),
        _check_asi07(agent_config),
        _check_asi08(agent_config),
        _check_asi09(agent_config),
        _check_asi10(agent_config),
    ]
