# Implementation checklist

## Before coding

- Locate the app factory and existing authentication, errors, and session helpers.
- Map the contract to SABA-API, SABA-SEC, SABA-OBS, and SABA-TEST requirements.
- Identify any required schema migration and compatibility decision.

## Change

- Add bounded request schemas and explicit public responses.
- Declare stable operation IDs, errors, and security scopes in OpenAPI.
- Resolve ownership from verified identity and filter queries before pagination.
- Use shared Problem Details handlers and correlation propagation.
- Preserve HTTP headers and do not return raw input in validation errors.
- Keep monetary calculations exact and database access parameterized.
- Add request-completion logs without business data or query strings.

## Finish

- Add success, boundary, scope, ownership, and error tests.
- Inspect behavior for malformed input and unexpected exceptions.
- Update contract documentation and run the targeted consumer checks.
- Report evidence and blockers; never assert a result that was not observed.
