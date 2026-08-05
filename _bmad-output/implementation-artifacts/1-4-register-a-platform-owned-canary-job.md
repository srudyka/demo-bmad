---
baseline_commit: 51bca7d70d384c1fa5052a9abebab261254a5757
---

# Story 1.4: Register a Platform-Owned Canary Job

Status: done

## Story

As a Platform On-call Engineer,
I want a low-risk platform-owned canary registered with the Cell before runtime
processing is built,
so that every later delivery, launch, completion, alert, and recovery capability
has a concrete end-to-end acceptance fixture.

## Acceptance Criteria

1. **Given** a disposable non-production account-Region Cell and approved existing ECS cluster, private subnets, security groups, and immutable canary image digest
   **When** the canary fixture root is planned
   **Then** it creates only canary-owned task, IAM, logging, schedule, CONFIG, and test-notification resources outside customer workloads
   **And** account, Region, cluster, network, image, and ownership values are explicit inputs rather than repository defaults.

2. **Given** the canary needs a canonical identity
   **When** the platform Cell declares its bootstrap reservation
   **Then** the namespace registry records the canary job ID with its fixture repository/root, apply identity, account, Region, Environment, owner, and ownership generation
   **And** the declaration is Cell-owned, identity-validated, and protected from normal Terraform replacement; atomic conflicting-claim detection remains a later Registrar capability.

3. **Given** later launch-role trust requires a stable Process Manager identity
   **When** the canary foundation is applied
   **Then** the Cell creates the boundary-constrained stable Process Manager role shell for the Cell major with no ECS launch authority yet
   **And** creating this identity early is documented as the stable-principal exception required to bind the canary launch-role trust without later replacement.

4. **Given** the canary task resources are created
   **When** IAM and task-definition configuration are inspected
   **Then** job-launch, ECS execution, and application task roles are separate; the image is immutable; CPU and memory are explicit; logs have bounded retention; and application permissions are empty by default
   **And** trust policies use exact service principals, source-account/source-resource conditions where supported, permissions boundaries, and no unjustified wildcard authority.

5. **Given** Scheduler launch evidence needs its first concrete destination
   **When** the canary schedule is created
   **Then** the Cell owns an encrypted Scheduler source queue and DLQ, while the canary root owns a disabled recurring schedule and a delivery role scoped to those exact queues with source-account and schedule-group protections
   **And** retry attempts, maximum event age, disabled flexible window, time zone, future activation anchor, and canonical scheduled-time payload are explicit.

6. **Given** all canary launch inputs are known
   **When** the fixture publishes CONFIG
   **Then** it writes one secret-free, best-effort content-addressed candidate to the canary's exact S3 inbox prefix containing task revision, cluster, private networking, roles, schedule generation, runtime deadline, log group, test notification metadata, and Deployment Identity
   **And** the lifecycle remains `PUBLISHED` with launch disabled until later Cell validation and materialization succeed.

7. **Given** the canary needs a safe alert destination
   **When** fixture notification resources are created
   **Then** they use a non-production test sink that records delivery evidence without contacting production on-call or customer integrations
   **And** the sink ARN is registered as canary metadata without granting arbitrary publish access.

8. **Given** the canary schedule remains disabled
   **When** the fixture is applied and validated
   **Then** no ECS task launches and no occurrence is falsely reported as successful
   **And** outputs expose the canary job ID, ownership generation, task revision, role identities, log group, schedule ARN, CONFIG hash, source queue, notification sink, and current lifecycle state without secret values.

9. **Given** canary fixture security tests run
   **When** unauthorized repository, stale role, wrong account, public subnet, public IP, mutable image, cross-prefix CONFIG write, broad `PassRole`, or direct ledger write is attempted
   **Then** every attempt fails before launch
   **And** the compliant fixture passes module validation and can be destroyed without deleting shared Cell registration or CONFIG evidence required by investigation.

## Tasks / Subtasks

- [x] 1. Resolve the two phase-one design blockers before adding resources (AC: 2, 6, 9)
  - [x] Confirm AWS provider 6.54.0 cannot publish a Terraform-managed `aws_s3_object` with the required `If-None-Match: *` precondition, then document the smallest reviewed, role-scoped best-effort compatibility exception. Do not add a broad bucket-policy exception or an imperative provisioner.
  - [x] Define the narrow Cell-controlled canary reservation declaration required before the general Registrar in Story 2.1 exists. It uses the Story 1.3 key/item shapes, preserves Cell ownership, and blocks ordinary Terraform replacement; the canary root never writes the namespace table directly.
  - [x] Record the selected mechanisms, failure modes, validation proof, and safe cleanup boundary in the canary README and story Dev Agent Record before implementation proceeds.

