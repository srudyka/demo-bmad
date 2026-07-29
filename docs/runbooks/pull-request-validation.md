# Credential-Free Pull Request Validation

The pull-request workflow in `.github/workflows/validate.yml` runs
`scripts/validate.sh` on the `pull_request` event. It has no AWS credentials,
protected Environment secrets, OIDC permission, or write-capable token. The
workflow uses full-SHA Action pins and the repository-pinned Terraform, Python,
and uv versions.

## Target discovery

For a pull request, `VALIDATION_BASE_SHA` is set to the base commit. The
validator reports every changed path and its owned validation target. The
inventory covers Terraform, runtime, contracts, tests, workflow policy,
dependencies, documentation, and generated references. An unknown path is
reported and selects the conservative safety suite; it is never silently
ignored. Local runs without `VALIDATION_BASE_SHA` intentionally run the full
repository suite.

To reproduce the inventory locally:

```bash
VALIDATION_BASE_SHA=<base-sha> ./scripts/validate.sh
```

To reproduce a named failure, use the stage and target printed by the
validator. Terraform checks use backend-free initialization and the committed
provider lock; they do not read protected state.

## Safety and artifact rules

Credentials, state, saved plans, `.terraform/`, committed `.tfvars`, private
keys, mutable production references, routine provisioners, `null_resource`,
and ungoverned workflow/action references block validation in every
Environment. Logs and test results must contain only bounded, non-secret
diagnostics. Do not upload raw plans, CONFIG, environment dumps, credentials,
or executable content from an untrusted pull request.

The current AWS provider deprecation warnings are documented in the platform
README and remain non-blocking modernization work. They must not be hidden by
weakening provider, lock, or Terraform validation.

## Rollback and staged policy

Trusted plans run the versioned `production-readiness` policy before any bounded
report or artifact is published. Findings contain only stable addresses, policy
codes, bounded evidence references, severity, and remediation; raw plan values,
credentials, and secrets are never retained. Production findings block from the
first release. An exception must bind one policy/resource, environment, source
revision, plan checksum, owner, independent approver, compensating control,
review date, signature, and expiry. Wildcards, reuse, stale bindings, and
non-exemptible controls are rejected. To roll back a policy release, disable
trusted-plan publication and restore the last reviewed policy bundle while
preserving the decision and approval evidence.

The retained report includes the policy/catalog versions, binary plan checksum,
evaluation timestamp, and bounded findings. The separate policy artifact is
published alongside the report so reviewers can inspect remediation evidence
without receiving raw plan values.

If validation policy causes an operational problem, restore the prior reviewed
validator/workflow revision and preserve the existing validation evidence.

Production approval is a separate protected workflow. Pull-request plans and
prior-run plans are review artifacts only and cannot be promoted. The protected
apply job checks out the exact deployment commit, verifies exact binary-plan and
readiness/approval bindings, uses a separate apply role, and never retries a
partial Terraform mutation automatically. Production activation remains blocked
until the later readiness story supplies real production evidence.
Rollback must not grant cloud credentials, bypass required checks, or delete
failure artifacts needed for investigation.

Policy findings use the versioned rollout catalog. Credential exposure,
invalid Terraform, formatting failures, and prohibited repository artifacts are
always blocking. Only explicitly catalogued governance findings may be
advisory, and production-equivalent controls must not inherit advisory status
from a lower Environment.
