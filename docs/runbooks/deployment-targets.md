# Trusted deployment targets

Each deployment Environment is selected by a reviewed immutable target manifest.
The manifest binds repository owner/repository IDs, the full-SHA reusable workflow,
Environment, account, Region, Terraform root, separate plan/apply roles, exact
state and native lock paths, Cell Contract checksum, and policy version. Consumer
workflow inputs may select a manifest reference only; they cannot override any
bound value.

Before `terraform init`, the trusted workflow runs the target preflight. It checks
the caller, account, Region, repository IDs, Environment, workflow SHA, manifest
checksum, root, role, state path, policy version, and Cell identity. A mismatch
returns a bounded failure code and must not read state or resources.

The workflow invokes the credential-free command before initialization:

```bash
python scripts/deployment_targets.py \
  --manifest "$REVIEWED_TARGET_MANIFEST" \
  --caller "$TRUSTED_CALLER_BINDING" \
  --authority "$AUTHORITATIVE_PLATFORM_BINDING" \
  --expected-manifest-sha256 "$REVIEWED_MANIFEST_SHA256"
```

The caller and authority binding files are produced by the protected deployment
workflow from the reviewed manifest and AWS/GitHub identity evidence. They must
not be generated from consumer workflow inputs. The root workflow must also
consume the returned backend values in its own `backend "s3"` configuration,
including `use_lockfile = true`; a module output cannot configure a caller's
Terraform backend after initialization.

In trusted mode, preflight additionally validates the GitHub claims, Cell
Contract checksum, and AWS account obtained directly from the runner's STS
`GetCallerIdentity` call. The account is never accepted as a workflow argument
or environment variable.

OIDC trust requires `aud=sts.amazonaws.com` and the complete immutable subject.
Plan and apply use separate short-lived roles with permissions boundaries. The
plan role is read-only; apply is limited to the manifest namespace and cannot
change IAM trust, boundaries, OIDC, backend controls, runtime tables, or unrelated
roles. No long-lived AWS keys are created or documented.

Identity rotation uses a reviewed bounded overlap: `validate_rotation` requires
the same target scope, a verified new manifest, and overlap no longer than 24
hours before the old subject is removed. Publish and verify the new
manifest/trust first, then remove the old subject. Rollback restores the last
reviewed identity; moving tags, wildcards, and destructive trust replacement are
not rollback mechanisms. Protected production Environments require reviewers,
self-review prevention, restricted refs, concurrency, and no administrator bypass.

## Trusted Terraform plans

The protected plan workflow must pin its reusable workflow and source commit, run
target preflight and credential-free repository validation first, and only then
run `terraform init -lockfile=readonly` and `terraform plan`. It must use the
manifest's plan role and committed provider/backend lock checksums; consumer
inputs cannot replace the root, state key, role, provider versions, or module
sources. A saved binary plan is accompanied by a SHA-256 checksum and bounded
metadata from `scripts/trusted_plan.py`.

Review output is a sanitized summary of lifecycle counts, bounded resource
addresses, categories, no-op status, and policy status. It must not contain plan
JSON values, variable values, credentials, raw logs, or state. The plan artifact
is retained only for the review window, addressed to the trusted reviewer, and
is never copied into the repository, a shared cache, or an untrusted pull
request artifact. A no-op plan still publishes metadata and policy/readiness
evidence.

If the source commit, workflow, target manifest, Cell checksum, lock checksum,
policy catalog, or protected environment changes after planning, invalidate the
plan and require a new preflight and plan. There is no plan-to-apply handoff:
apply starts from a separately approved immutable commit and independently
revalidates the target. Rollback disables plan/apply acceptance while retaining
review metadata and audit records; it does not delete or mutate Terraform state.

The `production-readiness` policy runs before report publication. Production
findings are blocking from the first release and contain only bounded codes,
stable addresses, evidence references, severity, and remediation. Exceptions
are single-resource, single-plan records bound to the policy version, target,
source revision, checksum, independent approver, compensating control, review
date, signature, and expiry. Wildcards, reuse, stale bindings, and
non-exemptible findings are rejected.
Malformed plan changes, unknown catalog categories, empty production plans,
unconditioned IAM delegation, wildcard IAM actions/resources, public IP
assignment, mutable schedule state, and unregistered jobs fail closed before
report publication. The policy artifact is retained with the bounded report.

## Protected production apply

The `production-approval-bundle.yml` workflow joins the fresh trusted plan with
independently produced approval, readiness, caller, Cell, and lock evidence.
It publishes a complete short-lived bundle only after exact checksums and
production readiness provenance pass. Production apply consumes that bundle
from the exact deployment commit. The
apply workflow uses a separate protected Environment and apply role, binds the
manifest, target, Cell Contract, lock files, policy result, readiness decision,
approval record, artifact expiry, and binary plan checksum, and uses
non-cancelling concurrency per account, Region, Environment, and root.

The mutation step runs only `terraform apply -input=false` against the approved
saved plan. It does not replan, refresh, accept variables or targets, or reuse a
prior-run or pull-request artifact. Apply failure or runner loss is terminal;
inspect state and locks, retain bounded failure evidence, and create a new fresh
plan for recovery. Rollback disables launch first where applicable and follows
the same policy, readiness, approval, target, and lock controls.

Emergency access is not a recovery shortcut: issue a time-bound, independently
approved emergency record, page the responsible responders immediately, retain
the actor/target/incident evidence, and complete the post-incident review before
closing the incident.

## Deployment identity and recovery evidence

Every protected apply must retain the sanitized Deployment Identity projection
and bind it to the source commit, workflow run, target manifest, plan/policy/
readiness checksums, CONFIG hash, schedule generation, and provider/backend
locks. Use the evidence projection for operational lookup; do not expose raw
plans, CONFIG, credentials, secret values, or unrestricted logs.

Apply results are terminal and distinguish success, failure, partial apply,
runner loss, cancellation, and lock conflict. A partial or failed result is
never rewritten as successful. Preserve stable resource addresses, bounded
errors, lock condition, lifecycle state, and output checksums.

Recovery starts by disabling launch and retiring or draining the affected
generation. Quarantine/reconcile in-flight evidence, select a known-good
compatible Deployment Identity, and create a fresh plan from actual state.
Run that plan through the normal target, policy, readiness, approval, OIDC,
concurrency, lock, and exact-plan controls. Never reuse a saved plan or delete
evidence as part of rollback.

Post-apply verification must record target identity, lifecycle acknowledgement,
schedule and expectation horizon, task revision/networking, logs, occurrence
processing, alarms, and alert routing as applicable. Launch remains disabled
until blocking checks and Job Owner application-compensation acknowledgements
are complete within the recovery objective.
