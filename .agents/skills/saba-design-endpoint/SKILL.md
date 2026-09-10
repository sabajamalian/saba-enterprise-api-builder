---
name: saba-design-endpoint
description: Use when designing a new API endpoint or changing an API contract. Produces a Saba Enterprise contract and acceptance cases before implementation.
---

# Design an endpoint

Input: a feature request and the consuming repository. Output: a reviewable
endpoint contract, unresolved decisions, and an implementation brief.

1. Inspect the current route, schema, identity, storage, and test conventions.
2. Read the installed `saba-api-contract`, `saba-api-security`,
   `saba-api-observability`, and `saba-api-testing` instructions by name.
3. Identify the caller, resource owner, required scopes, and data sensitivity.
   Ask when business intent or authorization policy is ambiguous.
4. Fill the [contract template](references/contract-template.md). Map each
   acceptance case to a SABA requirement and an executable or manual check.
5. Identify compatibility changes and obtain a decision before implementation.

Do not invent an identity bypass or relax standards to fit a sample. Report
missing repository context or contradictory requirements as blockers. This skill
does not need network access or credentials.
