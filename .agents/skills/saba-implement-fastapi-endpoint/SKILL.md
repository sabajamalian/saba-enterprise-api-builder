---
name: saba-implement-fastapi-endpoint
description: Use when implementing or modifying a FastAPI endpoint from an agreed contract under Saba Enterprise standards.
---

# Implement a FastAPI endpoint

Inputs: an agreed endpoint contract and the consuming repository. Output: a
focused implementation, contract tests, and an evidence report.

1. Read installed Saba API instructions and the FastAPI profile by name. Inspect
   existing routers, schemas, app factory, identity, database, and tests.
2. Check the contract has scope, ownership, bounds, failures, and compatibility
   decisions. Stop on missing business rules.
3. Follow the [implementation checklist](references/implementation-checklist.md).
   Reuse helpers and preserve consumer architecture.
4. Use `saba-verify-api` for validation. Run existing targeted commands and
   report their actual results.

Do not provision services, install MCP servers, copy credentials, change access
policy, or disable authentication. A missing dependency is a setup issue to
surface and resolve explicitly, not a reason to skip validation silently.
