---
applyTo: "**/*.py,**/pyproject.toml"
---

# Saba Enterprise FastAPI profile

Owner: Python Platform. Apply when implementing a FastAPI API. Language-neutral
SABA-API, SABA-SEC, SABA-OBS, and SABA-TEST requirements remain authoritative.

- **SABA-PY-001:** Reuse the consumer's app factory, settings, routers,
  dependencies, and persistence conventions. Use Pydantic request models with
  explicit bounds and forbidden extras, separate public response models, and
  dependency-injected authentication and database sessions.
- **SABA-PY-002:** Keep authentication, authorization, errors, and correlation
  handling in shared helpers. Install centralized exception handlers for
  validation and HTTP errors. Unexpected exceptions require a narrow application
  boundary that logs safely and returns a genuine 500.
- **SABA-PY-003:** Use a maintained JWT library and vetted crypto implementation.
  Use SQLAlchemy parameterized queries and request-scoped sessions; roll back
  failed transactions and close resources. Represent money with Decimal or
  integer minor units according to the contract.
- **SABA-PY-004:** Use pytest and HTTPX/FastAPI test clients where compatible
  with the consumer toolchain. Isolate databases and keys per test fixture.
  Lock application dependencies with the consumer's package manager; APM
  manages AI artifacts, not Python dependencies.

The package's purchase-request reference is an implementation example. Do not
copy its SQLite deployment assumptions, local issuer, or business fields into
another service without a decision.
