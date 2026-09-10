# FastAPI reference

A runnable purchase-request API for **Saba Enterprise, a hypothetical company**.
This demonstrates the API Builder's contracts and executable checks. It isn't
a production procurement system, an identity provider, or a cloud deployment.

## Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Python 3.12 or newer. This implementation was tested with **CPython 3.12.13**
  and **uv 0.11.2**. `.python-version` selects managed Python 3.12.

Run these commands from the repository root:

```sh
cd reference-api
uv sync --locked
uv run --locked python -m saba_api.dev keys
export SABA_ISSUER='https://local.saba.example'
export SABA_AUDIENCE='saba-reference-api'
export SABA_JWKS_PATH="$PWD/.local/jwks.json"
unset SABA_JWKS_URL
uv run --locked python -m saba_api
```

The launch module binds to `127.0.0.1:8000`, emits structured request-completion
logs, and disables Uvicorn access logs so URLs and query values aren't recorded.
The ASGI import target is `saba_api.main:app`. If running Uvicorn directly, include
`--no-access-log` and configure the `saba_api.requests` logger at INFO.
`/docs` and `/openapi.json` expose the contract. `/health` is public.

The key helper creates a new RSA identity in ignored `.local/`; the private key
has mode `600`. It refuses to overwrite existing keys. These files are temporary
development credentials, not production key material. Delete them when finished
and explicitly regenerate them when needed. Restart the API after changing a
local public JWKS file.

### Call the API

In a second terminal, start from the repository root:

```sh
cd reference-api
export SABA_ISSUER='https://local.saba.example'
export SABA_AUDIENCE='saba-reference-api'

# Keep the short-lived token in this shell only. Don't print it or commit it.
TOKEN="$(uv run --locked python -m saba_api.dev token \
  --issuer "$SABA_ISSUER" \
  --audience "$SABA_AUDIENCE" \
  --subject local-user \
  --scope 'purchase-requests:read purchase-requests:write')"

curl --fail-with-body --silent --show-error http://127.0.0.1:8000/health

CREATED="$(curl --fail-with-body --silent --show-error \
  -X POST http://127.0.0.1:8000/api/v1/purchase-requests \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -H 'X-Correlation-ID: local-create-1' \
  --data '{"title":"Research equipment","description":"One workstation","amount":"1234.56","currency":"USD"}')"
REQUEST_ID="$(printf '%s' "$CREATED" | uv run --locked python -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

curl --fail-with-body --silent --show-error \
  "http://127.0.0.1:8000/api/v1/purchase-requests/$REQUEST_ID" \
  -H "Authorization: Bearer $TOKEN"

curl --fail-with-body --silent --show-error \
  'http://127.0.0.1:8000/api/v1/purchase-requests?limit=25&offset=0' \
  -H "Authorization: Bearer $TOKEN"

# This intentionally returns 401 Problem Details with a Bearer challenge.
curl --silent --show-error --include \
  http://127.0.0.1:8000/api/v1/purchase-requests
unset TOKEN
```

Tokens expire after 15 minutes. Generate a new one with the same token command
if needed. There is no HTTP token-issuance endpoint.

## Contract

| Endpoint | Success | Required scope |
| --- | --- | --- |
| `GET /health` | 200, status | None |
| `POST /api/v1/purchase-requests` | 201, created request | `purchase-requests:write` |
| `GET /api/v1/purchase-requests/{request_id}` | 200, owned request | `purchase-requests:read` |
| `GET /api/v1/purchase-requests` | 200, page | `purchase-requests:read` |

- Input: `title` (trimmed, 1 to 120 characters), optional `description`
  (trimmed, at most 2,000 characters, default empty), `amount`, and `currency`.
  Unknown properties, including owner fields, are rejected.
- Money must be a decimal **JSON string**, from `"0.01"` to `"999999999.99"`,
  with at most two fractional digits. Exponents, numeric JSON values,
  nonfinite values, and negative values are rejected. Responses use two
  fractional digits. SQLite stores integer cents, not binary floating point.
- Currency must contain exactly three uppercase ASCII letters. This checks
  format, not membership in a currency registry.
- IDs are UUIDs. `created_at` is UTC. Internal owner IDs aren't response fields.
- Ownership comes only from the verified token subject. Another user's UUID
  returns the same 404 as a missing resource. Lists query only the caller's rows.
- Pages contain `items`, `limit`, and `offset`. Default limit is 25, maximum
  100, minimum 1. Offset is 0 to SQLite's signed 64-bit maximum. Invalid values
  return 422, not silent clamping. Ordering is `created_at ASC, id ASC`.

The security scheme is HTTP bearer, not a fabricated OAuth authorization flow.
OpenAPI documents the exact permission names in the scheme description and in
each protected operation's `x-required-scopes` extension. The token's `scope`
claim is a space-delimited string.

### Errors and logs

API errors use RFC 9457 `application/problem+json`, including validation,
authentication, authorization, missing routes/resources, unsupported methods,
identity outages, and unexpected failures. Each has `type`, `title`, `status`,
`detail`, `instance` (path without query), and `correlation_id`.
Validation adds `errors` containing only safe field paths and error codes;
unknown property names are replaced with `<unknown>`.

