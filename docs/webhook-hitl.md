# Webhook HITL Approval (v0.7)

v0.7 removes the terminal-only constraint on Human-in-the-Loop approval. Any
agent running through the REST sidecar can now request approval from an
operator service — Slack, Teams, an internal security console, PagerDuty
workflow, or a small custom endpoint — without blocking on stdin.

## Configuration

```yaml
tools:
  deploy_production:
    require_approval: true
  export_customer_data:
    require_approval: true

hitl:
  webhook_url: https://security.example.com/api/argus/approve
  webhook_secret: ${ARGUS_WEBHOOK_SECRET}  # inject at deploy time; never commit
  webhook_timeout_seconds: 30
```

Use `ARGUS_WEBHOOK_SECRET` through your deployment system rather than a checked-in
YAML value. Argus currently parses the literal resolved config value; render
or template the environment variable in your deploy pipeline.

## Request contract

Argus sends one `POST` request with canonical JSON and headers:

```http
Content-Type: application/json
X-Argus-Signature: sha256=<hmac-sha256-of-exact-body>
```

Payload:

```json
{
  "request_id": "24-char-stable-request-id",
  "tool_name": "deploy_production",
  "tool_input": {"environment": "prod"},
  "caller_id": "release-agent",
  "hop_depth": 1,
  "max_depth": 3,
  "provenance": "user_originated",
  "anomaly_context": null,
  "expires_at": 1787412345.2
}
```

Verify `X-Argus-Signature` before rendering the request to an operator:

```python
expected = "sha256=" + hmac.new(
    SECRET.encode(), raw_request_body, hashlib.sha256
).hexdigest()
assert hmac.compare_digest(request.headers["X-Argus-Signature"], expected)
```

## Response contract and failure semantics

Only one reply permits the call:

```json
{"decision": "approve"}
```

Everything else fails closed:

| Result | Argus behavior |
|---|---|
| `{"decision":"approve"}` | allow tool call |
| `{"decision":"deny"}` | raise `ApprovalDeniedError(rule="webhook_denied")` |
| timeout, HTTP error, invalid JSON, missing/unknown `decision` | raise `ApprovalDeniedError(rule="webhook_unavailable")` |

A webhook deployment is therefore strictly safer than terminal HITL for REST
agents: a damaged approval service cannot silently permit an action.

## Security notes

- The webhook is a control-plane trust boundary. Run it behind TLS, authenticate
  it via the HMAC signature, and maintain replay/audit records keyed by
  `request_id`.
- Treat `tool_input` as sensitive. Do not forward it into public chat channels
  without field-level redaction.
- Enforce `expires_at` at your approval service; late decisions must not be
  approved.
- The timeout is deliberately bounded. There is no retry loop because retrying
  a high-impact action approval can create ambiguous operator experiences.
