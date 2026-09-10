# Saba Enterprise API Builder

Versioned AI artifacts for designing, implementing, and reviewing API endpoints
against a shared engineering standard.

Saba Enterprise is a hypothetical company. Its standards are concrete project
requirements, with a FastAPI purchase-request reference that exercises them.
They are not an actual organization's policies or a certification of production
readiness.

## Use the repository agents

Open this repository in a supported GitHub Copilot client and select:

| Agent | Use it for |
| --- | --- |
| **Saba API Designer** | Turn a request into an endpoint contract, access rules, and acceptance cases |
| **Saba API Builder** | Implement an agreed contract using existing FastAPI patterns and tests |
| **Saba API Reviewer** | Review a change against named requirements and report evidence gaps |

The generated agents, instructions, prompts, and skills are committed.
Developers don't need APM to use them. Copilot access and custom-agent support
are still required. The designer and reviewer have read-only tools; the builder
can edit files and execute checks.

Start with Saba API Designer:

> Design an endpoint for submitting a purchase request. Inspect the reference
> service first. Identify the request and response schemas, ownership and scope
> rules, safe errors, compatibility implications, and acceptance cases.

Then give the agreed contract to Saba API Builder. Review the resulting changes
with Saba API Reviewer and the executable API checks.

## What the package supplies

| Artifact | Responsibility |
| --- | --- |
| [API contract instructions](.apm/instructions/saba-api-contract.instructions.md) | Versioned routes, public schemas, bounded pagination, Problem Details, compatibility |
| [Security instructions](.apm/instructions/saba-api-security.instructions.md) | JWT verification, scopes, object ownership, trusted key sources |
| [Observability instructions](.apm/instructions/saba-api-observability.instructions.md) | Correlation IDs, structured logs, redaction, safe failures |
| [Testing instructions](.apm/instructions/saba-api-testing.instructions.md) | Contract coverage, negative identity cases, evidence reporting |
| [FastAPI profile](.apm/instructions/saba-fastapi.instructions.md) | Python implementation patterns and dependency boundaries |
| [Skills](.apm/skills/) | Endpoint design, FastAPI implementation, and verification procedures |
| [Prompts](.apm/prompts/) | Short task entry points for clients that support prompt files |

Requirements have stable IDs such as `SABA-SEC-003` for object-level
authorization. [The standards map](docs/standards.md) connects them to ownership,
implementation, tests, and manual review.

## Install into another repository

Repository maintainers use [Microsoft APM](https://github.com/microsoft/apm) to
install the package, review the generated files, and commit them for their team.
The package is a classic APM directory with `apm.yml` and `.apm/`.

For unpublished/local development, add this to a consumer's `apm.yml`:

```yaml
name: my-service
version: 0.1.0
targets: [copilot]
dependencies:
  apm:
    - ../saba-enterprise-api-builder
```

Run `apm install` from that consumer using the version in
[`.apm-version`](.apm-version). The local dependency path must point to this
checkout and end with its directory name.

After the package content is published, consumers can replace the local path
with `sabajamalian/saba-enterprise-api-builder#COMMIT_SHA`, substituting a full
published commit SHA. No release tag is assumed to exist. See
[adoption](docs/adoption.md) for installation, updates, and client boundaries.

## Run the reference API

The [reference service](reference-api/README.md) implements purchase-request
creation, retrieval, and listing with local SQLite persistence, verified JWT
identity, scope checks, and resource ownership. Its local identity helper
generates keys and tokens explicitly; the API has no token-issuance endpoint.

```sh
cd reference-api
uv sync --locked --python 3.12
uv run pytest
```

Use the reference README for startup and authenticated requests.

## Maintain the artifacts

Edit `.apm/`, then regenerate through the pinned APM CLI:

```sh
uv sync --locked --python 3.12
export APM_BIN="$(uv run python scripts/install_apm.py)"
uv run python scripts/artifacts.py --write
uv run python -m unittest discover -s tests -v
uv run python scripts/artifacts.py --check --consumer-test
```

The installer helper supports macOS/Linux arm64 and x86_64. It downloads an
official release and verifies its published checksum. Other platforms can
install the same APM release manually and set `APM_BIN`.

The synchronization helper invokes APM in an isolated project and copies only
its recorded projections. It refuses unreviewed edits to generated files and
unmanaged collisions. [Maintenance](docs/maintenance.md) explains the local
deployment ledger, source export, and release prerequisites.

## Enforcement boundaries

APM distributes and audits agent configuration. Instructions guide the agent.
The reference API enforces identity, access, and validation in application code;
its tests exercise those behaviors. Required CI checks and policy ownership
remain repository-administration responsibilities.

The [CI workflow](.github/workflows/ci.yml) separates artifact integrity from API
contract checks. It does not run an AI agent, require model credentials, deploy
infrastructure, or configure an organization's policy. A read-only review cannot
substitute for executed tests.

See [architecture](docs/architecture.md) for source ownership and the complete
design-to-review path.