- [x] 2. Add Cell-owned canary prerequisites without creating runtime processing (AC: 2, 3, 5, 9)
  - [x] Extend `modules/ecs-scheduled-job-platform/` for the platform-controlled canary reservation declaration, a stable Cell-major Process Manager role shell, Scheduler schedule group, encrypted Scheduler source SQS queue/DLQ, and exact resource policies only.
  - [x] The Process Manager role shell is trusted only by `lambda.amazonaws.com`, carries the supplied permissions boundary, uses a stable Cell-major name/path, and has no `ecs:RunTask`, `iam:PassRole`, ledger, CONFIG-registry, queue-consumption, Lambda, or self-modifying authority.
  - [x] Create standard KMS-encrypted queues with 14-day retention, DLQ redrive `maxReceiveCount >= 5`, and no public policy. Bind Scheduler send permission to `scheduler.amazonaws.com`, exact Cell account, and exact schedule-group ARN. Do not create a normalizer, canonical ingress, processor, ledger, alert, ECS-event, or log queue.
  - [x] Publish actual new Cell-owned ARNs in the existing SSM Cell Contract only after extending the checked-in contract fixture/schema tests, checksum, ownership catalog, manifest/release/migration evidence as required. Preserve the canonical path, Cell identity, and prior integrations.

- [x] 3. Create the isolated, non-production canary fixture root (AC: 1, 4, 5, 7, 8)
  - [x] Add `fixtures/canary/{main,variables,outputs,versions}.tf`, README, and a lock file containing macOS ARM and Linux AMD64 provider hashes. It is a separate backend-free Terraform root with clearly fictitious, non-secret validation values and no state/backend/provider credentials.
  - [x] Keep `modules/ecs-scheduled-job/` resource-free in this story. The canary fixture is a platform-owned exception, not the public generic job module interface introduced by Epic 2.
  - [x] Require explicit account, Region, Cell Contract/resource identifiers, fixture repository/root/apply identity, owner, job ID, ownership generation, ECS cluster, private subnet IDs, security-group IDs, immutable image digest, CPU/memory, schedule settings, KMS/boundary ARNs, and notification sink metadata. Do not provide deployment identity defaults.
  - [x] Consume Cell outputs/SSM discovery only as inputs; never use `terraform_remote_state`, an account-hiding provider alias, or a job-root mutation of Cell resources.

- [x] 4. Provision task, logging, and roles with narrow authority (AC: 1, 3, 4, 8, 9)
  - [x] Create distinct launch, ECS execution, and application task roles. Launch trust is the exact stable Process Manager role; execution/task trust is only `ecs-tasks.amazonaws.com`. Apply the supplied permissions boundary to every role.
  - [x] Keep the application task policy empty by default. The execution role is limited to the exact image/log resources and explicitly introduced approved secret references. Launch `iam:PassRole` is limited to the exact task/execution role ARNs with `iam:PassedToService = ecs-tasks.amazonaws.com`; do not grant `RunTask` yet.
  - [x] Create a Fargate task definition with `awsvpc`, explicit supported CPU/memory, immutable `repository@sha256:<64 lowercase hex>` image, no plaintext secrets, and required tags. Create a KMS-encrypted CloudWatch log group with explicit bounded retention and secret-free structured completion contract configuration.
  - [x] Require nonempty private subnet/security-group inputs and `assign_public_ip = "DISABLED"`. Document the required NAT or approved VPC endpoints for image pulls, logs, secrets, and workload dependencies.

- [x] 5. Create the disabled Scheduler evidence path and safe notification sink (AC: 5, 7, 8, 9)
  - [x] Create a disabled recurring EventBridge Scheduler schedule that targets the Cell Scheduler source queue, never ECS. Use `OFF` flexible time window, explicit IANA time zone, future activation anchor, bounded retry/maximum event age, DLQ, and a secret-free payload including the literal Scheduler scheduled-time context.
  - [x] Create the Scheduler delivery role trusted by `scheduler.amazonaws.com` with exact source-account/schedule-group protections where supported. Its authority is exact `sqs:SendMessage` to the Cell source/DLQ only; it cannot call ECS or publish arbitrary messages.
  - [x] Create an encrypted non-production test notification sink that records evidence without subscriptions to production on-call or customer systems. Any publisher permission is limited to that exact sink; the sink ARN is CONFIG metadata only. Do not add alert routing or alarms.
  - [x] Assert phase-one behavior: schedule is disabled; it creates no ECS task, occurrence, success signal, or runtime state.

