def test_api_key_redaction():
    from argus.security.redactor.redactor import SecretRedactor

    redactor = SecretRedactor()
    output = "The result is OK. API_KEY=sk-1234567890abcdef1234567890abcdef"
    result = redactor.redact(output)
    assert "sk-1234" not in result
    assert "[REDACTED]" in result


def test_pii_email_redaction():
    from argus.security.redactor.redactor import SecretRedactor

    redactor = SecretRedactor()
    output = "Contact user@example.com for details."
    result = redactor.redact(output)
    assert "user@example.com" not in result
    assert "[REDACTED]" in result


def test_soft_block_run_continues():
    from argus.security.redactor.redactor import SecretRedactor

    redactor = SecretRedactor()
    # Redaction must NOT raise — it returns sanitized output (soft block)
    output = "token=ghp_abcdefghijklmnopqrstuvwxyz123456"
    result = redactor.redact(output)
    assert isinstance(result, str)
    assert "ghp_" not in result


def test_extra_patterns_redacted():
    """POLC-02: custom secret patterns from argus.yaml are applied by SecretRedactor."""
    from argus.security.redactor.redactor import SecretRedactor

    redactor = SecretRedactor(extra_patterns=[r"INTERNAL-\d{6}"])
    output = "Reference: INTERNAL-123456 is classified."
    result = redactor.redact(output)
    assert "INTERNAL-123456" not in result
    assert "[REDACTED]" in result


def test_extra_patterns_alongside_builtins():
    """POLC-02: custom patterns work alongside built-in patterns."""
    from argus.security.redactor.redactor import SecretRedactor

    redactor = SecretRedactor(extra_patterns=[r"CUSTOM-[A-Z]{4}"])
    output = "key=sk-1234567890abcdef1234567890abcdef ref=CUSTOM-ABCD"
    result = redactor.redact(output)
    assert "sk-1234" not in result
    assert "CUSTOM-ABCD" not in result
    assert result.count("[REDACTED]") == 2


def test_extra_patterns_empty_list_no_effect():
    """Extra patterns as empty list behaves same as default."""
    from argus.security.redactor.redactor import SecretRedactor

    redactor = SecretRedactor(extra_patterns=[])
    output = "safe text with no secrets"
    result = redactor.redact(output)
    assert result == output
