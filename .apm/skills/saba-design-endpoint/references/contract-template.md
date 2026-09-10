# Endpoint contract

## Request and outcome

Describe the business operation, actor, and resulting state. List unresolved
decisions separately.

## HTTP contract

Method, `/api/v1/...` path, stable operation ID, request schema and bounds,
public response schema, success status, and response headers.

## Identity and access

Trusted issuer/audience configuration, required scopes, resource ownership rule,
and how list queries restrict results before pagination.

## Failures

For each applicable failure: condition, status, problem type, safe detail,
correlation ID, and protocol headers. Include invalid input, missing/invalid
identity, insufficient scope, inaccessible resources, and internal failures.

## Lists

Default and maximum page size, invalid-value behavior, stable ordering and
tie-breaker, and offset/cursor behavior.

## Evidence

Map SABA requirement IDs to test cases and manual review. Specify log fields,
redaction expectations, compatibility impact, and any approved exception.

## Implementation brief

Affected modules, reusable helpers, migration needs, and acceptance cases.