- [x] 6. Publish exactly one `PUBLISHED` CONFIG candidate (AC: 1, 6, 8, 9)
  - [x] Construct a secret-free CONFIG body with actual task revision, cluster, private network, role ARNs, schedule generation, completion/runtime deadline, log group, test notification metadata, ownership generation, and schema-valid Deployment Identity.
  - [x] Reuse strict local schema/JCS helpers to validate `config.schema.json` and `deployment-identity.schema.json`, calculate `config_version`, and publish only `jobs/<job_id>/config/<config_version>.json`. Require the registration-derived job principal tag and conditional write behavior already enforced by the Cell bucket policy.
  - [x] Record lifecycle state `PUBLISHED` only. Do not write the CONFIG registry, ledger, acknowledgement/horizon, materialized expectations, task events, completion, `VALIDATED`, `MATERIALIZED`, or `ENABLED` state.
  - [x] Expose only secret-free job ID, generation, task revision, role ARNs/RoleIds, log group, schedule ARN, CONFIG hash, Scheduler source/DLQ, notification sink, and `PUBLISHED` lifecycle output.

- [x] 7. Add local proof, documentation, and safe teardown coverage (AC: 1-9)
  - [x] Add deterministic declaration and input-validation tests for the permitted Cell-owned bootstrap shape and wrong account/Region rejection. Keep atomic registration conflict/retry semantics deferred to the general Registrar and add no AWS-dependent test path.
  - [x] Add static/contract/IAM-negative tests for queue encryption/retention/redrive/policies, Process Manager shell without launch authority, three-role separation/boundaries, exact trust and `PassRole`, private network, immutable image, logs retention, disabled schedule/source-queue target, CONFIG schema/hash/key/lifecycle, safe test sink, and secret-free outputs.
  - [x] Reject every AC 9 condition, including direct ledger/registry writes and fixture destruction that targets Cell-owned registration, CONFIG evidence, inbox, registry, or queues. Do not claim a live task run or Scheduler delivery without recorded disposable-account evidence.
  - [x] Update module/fixture README and `docs/runbooks/README.md` with ownership, prerequisites, schedule-disabled/no-runtime behavior, CONFIG writer requirement, retained evidence, rollback, and teardown. Update structure/documentation tests narrowly.

- [x] 8. Run full credential-free validation (AC: 1-9)
  - [x] Run `terraform fmt -check -recursive`, backend-free locked init/validate for every discovered root including `fixtures/canary`, Ruff format/check, mypy, tests, Checkov, hygiene, `./scripts/validate.sh`, and `git diff --check`.
  - [x] Preserve credential scrubbing, temporary `TF_DATA_DIR`, `-backend=false`, `-lockfile=readonly`, dynamic root discovery, and the narrow Cell-only Checkov exception. Do not regenerate existing locks casually.

### Review Findings

- [x] [Review][Patch] Align Story 1.4 and documentation to the selected best-effort declarative reservation scope [modules/ecs-scheduled-job-platform/main.tf:367]
- [x] [Review][Patch] Align Story 1.4 and documentation to the selected best-effort content-addressed CONFIG publication scope [modules/ecs-scheduled-job-platform/main.tf:157]
- [x] [Review][Patch] Generate the canonical schedule generation hash [fixtures/canary/main.tf:46]
- [x] [Review][Patch] Remove unsupported CONFIG publisher session tags or authorize tightly scoped `sts:TagSession` [fixtures/canary/main.tf:15]
- [x] [Review][Patch] Publish all fixture-required Cell identifiers through the Cell Contract and update fixture/checksum/release evidence [modules/ecs-scheduled-job-platform/main.tf:211]
- [x] [Review][Patch] Bind and validate fixture and reservation identity against the same Cell, account, Region, environment, application, and job prefix [modules/ecs-scheduled-job-platform/variables.tf:139]
- [x] [Review][Patch] Use a durable non-production notification evidence sink [fixtures/canary/main.tf:280]
- [x] [Review][Patch] Validate Scheduler bounds, CloudWatch retention enum, and ECR image/repository consistency before apply [fixtures/canary/variables.tf:156]
- [x] [Review][Patch] Apply the Cell KMS Region guard to the Scheduler queues [modules/ecs-scheduled-job-platform/main.tf:461]

## Dev Notes

### Scope And Sequencing

This is a platform-owned, disposable non-production fixture. It establishes a
real task/schedule/CONFIG shape for later stories but deliberately does not
launch it. Story 1.5 consumes the Scheduler source queue; Story 1.6 validates
and materializes CONFIG; later stories own the ledger, ECS launch, evidence,
completion, deadlines, alerts, and recovery.

The worktree contains reviewed, uncommitted Story 1.3 changes. Preserve that
baseline, especially no premature EventBridge notification, immutable
`If-None-Match` CONFIG writes, no CONFIG expiration, 4 KiB SSM guard, local KMS
Region checks, canonical prefix policy, and the narrow Checkov suppression.

### Ownership Boundaries

- Cell root: registration exception, Process Manager shell, Scheduler group,
  Scheduler source/DLQ, their policies, and Cell Contract additions.
