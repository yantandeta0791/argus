BUILTIN_PATTERNS = [
    # OWASP LLM01:2025 direct injection patterns (case-insensitive via re.compile flag)
    r'ignore\s+(?:all\s+)?previous\s+instructions?',
    r'you\s+are\s+now\s+(?:in\s+)?developer\s+mode',
    r'system\s+override',
    r'reveal\s+(?:your\s+)?prompt',
    r'disregard\s+(?:all\s+)?instructions?',
    r'forget\s+(?:all\s+)?previous\s+(?:instructions?|context)',
    r'you\s+are\s+now\s+(?:free|allowed|permitted)\s+to',
    r'print\s+your\s+(?:system\s+)?instructions?',
    r'output\s+your\s+(?:full\s+)?(?:system\s+)?prompt',
    # Jailbreak structural markers
    r'---BEGIN\s+(?:SYSTEM|INSTRUCTION)',
    # System prompt leakage indicators
    r'SYSTEM\s*:\s*You\s+are',
    # XML/HTML system instruction tags
    r'<\s*(?:system|instruction)\s*>',
    # Bracket-based system tags
    r'\[SYSTEM\].*(?:ignore|override|bypass)',
]
