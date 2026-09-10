# Adopt the package

## Repository maintainer

Install the APM release recorded in `.apm-version`. Select the Copilot target
explicitly so deployment does not vary with whichever clients happen to be
installed on the maintainer's machine.

Install the published package from your consumer repository:

```sh
apm install sabajamalian/saba-enterprise-api-builder#v0.1.0 --target copilot
```

Alternatively, declare the same dependency in the consumer manifest:

```yaml
name: payments-service
version: 0.1.0
targets: [copilot]
dependencies:
  apm:
    - sabajamalian/saba-enterprise-api-builder#v0.1.0
```

The reference selects the `v0.1.0` Git tag. APM pins its resolved commit and
content hashes in the consumer lockfile, independently of subsequent changes
to `main`. With the manifest in place, run:

```sh
apm install
apm audit --ci
git diff
```

Review and commit the manifest, generated lockfile, `.github/agents/`,
`.github/instructions/`, `.github/prompts/`, and `.agents/skills/` changes.
Ignore `apm_modules/`. Review collisions with existing instructions before
continuing; do not use `--force` to dismiss them.

The package contains no MCP servers, executable install hooks, identity-provider
configuration, or Python application dependencies. Installing it does not add
the reference application or its CI workflow to your service.

## Local package development

To evaluate uncommitted artifact changes, replace the remote dependency in the
consumer manifest with `../saba-enterprise-api-builder` and run `apm install`.
That example assumes the consumer and package checkout are sibling directories.
Adjust the path for your layout, keeping the package directory's name at the end.
Local dependency locks record local provenance; switch back to a reviewed
version tag or full commit pin before distributing the configuration to your team.

## Developer

Pull the repository and select Saba API Designer, Builder, or Reviewer in your
supported Copilot client. No APM installation is needed to consume committed
files. Use the repository's normal Python/application setup to run its checks.

Prompt files are an optional entry point in clients that support them. Agents
use shared tool aliases and do not depend on IDE-only handoffs. Actual client
discovery and supported artifact types can vary; consult GitHub's
[custom agent reference](https://docs.github.com/en/copilot/reference/custom-agents-configuration)
and APM's [target matrix](https://microsoft.github.io/apm/reference/targets-matrix/).

The designer produces a contract; the builder implements it; the reviewer
inspects evidence. Those roles are selectable independently and do not imply
automatic multi-agent execution.

## Consumer CI

Use the pinned APM version. Audit committed state before any install that could
reconcile it. Use `apm install --frozen` to require manifest/lockfile consistency;
it complements the on-disk audit rather than replacing it. Run the service's
own contract tests separately.

Organizations using APM policy must also protect policy sources, set explicit
policy-fetch failure behavior, and configure required checks. This package does
not discover or install a fictional Saba Enterprise organization policy.
The package's own local integrity checks are not an organizational allowlist.

## Updates and rollback

Change the consumer's version tag through a reviewed PR, run APM, inspect the
manifest, lockfile, and generated diff, and run the service checks. Published
version tags must not be moved; publish a new version for changes.
Reading a new instruction does
not automatically migrate existing application code; use the designer/builder
workflow for any required behavioral change.

Rollback restores the previously approved manifest, lockfile, and generated
artifacts together through a reviewed change. Inspect application changes
separately; a configuration rollback does not undo a database migration.
