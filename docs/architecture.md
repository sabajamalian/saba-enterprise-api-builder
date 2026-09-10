# Architecture

The package carries shared engineering knowledge through design, implementation,
and review. The reference service makes selected requirements executable.

## Source ownership

| Location | Owner and purpose |
| --- | --- |
| `.apm/instructions/` | Domain owners maintain normative requirement definitions |
| `.apm/agents/` | Platform maintainers define role boundaries and allowed tools |
| `.apm/skills/` | Workflow owners maintain procedures and co-located references |
| `.apm/prompts/` | Maintainers provide short user entry points |
| `.github/agents`, `.github/instructions`, `.github/prompts`, `.agents/skills` | APM-generated, committed consumer-facing files |
| `apm.lock.yaml` | APM-generated local deployment ledger for this producer |
| `.github/apm-managed.json` | Synchronization inventory and hashes of generated files |
| `reference-api/` | Runnable FastAPI implementation with independent Python dependencies |
| `tests/` | Package authoring and synchronization safety checks |

The root manifest publishes a single classic APM package. `.apm/` is an explicit
include; the source export contains only `.apm/` and `apm.yml`. Skill references
are co-located so links still work in another repository.

## Projection and consumer path

`scripts/artifacts.py` copies the canonical source to a temporary producer
directory and invokes APM. APM parses and installs the actual primitives; the
helper does not reimplement its target mapping.

The helper compares APM's outputs against the committed inventory. On an
explicit write, it synchronizes the known generated files and APM's local
deployment ledger. Existing unrecorded files, modified projections, and symlinked
destinations are rejected. Unrelated files are preserved.

The consumer smoke check uses a different project directory and an actual APM
local dependency. It checks installation, frozen replay, preservation of an
existing team agent, and rejection of an edited managed agent during audit.
It exercises local-source portability. The published Git pin in
[adoption](adoption.md) also passed a separate remote installation, audit, and
frozen replay. Repeat that remote check when publishing a new consumer pin;
the local smoke check does not fetch GitHub.

## Endpoint workflow

The designer reads the existing service and produces a contract with SABA IDs.
The builder reuses the service's architecture, implements the contract, and runs
checks. The reviewer compares the contract, code, tests, and recorded results.
Unresolved business decisions remain explicit.

CI has independent artifact and reference API jobs. No model or agent executes
in these jobs, so artifact integrity and API behavior can be checked without
Copilot credentials.

## Boundaries

The reference service uses local SQLite persistence and generated development
identity fixtures. A deployed service needs decisions about provider trust,
database migrations, concurrency, telemetry destinations, operations, rate
limits, and infrastructure. The package does not provision those systems.
