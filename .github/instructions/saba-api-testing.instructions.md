---
applyTo: "**"
---

# Saba Enterprise API testing

Owner: Quality Engineering and API Architecture.

- **SABA-TEST-001:** For each changed endpoint, test success schemas/statuses,
  validation bounds, unknown fields, applicable failures, protocol headers,
  correlation, and OpenAPI operation/security/error declarations. Test stable
  list ordering and pagination boundaries. Assert observable behavior rather
  than implementation details.
- **SABA-TEST-002:** Test no token, invalid signature, wrong issuer/audience,
  expiry, wrong algorithm, missing claims, unknown key, insufficient scope,
  cross-user reads, and list isolation. Generate ephemeral test keys. Tests must
  not require external identity services or contain reusable credentials.
- **SABA-TEST-003:** Include negative control tests proving the contract checker
  rejects deliberately invalid responses. Separate application contract
  failures from APM configuration-integrity failures.
- **SABA-TEST-004:** Run the smallest relevant existing tests before completing
  a change. State exactly what ran and what remains unverified in the work
  report. A code review or an agent's assertion is not execution evidence.

Map requirement IDs to executable tests and manual checks. OpenAPI structural
checks do not establish complete backward compatibility; review contract diffs
and business semantics explicitly. Do not add new testing tools when the
consumer already has a suitable runner.
