# Verification matrix

| Requirement | Inspect or execute |
| --- | --- |
| SABA-API-001 | Versioned routes, plural names, stable unique operation IDs |
| SABA-API-002 | Schemas, unknown fields, exact money, minimum/maximum values |
| SABA-API-003 | Problem Details type/status/media/headers and sanitized errors |
| SABA-API-004 | Default/max page, invalid bounds, authorized counts, ordering |
| SABA-API-005 | Prior/current contracts and explicit compatibility decisions |
| SABA-SEC-001 | Signature, issuer, audience, claims, expiry, algorithm tests |
| SABA-SEC-002 | 401/challenge versus 403 and OpenAPI scope declarations |
| SABA-SEC-003 | Cross-user get and list tests; owner cannot come from input |
| SABA-SEC-004 | Trusted key source, network bounds, refresh, no committed keys |
| SABA-OBS-001 | Accepted/rejected correlation IDs and propagation on errors |
| SABA-OBS-002 | Application and server logs omit bodies, credentials, queries |
| SABA-OBS-003 | Unexpected error remains 500 with safe diagnostic evidence |
| SABA-TEST-001 | Observable success and failure contract tests |
| SABA-TEST-002 | Negative identity/ownership matrix with isolated fixtures |
| SABA-TEST-003 | Checker rejects deliberately malformed contract fixtures |
| SABA-TEST-004 | Actual execution report and explicit gaps |
| SABA-PY-001 | Consumer architecture, schema and session reuse |
| SABA-PY-002 | Central error/auth/correlation helpers |
| SABA-PY-003 | Maintained crypto, safe transactions, exact monetary values |
| SABA-PY-004 | Locked dependencies and isolated test infrastructure |

Report: finding, severity, requirement, file/line, concrete failure, correction.
Keep unresolved business-policy questions separate from confirmed defects.
