---
applyTo: "**"
---

# Saba Enterprise API observability

Owner: Site Reliability Engineering.

- **SABA-OBS-001:** Accept `X-Correlation-ID` only when it matches
  `[A-Za-z0-9._-]{1,64}`; otherwise generate a UUID. Propagate the effective
  value in every response, including failures, and in Problem Details and logs.
  Correlation is diagnostic metadata, never an authorization credential.
- **SABA-OBS-002:** Emit a structured request-completion event containing the
  method, route template when available, status, duration, and correlation ID.
  Never log authorization headers, tokens, cookies, request/response bodies,
  query strings, raw validation inputs, or personal/business data.
- **SABA-OBS-003:** Unexpected failures produce a safe 500 Problem Details
  response and an error event. Do not expose internal exception text. Keep
  failures visible without logging sensitive payloads. Avoid duplicate error
  logs, success-shaped fallbacks, and silent catches.

Use the consumer's existing telemetry integration where compatible. Review
server access logs as well as application logs; an upstream server may otherwise
record query strings despite application-level redaction. Do not claim a logging
policy is satisfied solely because application logging is safe.
