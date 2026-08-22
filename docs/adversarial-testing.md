# Adversarial Testing (v0.6)

Argus ships a versioned, executable attack corpus and publishes its detection
results. Detection claims are backed by a test anyone can run — not marketing
copy.

## Run it

```python
from argus.security.adversarial import run_corpus

report = run_corpus()
print(report["passed"], "/", report["total"])
# 16 / 16
print(report["detection_rate_by_category"])
# {'injection': 1.0, 'secret': 1.0}
```

Or via pytest (runs in CI on every commit):

```bash
pytest tests/security/test_v06_features.py::test_full_corpus_detected_by_live_gates -v
```

## What the corpus covers today

| Category | Cases | Gate under test | OWASP LLM ref |
|---|---|---|---|
| Injection (direct) | obfuscation via zero-width Unicode | PromptShield (Gate 3) | LLM01 |
| Injection (case/whitespace variants) | case-insensitivity of patterns | PromptShield | LLM01 |
| Injection (indirect framing) | `<system>` tags, `---BEGIN SYSTEM---` markers, `SYSTEM:` prefix | PromptShield | LLM01 |
| Secret exposure | OpenAI keys, GitHub tokens, AWS keys, Bearer tokens, PII email | SecretRedactor (Gate 4) | LLM02 |

Case IDs are stable and append-only (`INJ-001`, `SEC-001`, …). A failing case
means a regression in Argus — never delete or "fix" the case.

## Honest scope statement

This corpus proves the **deterministic baseline** works: pattern-based
injection detection and regex secret scrubbing. It does not claim:

- semantic injection detection (paraphrased attacks, non-English payloads)
- coverage of novel jailbreak techniques

For those layers, plug a classifier provider (Lakera, Azure Prompt Shields,
Bedrock Guardrails) at the adapter boundary; Argus still controls what an
agent may *do* when any detector misses. The corpus grows over time — new
cases are added as attack techniques are documented; published results are
regenerated per release.

## Adding cases

Append to `_INJECTION_PAYLOADS` / `_SECRET_PAYLOADS` in
`argus/security/adversarial.py` with the next stable ID. The runner treats
"gate did not raise / did not redact" as a failure entry — never an exception
— so a broken detector produces a readable report, not a crash.
