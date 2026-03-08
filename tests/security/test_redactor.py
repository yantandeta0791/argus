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