Problem type identifiers follow `https://saba.example/problems/http-{status}`.
They are stable example identifiers, not claims of a hosted documentation site:

| Status | Meaning |
| --- | --- |
| 401 | Missing or invalid bearer credentials; includes `WWW-Authenticate` |
| 403 | Verified identity lacks the required scope |
| 404 | Route or owned resource not found |
| 405 | Unsupported HTTP method; preserves `Allow` |
| 422 | Invalid request fields, ID, or pagination |
| 500 | Unexpected failure, without internal exception details |
| 503 | Trusted identity keys temporarily unavailable; includes `Retry-After` |

Every response carries `X-Correlation-ID`. Exactly one inbound header matching
`[A-Za-z0-9._-]{1,64}` is retained; otherwise a UUID is generated.
Completion logs contain event name, HTTP method, route **template**, status,
duration, and correlation ID. Unmatched paths aren't logged. Unexpected-error
logs omit exception messages and tracebacks because they can contain secrets.
Neither request bodies, bearer tokens, query values, nor resource IDs are logged.

## Configuration and remote identity keys

| Environment variable | Meaning |
| --- | --- |
| `SABA_ISSUER` | Required exact token issuer |
| `SABA_AUDIENCE` | Required accepted audience |
| `SABA_JWKS_PATH` | Local public JWKS file, mutually exclusive with URL |
| `SABA_JWKS_URL` | Operator-configured trusted HTTPS JWKS URL |
| `SABA_DATABASE_URL` | Optional SQLite URL; defaults to `sqlite:///.local/purchase-requests.db` |

Missing identity configuration or an invalid local JWKS fails startup.
Authentication cannot be disabled. The default database is persistent across
restarts; its tables are created at startup.

For an existing identity provider, set its issuer, audience, and HTTPS JWKS URL,
then unset `SABA_JWKS_PATH`. Obtain bearer tokens through that provider's normal
flow. The API doesn't discover endpoints from token headers or issue provider
tokens. It accepts only RS256 signatures, using public RSA keys of at least
2,048 bits. Signature, issuer, audience, expiration, issued-at, and optional
not-before are verified. `sub`, `iat`, `exp`, `iss`, and `aud` are required;
`sub` must be a nonblank string. Token-provided `jku` and `x5u` aren't trusted.

Remote retrieval uses certificate-verified HTTPS, a 2-second connect timeout,
5-second I/O timeouts, a 5-second elapsed retrieval check between chunks, a
1 MiB response limit, and at most 32 keys. A stalled read can add up to one I/O
timeout beyond the elapsed check. Compressed responses and redirects are
rejected. Proxy settings from the environment aren't inherited. Keys are cached
for 5 minutes per process. Unknown-key refreshes and failed retrieval retries
are limited to one attempt per 30 seconds, coordinated across request threads.
Providers should publish new keys before using them to sign tokens.

An unexpired cached known key remains usable during an issuer outage. Expired
keys never get a stale-cache fallback. An unknown key after a successful refresh
returns 401; unavailable or invalid remote key material returns safe 503.
Local files are loaded once at startup and don't use remote refresh.

## Tests

```sh
cd reference-api
uv sync --locked
uv run --locked pytest
```

Tests generate asymmetric keys per session and create isolated SQLite files
under ignored `.local/pytest/`. No tenant, cloud resource, or external identity
network is used. Coverage includes ownership, persistence, exact money,
pagination order/bounds, JWT rejection cases, key rotation and concurrent
refresh suppression, issuer outages, log redaction, safe 500 responses, and
OpenAPI references. `tests/contracts.py` contains the reusable Problem Details
assertion. Negative fixtures prove it rejects malformed error output.

The initial installation used a mirror while canonical downloads were unavailable.
`uv.lock` now references only canonical PyPI: all 298 distribution filenames,
SHA256 hashes, and sizes were matched against exact-version PyPI metadata before
migrating their URLs. Dependency versions and other metadata are unchanged.
Offline lock checking and synchronization of the installed environment pass;
142 tests pass against those hash-identical installed distributions. A clean
offline canonical installation fails because canonical artifacts aren't cached.
Successful canonical package downloads remain unverified in this environment.

## Production boundaries

This is a small local reference, not a production-readiness claim:

- SQLite table creation isn't a migration, backup, high-availability, or
  concurrent-write strategy. Use reviewed migrations and deployment-specific
  persistence for a production service.
- Offset pagination isn't a snapshot across requests; concurrent insertions
  can shift later pages. Large offsets also cost database work.
- Process-local JWKS caching doesn't coordinate across workers. Key rotation
  propagation, outage alerts, provider policy, and emergency key revocation need
  an operational design.
- There is no TLS termination, request-size/rate limiting, secret manager,
  retention policy, audit trail, or deployment configuration.
- Safe completion/error events aren't a full telemetry platform. Add
  access-controlled diagnostics without logging request data or credentials.
- These tokens represent users in one subject namespace. Multitenancy, approval
  workflows, idempotency, and administrative access aren't implemented.
- Review and restrict documentation exposure and ingress before deployment.
  Never expose the development private key or replace verified auth with a
  local bypass.
