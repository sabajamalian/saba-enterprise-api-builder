---
name: saba-verify-api
description: Use when testing or reviewing an API change against Saba Enterprise contract, identity, observability, and compatibility requirements.
---

# Verify an API

Inputs: endpoint contract, changed implementation, tests, and available execution
results. Output: requirement-to-evidence coverage and actionable findings.

Read the installed Saba API instructions and use the
[verification matrix](references/verification-matrix.md).

For a builder with execution permission, run existing targeted checks and inspect
their output. For a read-only reviewer, inspect code and recorded CI results;
request execution when evidence is missing. Do not exceed the invoking agent's
tool permissions.

Classify each requirement as supported by executable evidence, manual review,
failed, or unverified. Include file/line or test-result references. A passing APM
audit establishes configuration checks only; it cannot prove the endpoint
validates identity, preserves compatibility, or avoids leaking data.

Do not "fix" a failing assertion by weakening the requirement. Explain the
failure case and seek a reviewed exception or implementation correction.
