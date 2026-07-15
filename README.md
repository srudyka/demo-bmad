# demo-bmad

## BMAD Customization

Team-level BMAD overrides live in `_bmad/custom/`. The AWS Terraform
implementation contract is captured in
`_bmad/custom/standards/aws-terraform-implementation.md` and is loaded by the
BMAD spec, story creation, implementation, code review, readiness, and
developer-agent workflows.

Use this standard to keep AI-generated Terraform implementations consistent
across branches. If an implementation intentionally deviates from the standard,
document the reason in the story or PR notes.

## Platform Bootstrap

This repository is the implementation home for the ECS scheduled jobs platform.
The bootstrap establishes ownership boundaries, reproducible tooling, and
credential-free validation. It intentionally creates no AWS resources.

The Platform Cell module owns shared resources for one AWS account and Region.
The scheduled-job module owns per-job resources. Later stories add behavior;
neither module may read the other root's Terraform state or mutate resources
owned by the other module.

## Prerequisites

- Terraform compatible with `>= 1.10, < 2.0` (tested seed: 1.15.8)
- Python compatible with `>= 3.14, < 3.15` (tested seed: 3.14.6)
- uv 0.11.28
- Network access to the Terraform registry and Python package index, or approved
  internal mirrors containing the locked dependencies

No AWS credentials are required or passed to validation subprocesses.

## Repository Layout

```text
modules/
  ecs-scheduled-job-platform/  # shared account/Region Cell ownership
  ecs-scheduled-job/           # per-job resource ownership
runtime/                       # seven typed Cell runtime package boundaries
contracts/                     # normative compatibility package boundary
tests/
  contract/                    # repository and interface contracts
  integration/                 # credential-free component checks
  hygiene/                     # positive/negative policy fixtures
docs/runbooks/                 # stable operator Runbook location
scripts/                       # shared local/CI validation and hygiene tooling
```

Each Terraform module has a resource-free `examples/basic/` root. Production
examples, environment roots, AWS resources, runtime behavior, and compatibility
schemas are introduced only by their owning stories.

## Validation

Run the same command used by the GitHub `pull_request` workflow:

```bash
./scripts/validate.sh
```

It verifies the uv lock, installs dependencies outside the checkout by default,
reports the resolved toolchain, checks Terraform/Python formatting, initializes
and validates every discovered Terraform root without a backend, runs Ruff,
strict mypy, pytest, Checkov, and repository hygiene, and removes its temporary
Python, cache, and Terraform data. Failures include the exact module, example,
package, suite, or policy.

The wrapper removes ambient AWS credentials and tool override variables before
dependency setup. AWS shared configuration and instance metadata discovery are
disabled for every validation subprocess. Run approved mirror configuration
through the repository tool configuration rather than ambient test or Terraform
CLI argument variables.

Validation never plans, applies, accesses protected state, or creates a
deployment artifact. `terraform validate` proves configuration consistency; it
does not prove AWS API access or deployed behavior.

## Tested Toolchain

| Tool | Bootstrap seed | Compatibility contract |
| --- | --- | --- |
| Terraform | 1.15.8 | `>= 1.10, < 2.0` |
| AWS provider | 6.54.0 | `>= 6.0, < 7.0` |
| Python | 3.14.6 | `>= 3.14, < 3.15` |
| uv | 0.11.28 | exact repository tool pin |
| Checkov | 3.3.8 | exact direct dependency |
| mypy | 2.3.0 | exact direct dependency |
| pytest | 9.1.1 | exact direct dependency |
| Ruff | 0.15.21 | exact direct dependency |

The Terraform, AWS provider, and Python entries are dated validation seeds, not
permanent patch constraints. CI and `uv.lock` make the currently tested set
reproducible.

## Provider Lock Updates

Each module and module-local example owns its `.terraform.lock.hcl`; do not copy
locks between roots. A reusable module's validation lock does not replace the
consumer root's lock.

To qualify a provider update, run `terraform init -backend=false -upgrade`
independently in both module directories and both `examples/basic/` directories.
Review every lock diff, confirm all four roots resolve the same approved provider
version, then run `./scripts/validate.sh`. Normal validation uses
`-lockfile=readonly` and fails rather than changing a lock.

## Contribution Contract

- Keep Terraform resource addresses stable. An intentional address change must
  include reviewed `moved` blocks or explicit migration guidance and rollback
  notes.
- Do not use routine provisioners, `null_resource`, cross-repository
  `terraform_remote_state`, mutable production references such as `latest`, or
  hardcoded deployment identity.
- Keep account IDs, Regions, Environments, ARNs, repository IDs, credentials,
  and secret values outside reusable modules and runtime defaults.
- Commit provider and Python locks. Never commit `.tfvars`, state, saved plans,
  `.terraform/`, local configuration, credentials, keys, or generated secrets.
- Pin repository Actions to full commit SHAs and container Actions to image
  digests, including references inside local composite Actions.
- Document any standards deviation in the story and PR with its scope, reason,
  reviewer, risk, and rollback. Undocumented deviations fail review.

## Security Boundary

The baseline workflow is credential-free and has only `contents: read`. It uses
the unprivileged `pull_request` event and full-SHA Action references. It does not
request OIDC, read secrets or protected state, select a deployment Environment,
transfer executable artifacts to privileged jobs, plan, or apply.

Trusted planning, OIDC role binding, approval, and production apply are later
delivery capabilities. Do not extend the baseline workflow with privileges.

## Troubleshooting

- `terraform:<path>:init`: confirm registry or approved mirror access and that
  the root-local provider lock is current.
- `terraform:<path>:validate`: fix the named root; this does not require AWS
  credentials.
- `python:*` or `tests:*`: run the reported uv-managed tool directly with
  `uv run --locked` for focused output.
- `security:terraform`: address the Checkov finding or document an approved,
  narrowly scoped standards deviation.
- `repository:hygiene`: remove the named prohibited artifact or pattern. Do not
  bypass the check with force-add or an ignore rule.

## Rollback

Story 1.1 is repository-only and creates no AWS resources, state, plans, or
deployment artifacts. Roll back with a normal version-control revert of the
bootstrap files, restore the previous `README.md` and `.gitignore`, and rerun the
checks that existed before the seed. Do not run `terraform destroy`, edit a
backend, or perform an AWS operation.
