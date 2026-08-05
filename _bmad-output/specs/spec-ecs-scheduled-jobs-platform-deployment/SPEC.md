---
id: SPEC-ecs-scheduled-jobs-platform-deployment
companions:
  - deployment-contract.md
  - ../../planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md
  - ../../planning-artifacts/prds/prd-demo-bmad-2026-07-13/prd.md
  - ../../planning-artifacts/prds/prd-demo-bmad-2026-07-13/addendum.md
  - ../../project-context.md
  - ../../../_bmad/custom/standards/aws-terraform-implementation.md
sources: []
---

# ECS Scheduled Jobs Platform Deployment

## Why

Platform Engineering needs a safe, repeatable way to demonstrate the existing ECS Scheduled Jobs Platform in a real AWS environment. The current repository has reusable Cell and job modules plus protected delivery building blocks, but its examples contain synthetic values and do not provide one coherent disposable deployment and teardown contract.

## Capabilities

- **CAP-1**
  - **intent:** Platform Engineering can deploy the account-local Platform Cell and one scheduled-job consumer into a disposable non-production AWS environment.
  - **success:** Cell and job ownership boundaries are respected, resources deploy to the approved target, and the schedule remains disabled until the exact Cell acknowledgement is accepted.

- **CAP-2**
  - **intent:** An operator can run one immutable-image ECS Fargate scheduled job through the supported Scheduler → Cell → ECS path.
  - **success:** A real occurrence launches, produces structured completion evidence, and exposes expected logs, alarms, retries, and DLQ behavior.

- **CAP-3**
  - **intent:** The deployment can obtain non-secret target configuration from protected GitHub Environment controls and sensitive values from an approved Infisical integration.
  - **success:** Authorized steps receive only scoped runtime secrets; plans, state, artifacts, logs, and evidence contain no secret values.

- **CAP-4**
  - **intent:** An authorized operator can validate, plan, approve, apply, verify, and record a deployment through a protected workflow.
  - **success:** Any source, target, role, lock, plan, acknowledgement, or readiness mismatch fails before mutation; a passing run records Deployment Identity and bounded verification evidence.

- **CAP-5**
  - **intent:** An authorized operator can destroy the disposable non-production deployment through a separate protected workflow.
  - **success:** Only the approved disposable target is removed after confirmation, approval, and evidence preservation; production, shared Cell resources, protected state, retained evidence, and prevent-destroy resources remain protected.

- **CAP-6**
  - **intent:** Operators can recover safely from failed or partial deployment, runtime, or teardown operations.
  - **success:** Failures produce bounded recovery guidance, mutations are not retried automatically, and a subsequent mutation requires fresh target, plan, lock, and approval validation.

## Constraints

- Preserve the account-local Cell architecture and existing `AD-1` through `AD-34`; Platform Engineering owns shared Cell state and application roots own job state.
- Use Terraform with committed provider locks, explicit validated interfaces, stable resource addresses, required ownership tags, encrypted state/data, private task networking, separate least-privilege IAM roles, bounded retries, logs, alarms, DLQs, runbooks, and rollback notes.
- Bind deployment to an immutable target manifest, protected GitHub Environment, GitHub OIDC, separate plan/apply authority, exact saved-plan apply, and full-SHA workflow/action references; long-lived AWS credentials are prohibited.
- GitHub Environment configuration is non-secret deployment control/configuration. Infisical uses a scoped OIDC-authenticated machine identity for sensitive values. Secret values never enter Terraform variables/state/plans, CONFIG, artifacts, logs, or evidence.
- Preserve the `RESERVED → PUBLISHED → VALIDATED → MATERIALIZED → ENABLED` handshake. Missing target identity, secret retrieval, lock, Cell acknowledgement, readiness, or verification evidence fails closed.
- The demonstration is disposable non-production. Production activation/destruction, arbitrary target selection, direct Scheduler-to-ECS bypass, `terraform_remote_state`, committed secrets/state/plans, mutable image tags, public task networking, and automatic broad cleanup are forbidden.
- AWS resources require least privilege, confused-deputy protections where supported, encryption at rest, explicit retention, required tags, and no unjustified wildcard IAM or public exposure.

## Non-goals

- Production activation or production destruction.
- A general multi-environment destroy service or automatic cleanup after failed deployment.
- Infisical project administration, secret creation, enterprise policy administration, or organization-wide secret migration.
- Replacing the existing Cell architecture, direct Scheduler-to-ECS execution, or the existing exact-plan production controls.

## Success signal

One disposable non-production AWS Environment provisions the Platform Cell and one scheduled-job consumer, proves at least one successful occurrence and one controlled failure/retry path, and publishes sanitized evidence for Cell publication, schedule state, ECS launch, completion, logs, alarms, retries, DLQ behavior, and teardown safety. A separate destroy run removes only the approved disposable consumer target without affecting shared Cell foundations or retained evidence.

## Assumptions

- The target Account, Region, backend, ECS cluster, ECR image digest, private network, GitHub Environments, OIDC roles, Cell prerequisites, and Infisical project/machine identity will be approved before implementation.
- Infisical is approved for the selected project/environment/path scope and supports GitHub OIDC machine-identity authentication.

## Open Questions

- Which Account, Region, backend, target manifest, GitHub Environment/reviewer set, OIDC subject, Infisical project/environment/path scope, and pilot job configuration are approved?
- Which Cell resources survive teardown, and what evidence/log retention is required before destroying the disposable consumer environment?
- Will Cell and job deployment use separate Terraform roots with an explicit dependency, or one coordinated root that still preserves separate ownership and state?
