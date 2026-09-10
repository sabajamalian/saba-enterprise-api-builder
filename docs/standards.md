# Saba Enterprise API standards

These are the package's hypothetical company standards. Normative definitions
live in `.apm/instructions/`; generated Copilot instructions are projections.
Numbers such as the pagination maximum are design decisions recorded in those
definitions, not measured performance claims.

## Requirement ownership and evidence

| Requirement | Owner | Implementation/check | Remaining review |
| --- | --- | --- | --- |
| SABA-API-001 | API Architecture | Reference routes and OpenAPI tests | Resource naming and intended API shape |
| SABA-API-002 | API Architecture | Request/response models and boundary tests | Business validation completeness |
| SABA-API-003 | API Architecture | Shared error handlers and Problem Details assertions | Suitability of problem types/details |
| SABA-API-004 | API Architecture | Authorized list query and pagination tests | Ordering semantics for changing datasets |
| SABA-API-005 | API Architecture | OpenAPI structural checks | Full backward-compatibility review against the previous contract |
| SABA-SEC-001 | Identity | JWT verifier and negative token tests | Issuer/audience configuration and provider trust |
| SABA-SEC-002 | Identity | Scope dependencies and 401/403/OpenAPI tests | Correct business permissions |
| SABA-SEC-003 | Application Security | Owner-filtered get/list and cross-user tests | Business visibility rules |
| SABA-SEC-004 | Identity | Key-source configuration, cache/refresh tests, local key utility | Production provider operations and secret management |
| SABA-OBS-001 | SRE | Correlation middleware and propagation tests | Cross-service propagation |
| SABA-OBS-002 | SRE | Safe request-completion logging and log-capture tests | Proxy/server logs, retention, and telemetry destinations |
| SABA-OBS-003 | SRE | Safe unexpected-error boundary and 500 tests | Incident response and alerting |
| SABA-TEST-001 | Quality Engineering | Reference pytest/HTTPX API contracts | Business case coverage |
| SABA-TEST-002 | Quality Engineering | Isolated keys/database and negative identity matrix | Additional provider-specific cases |
| SABA-TEST-003 | Quality Engineering | Deliberately invalid contract fixture rejected by checker | Whether each new requirement has an effective check |
| SABA-TEST-004 | Quality Engineering | CI result and builder execution report | Results are current for the reviewed commit |
| SABA-PY-001 | Python Platform | App factory, models, and dependency injection | Fit with the consuming service |
| SABA-PY-002 | Python Platform | Shared identity/error/correlation helpers | Avoiding duplicated implementations |
| SABA-PY-003 | Python Platform | JWT library, sessions, Decimal values, persistence tests | Production database/migration behavior |
| SABA-PY-004 | Python Platform | uv lockfile and isolated pytest fixtures | Dependency-update review |

Executable coverage lives under [reference-api/tests](../reference-api/tests/).
The [API contract tests](../reference-api/tests/test_api.py) exercise schemas,
ownership, persistence, pagination, and OpenAPI. [Token tests](../reference-api/tests/test_auth.py)
and [JWKS tests](../reference-api/tests/test_jwks.py) exercise identity rejection,
rotation, bounded retrieval, and outages. [Observability tests](../reference-api/tests/test_observability.py)
exercise redaction, correlation, safe failures, and invalid contract fixtures.
[Configuration and development-identity tests](../reference-api/tests/test_settings_dev.py)
cover startup failures and local key/token behavior.

The [installed verification matrix](../.apm/skills/saba-verify-api/references/verification-matrix.md)
travels with the package so reviewers in other repositories have the same IDs.

## Applying standards to an existing service

Inspect the consumer's current contract and architecture first. A new service
uses the defaults directly. An existing incompatible convention needs a
deliberate migration decision. The builder must not silently rename existing
routes or change a caller's accepted values.

An exception records the requirement, reason, affected endpoints, risk owner,
compensating control, and review condition. It does not change the shared
baseline unless its owner approves a package change. Instructions cannot stop a
developer or another agent from ignoring an exception process; code review and
repository policy must make that process authoritative.

## Guidance, package checks, and runtime controls

| Layer | What it establishes |
| --- | --- |
| AI artifacts | The context and procedure supplied to Copilot |
| APM and projection checks | What was installed, whether managed bytes drifted, and whether regeneration matches source |
| API contract tests | The implemented behavior exercised by the test cases |
| Runtime code | Request validation, token verification, authorization, and error handling |
| Repository/organization controls | Required checks, reviewer ownership, approved sources, and release authority |

No layer here establishes legal compliance, exhaustive security assurance, or
production readiness by itself.
