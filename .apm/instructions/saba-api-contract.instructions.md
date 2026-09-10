---
applyTo: "**"
---

# Saba Enterprise API contract

Owner: API Architecture. These are hypothetical Saba Enterprise standards.
Normative requirements apply when designing or changing an HTTP API.

- **SABA-API-001:** Use `/api/v1` and plural kebab-case resource paths for new
  APIs. Define stable, unique OpenAPI operation IDs. Existing incompatible
  conventions require an explicit migration decision, not an unsolicited rewrite.
- **SABA-API-002:** Define separate request and public response schemas. Reject
  unknown request properties, bound strings and numbers, and validate identifiers.
  Never bind client input directly to internal persistence or ownership fields.
  Document exact decimal representation for money; do not use binary floats.
- **SABA-API-003:** Document success and applicable failure responses. Use RFC 9457
  Problem Details with `application/problem+json` and `type`, `title`, `status`,
  `detail`, `instance`, and `correlation_id`. `status` matches the HTTP status.
  Do not expose tokens, raw rejected inputs, SQL, exception messages, or traces.
  Use stable problem type URIs. Preserve protocol headers such as `Allow` and
  `WWW-Authenticate`.
- **SABA-API-004:** List endpoints default to 25 results and reject limits outside
  1 through 100 and negative offsets. Specify stable ordering with a unique
  tie-breaker. Apply authorization before pagination and counts. These are
  company defaults; an exception needs an explicit recorded decision.
- **SABA-API-005:** Review contract changes for compatibility. Do not silently
  remove or rename fields, narrow accepted values, or change status semantics
  in an existing v1 contract. Record migrations and required consumer actions.

The endpoint design must name its business-specific conflict conditions instead
of treating every failed operation as 400 or 500. Guidance requires executable
validation and tests in the consuming service.
