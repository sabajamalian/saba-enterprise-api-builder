---
applyTo: "**"
---

# Saba Enterprise API security

Owner: Identity and Application Security. Apply to API identity, access, input,
and data handling. These requirements need implementation and negative tests.

- **SABA-SEC-001:** Validate bearer JWTs using a maintained library and a fixed
  approved algorithm (RS256 for the FastAPI profile). Verify signature, trusted
  issuer, intended audience, expiry, and required claims. Require nonempty
  `sub`, `iss`, `aud`, `exp`, and `iat`; honor `nbf` when present. Configure
  trusted keys independently from requests. Never follow token `jku` or `x5u`.
  Missing identity configuration must fail startup. Never disable verification
  to make local development work.
- **SABA-SEC-002:** Define explicit operation scopes. Missing or invalid identity
  returns 401 and a Bearer challenge. A verified caller missing a required scope
  receives 403. Document the scopes in OpenAPI and test both cases.
- **SABA-SEC-003:** Enforce object-level authorization in queries. Derive ownership
  from the verified subject, never a submitted owner field. Return 404 for a
  resource the caller cannot see. Filter lists and counts before pagination.
  Never accept possession of a UUID as evidence of access.
- **SABA-SEC-004:** Use trusted HTTPS JWKS configuration or an explicitly
  configured local public key set. Bound network timeouts, cache lifetime, and
  unknown-key refresh. Do not follow arbitrary redirects. Authentication fails
  closed when no valid trusted key is available. Local token generation stays
  outside the HTTP API. Never commit private keys or reusable tokens.

Consumer-specific role mappings, issuer configuration, and business access rules
must be explicit. Ask if they are missing. Do not invent a privileged account,
hardcode credentials, create an allow-all mode, or copy authentication settings
from another organization.

Runtime identity providers and application authorization enforce access. APM
package approval does not authorize an API request or inspect token scopes.