- Canary fixture root: task definition, launch/execution/task roles, log group,
  disabled schedule/delivery role, CONFIG candidate, and non-production sink.
- No root may read another Terraform state. The canary root has no direct
  namespace/configuration registry, ledger, queue-policy, or Cell IAM mutation.

### Architecture And Security Guardrails

- Use AD-5 contracts, AD-11 queue bounds, AD-12 role separation, AD-13 private
  Fargate networking, AD-24 stable Process Manager principal, AD-25 one owner
  per edge, AD-28 registration, and AD-29 publish-before-enable.
- Fargate requires `awsvpc`; private subnets and `assign_public_ip = "DISABLED"`
  are mandatory. Do not invent network, account, Region, cluster, image, or
  identity defaults.
- All new roles need supplied permissions boundaries and exact trust/resources.
  No broad wildcard, plaintext secret, public task, mutable tag, provisioner,
  `null_resource`, remote state, or generated state/plan file is acceptable.
- SQS source/DLQ are standard, CMK-encrypted, 14-day retained, with redrive at
  least five. Scheduler authority is derived from queue ARN, sender RoleId, and
  schedule group; message body coordinates remain assertions.

### Contract And Test Requirements

Reuse `tests/contract/support/contracts.py`, local schema registry, RFC 8785
hashing, schedule generation, lifecycle catalog, IAM catalog, ownership catalog,
producer catalog, and queue constraints. Do not duplicate contract logic or
change a versioned artifact without updating its manifest/release/migration
evidence. Tests are credential-free, local, deterministic, and must prove static
scope/policy semantics rather than deployed execution.

### Validation And Rollback

Every discovered Terraform root has `versions.tf` and a provider lock. Run all
existing validation, preserving the temporary data-dir and locked backend-free
initialization pattern. Rollback retains shared Cell registration and CONFIG
evidence, keeps launch disabled, and reverts compatible fixture definitions; it
is not routine destructive cleanup.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.4]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-5-to-AD-13]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-23-to-AD-29]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/solution-design-review.md#Terraform-and-Delivery]
- [Source: contracts/v1/catalogs/iam.json]
- [Source: contracts/v1/catalogs/queue-lambda-constraints.json]
- [Source: contracts/v1/catalogs/lifecycle.json]
- [Source: _bmad-output/implementation-artifacts/1-3-deploy-cell-registration-and-discovery-foundations.md]
- [Source: _bmad-output/project-context.md]
- [Source: _bmad/custom/standards/aws-terraform-implementation.md]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Created from Epic 1 Story 1.4, the Architecture Spine, solution design review,
  Compatibility Package, Story 1.3 review record, current repository structure,
  and current AWS service documentation.
- Baseline commit is `51bca7d`; Story 1.3 remains reviewed uncommitted context.
- AWS provider `6.54.0` schema inspection: `aws_s3_object` has no
  `If-None-Match` argument and `aws_dynamodb_table_item` has no conditional
  expression argument. The bootstrap therefore uses a Cell-owned best-effort
  declaration and a narrowly role-scoped CONFIG publication compatibility
  exception; it does not grant the fixture direct namespace mutation access.
- Terraform validation used backend-free locked init with temporary
  `TF_DATA_DIR`; no AWS credentials or deployment plan were used.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Selected bootstrap mechanism documented in `fixtures/canary/README.md`:
  Cell-owned reservation items use the standard key shapes and reject identity
  replacement with `prevent_destroy`; the generic transactional Registrar stays
  deferred. The Cell publisher role is the only principal exempted from the
  `If-None-Match` deny, and only for the registered canary prefix.
- Safe cleanup retains the Cell reservation, CONFIG candidate/object versions,
  queues, and other investigation evidence; the schedule remains disabled.
- Full credential-free gate passed after adding the canary root and its dedicated
  Checkov stage. No AWS credentials, plan, apply, Scheduler delivery, ECS task,
  occurrence, success, or alert evidence was produced.
- Code review selected the best-effort declarative bootstrap scope. Follow-up
  corrections aligned contract integrations, schedule hashing, provider trust,
  identity and input validation, durable notification evidence, queue KMS
  Region guards, and documentation with that scope.

### File List

- _bmad-output/implementation-artifacts/1-4-register-a-platform-owned-canary-job.md
- docs/runbooks/README.md
- fixtures/canary/
- modules/ecs-scheduled-job-platform/
- scripts/validate.py
- tests/contract/support/contracts.py
- tests/contract/test_canary_fixture.py
- tests/contract/test_canary_reservation.py
- tests/contract/test_cell_foundation.py
- tests/contract/test_documentation.py
- tests/contract/test_repository_structure.py

### Change Log

- 2026-07-16: Created Story 1.4 implementation context and marked it ready for development.
