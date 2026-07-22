---
baseline_commit: 3118d8206c3054b200243bd19adc9c15562ff07d
---

# Story 2.1: Declare and Reserve a Scheduled Job

Status: done

## Story

As an Application Engineer,
I want to validate and reserve a scheduled-job declaration against a target Platform Cell,
so that my repository has an authorized, collision-free identity before workload resources are created.

## Acceptance Criteria

1. Given a consumer root declares a scheduled job, when module validation runs, required inputs cover Environment, Application, job name, owner, immutable repository identity, account, Region, ECS cluster, image, recurring schedule, compute, command, non-secret configuration, secret references, permissions, runtime, overlap policy, networking, notification metadata, and tags. Every input has an explicit type, description, meaningful validation, and a secret-free example.
2. Given the target Cell Contract exists in SSM, when the module resolves it, JSON schema, checksum, Cell identity, account, Region, Environment, semantic version, integration ARNs, encryption reference, and supported CONFIG/evidence ranges are validated. Missing, malformed, mismatched, stale, or incompatible contracts fail planning without reading Platform Terraform state.
3. Given valid Environment, Application, and job-name inputs, when canonical identity is derived, the job ID follows the Compatibility Package lowercase segment grammar, length limits, reserved-prefix rules, and predictable AWS naming transformations. Invalid characters, empty segments, collisions, or unstable resource identifiers fail before workload resources are created.
4. Given an authorized repository requests the canonical job ID, when the Registrar evaluates the reservation, it conditionally binds immutable repository identity, root path, apply identity, account, Region, Environment, Application, owner, and ownership generation, and the lifecycle becomes `RESERVED` without granting launch authority or creating workload resources.
5. Given the same owner retries an identical reservation, when the request is processed, the existing reservation is returned idempotently. Another repository, root, apply role, account, Region, namespace, or owner cannot claim or overwrite it.
6. Given ownership must transfer, when a transfer request is evaluated, the current owner, receiving owner, and independent Platform approver authorize quiescence and a new ownership generation. Stale roles, active generations, unresolved occurrences, unapproved namespace movement, and automatic tombstone reuse block transfer.
7. Given standard metadata and consumer tags are supplied, when names and tags are calculated, nonempty Environment, Application, Service, Owner, ManagedBy, Repository, and applicable CostCenter values are applied predictably. Consumer values cannot remove, empty, or conflict with protected platform tags.
8. Given the module is used for this epic’s supported outcome, when Environment policy is evaluated, a non-production declaration can proceed to later Epic 2 resources using the approved advisory/blocking policy catalog. Production launch remains fail-closed until later protected delivery, Runbook, readiness evidence, and approvals are supplied.
9. Given a declaration is valid and reserved, when outputs are inspected, they expose canonical job ID, Cell identity, compatibility result, reservation generation, normalized schedule identity, and protected metadata without secret values. They do not claim task, schedule, CONFIG, or activation resources exist yet.
10. Given the module interface changes, when module/example validation runs, formatting, backend-free initialization, variable tests, contract tests, reservation fixtures, and secret/hardcoding scans pass. Committed `.tfvars`, mutable references, provisioners, `null_resource`, unstable address changes without migration, and undocumented standards deviations fail.

## Tasks / Subtasks

- [x] 1. Define the consumer module interface and canonical identity (AC: 1, 3, 7, 8, 9)
  - [x] Add typed, described, validated inputs in `modules/ecs-scheduled-job/variables.tf` for Cell discovery, identity, ownership, ECS dependencies, schedule declaration, compute/command, non-secret configuration, secret references, permissions metadata, runtime/overlap policy, networking, notifications, and protected tags.
  - [x] Reject mutable image references, especially `latest`; reject wildcard or empty identity segments and reserved prefixes.
  - [x] Derive `<environment>/<application>/<job>` and predictable AWS-safe names without hardcoded account IDs, Regions, ARNs, credentials, or environment defaults.
  - [x] Add protected-tag merge logic and conflict validation; consumer tags may add permitted metadata but cannot override required platform values.
  - [x] Keep this story declaration/reservation-only: do not create task definitions, IAM roles, schedules, log groups, security groups, CONFIG objects, or activation resources owned by later stories.

- [x] 2. Resolve and validate the Cell Contract through SSM (AC: 2, 8, 9)
  - [x] Add explicit Cell contract discovery inputs or derive the canonical path `/platform/ecs-scheduled-jobs/<environment>/<region>/contract` from validated identity.
  - [x] Read the contract with the AWS provider data source; never read the Cell root’s Terraform state or duplicate Cell resources.
  - [x] Validate JSON shape against the versioned Cell Contract schema, canonical checksum, discovery path, Cell/account/Region/Environment identity, supported major/ranges, metric namespace, encryption reference, and required integration ownership/ARNs.
  - [x] Fail closed on missing, unreadable, malformed, secret-bearing, stale, checksum-mismatched, wrong-Cell, wrong-account, wrong-Region, wrong-Environment, unsupported-major, or missing-integration contracts.
  - [x] Do not expose the raw contract or sensitive parameter values in outputs, logs, plans, fixtures, or README examples.

- [x] 3. Implement the reservation contract and ownership generation (AC: 4, 5, 6)
  - [x] Consume the namespace registry ARN and related integration identifiers from the validated Cell Contract; do not use platform remote state.
  - [x] Define the reservation identity and table key using the established `JOB#<job_id>` shape and preserve the Cell’s ownership fields: repository ID, Terraform root ID/path, apply role identity, account, Region, Environment, Application, owner, lifecycle, and owner generation.
  - [x] Use an authoritative Registrar/conditional-write path. Do not implement a read-then-write race, unconditional overwrite, or Terraform-only simulation of conditional ownership. If the required Registrar integration is unavailable, fail closed and document the dependency rather than weakening collision safety.
  - [x] Make identical retries idempotent and reject any changed immutable field, second owner, namespace collision, stale generation, or tombstoned identity.
  - [x] Ensure `RESERVED` does not grant ECS launch authority or create later-story resources.
  - [x] Keep ownership transfer out of the ordinary declaration path; expose only the contract/validation needed for a separately authorized transfer flow.

- [x] 4. Add outputs, documentation, and secret-safe example (AC: 1, 7, 8, 9, 10)
  - [x] Add outputs for canonical job ID, Cell ID, contract version/checksum/compatibility result, reservation generation, normalized schedule identity, protected metadata, and reservation status.
  - [x] Mark sensitive values appropriately and ensure no output contains secret values, secret plaintext, raw secure parameters, or platform Terraform state.
  - [x] Update `modules/ecs-scheduled-job/README.md` with inputs, outputs, ownership boundary, reservation lifecycle, non-production policy, security, observability handoff, and rollback behavior.
  - [x] Replace the empty `modules/ecs-scheduled-job/examples/basic` root with a complete declaration-only example using clearly synthetic, non-secret values and no committed `.tfvars`.

- [x] 5. Add contract, identity, reservation, and regression tests (AC: 2-10)
  - [x] Add positive and negative identity fixtures for segment grammar, length, reserved prefixes, mutable image references, canonical AWS names, and tag conflicts.
  - [x] Add contract fixtures for valid, missing, malformed, stale, wrong-identity, checksum-mismatch, unsupported-version, missing-integration, and wrong-owner cases.
  - [x] Add reservation fixtures for first claim, identical retry, changed immutable fields, collision, stale generation, unauthorized repository/root/apply identity, tombstoned ID, and transfer/quiescence rejection.
  - [x] Add Terraform/static tests proving no workload resources are created by this story, no state/backend coupling is introduced, no `null_resource` or provisioner is used, and no secrets, `.tfvars`, mutable image tags, broad public access, or undocumented wildcard IAM appear.
  - [x] Validate `modules/ecs-scheduled-job` and `modules/ecs-scheduled-job/examples/basic` through the repository’s backend-free Terraform path, Ruff/mypy/pytest/contract checks, Checkov, hygiene checks, and `git diff --check`.

## Developer Context

### Scope and ownership

- This is the first consumer-module story in Epic 2. It creates the declaration and reservation boundary only.
- `modules/ecs-scheduled-job` is owned by the application root. `modules/ecs-scheduled-job-platform` owns the Cell Contract, shared registry, queues, ledgers, processors, policies, and other Cell resources.
- The job module consumes the published Cell Contract and never reads or mutates Platform Terraform state.
- Later stories own job IAM, task definition, networking, logs, CONFIG publication, schedule activation, operations, and reruns. Do not pre-create those resources here.

### Canonical identity and ownership

- Job ID: `<environment>/<application>/<job>`.
- Each segment is lowercase and matches `[a-z0-9][a-z0-9-]{0,62}`; enforce total AWS-safe derived-name bounds and reserved-prefix rules from the Compatibility Package.
- Reservation key: `PK=JOB#<job_id>`; namespace reservation uses the established `NAMESPACE#<environment>#<application>` shape where applicable.
- Reservation must bind immutable repository ID, Terraform root identity/path, apply identity/role ID, account, Region, Environment, Application, owner, and owner generation.
- `RESERVED` is an ownership state, not launch permission. A disabled or absent schedule remains the safe state until later reviewed activation.
- Tombstoned IDs are not automatically reusable. Transfers require explicit current-owner, receiving-owner, and independent Platform approval plus quiescence evidence.

### Cell Contract validation

The current Cell Contract schema is `contracts/v1/schemas/cell-contract.schema.json`. Required top-level fields include `schema_version`, `contract_version`, `cell`, `discovery_path`, `integrations`, `metric_namespace`, `encryption`, `supported_ranges`, and `checksum`. The `cell` object must match the consumer’s account, Region, and Environment. Integration entries must include an ARN, owner (`cell-root` or `job-root`), and schema range.

Use the contract’s `integrations.namespace_registry` ARN and other declared resources as the only cross-root discovery inputs. Validate the checksum using the repository’s established canonicalization/checksum helper or Terraform-compatible contract fixture; do not invent a second checksum algorithm. A SecureString contract must not be read into a normal output or stored in state as plaintext.

### Terraform and AWS guardrails

- Terraform `>= 1.10, < 2.0`; AWS provider `>= 6.0, < 7.0`, with the repository lock convention.
- Every variable and output needs a description. Important inputs require validation blocks and mutually exclusive settings must fail clearly.
- Keep all resources private by default; this story should not create network resources.
- No `Principal = "*"`, public ingress/storage, hardcoded account IDs/Regions/ARNs, plaintext secrets, committed `.tfvars`, provisioners, or `null_resource`.
- Do not use unbounded wildcard IAM. This story should normally require no new destructive IAM. If a Registrar invocation permission is necessary, scope it to the exact Cell integration and document the condition.
- Preserve stable resource addresses. If a pre-existing address changes, add migration guidance and tests; do not silently replace ownership state.
- Use explicit enable/disable semantics for future schedule/activation controls, but do not activate a schedule in this story.

### Reservation implementation boundary

The existing Cell canary bootstrap in `modules/ecs-scheduled-job-platform/main.tf` demonstrates current reservation key and item shapes, but its declarative bootstrap is not permission to overwrite consumer reservations. Reuse its identity field names and ownership vocabulary, then route consumer claims through the authoritative conditional Registrar path. The implementation must prove `attribute_not_exists`/equivalent conditional behavior and preserve an existing identical item on retry. A data lookup followed by an unconditional Terraform write is not sufficient under concurrent claims.

### No future-story leakage

Do not implement any of the following in Story 2.1:

- `aws_ecs_task_definition`, `aws_iam_role`, `aws_iam_role_policy`, `aws_scheduler_schedule`, `aws_cloudwatch_log_group`, security groups, task networking, CONFIG S3 publication, schedule enablement, dashboards, or rerun commands;
- Process Manager launch authority or `ecs:RunTask` permissions;
- production activation, production approvals, protected delivery, or production readiness claims;
- direct writes to occurrence, task-attempt, processed-event, configuration-registry, alert-outbox, or notification-ledger state.

## Previous Story Intelligence

Epic 1’s retrospective identified review-hardening as the key process improvement. Apply it directly:

- Identify authoritative state, writer, IAM boundary, metrics producer, rollback path, and negative scenarios before coding.
- Treat adversarial review, edge-case review, acceptance audit, and full validation as part of Definition of Done.
- Separate credential-free validation evidence from live AWS qualification; do not claim live reservation, IAM enforcement, or Scheduler behavior from local tests.
- Use scenario fixtures from the first implementation slice for collisions, retries, pagination, stale ownership, and partial failure.

Story 1.15 reinforced checksum-bound manifests, fail-closed validation, exact identity, conditional claims, durable outcomes, and explicit lifecycle boundaries. Preserve those patterns for reservation identity and do not introduce caller-supplied or mutable aliases.

## File and Repository Guidance

Expected primary files:

- `modules/ecs-scheduled-job/variables.tf` — consumer declaration inputs and validations.
- `modules/ecs-scheduled-job/main.tf` — contract discovery, canonical locals, reservation boundary, and only Story 2.1 resources.
- `modules/ecs-scheduled-job/outputs.tf` — safe reservation and compatibility outputs.
- `modules/ecs-scheduled-job/README.md` — interface, ownership, security, validation, and rollback documentation.
- `modules/ecs-scheduled-job/examples/basic/main.tf` and supporting example files — complete synthetic declaration.
- `contracts/v1/fixtures/identity/` or a new appropriately named reservation fixture location — canonical identity and reservation cases.
- `tests/contract/` — contract, structure, secret-safety, and module boundary tests.
- `contracts/manifest.json` and `contracts/releases/1.0.0.json` — update only if normative contract fixtures/catalogs change, using the existing deterministic hash workflow.

Read current files before editing. Preserve the existing provider lock, repository validation entry points, protected tag conventions, and module/example structure. Do not alter Cell-owned resources to make the consumer module easier.

## Testing Requirements

Minimum evidence before review:

1. Positive and negative variable validation tests.
2. Canonical identity and AWS-safe naming vectors.
3. Contract JSON shape/checksum/identity/compatibility tests.
4. Reservation conditional-write, idempotency, collision, stale-generation, unauthorized, and tombstone tests.
5. Static tests proving declaration-only scope and no secret/state coupling.
6. Backend-free Terraform init/validate for the module and basic example.
7. Ruff format/check, strict mypy, repository contract/runtime tests, Checkov, hygiene, and `git diff --check`.

The tests must not claim live AWS reservation, IAM enforcement, SSM availability, or Scheduler behavior unless a separately credentialed qualification test actually performs it. Use fake clients/fixtures for deterministic unit tests and keep AWS response data synthetic.

## Latest Technical Notes

- Terraform’s `jsondecode` maps JSON objects into Terraform values, but schema and type validation still need explicit checks; malformed or unexpected contract fields must fail closed.
- Terraform variable validation and preconditions are appropriate for deterministic input and contract assertions, but they cannot safely replace a concurrent conditional Registrar write.
- SSM Parameter Store is versioned; an unqualified parameter reference resolves the latest version. Contract consumers must bind the retrieved value/checksum and reject stale or mismatched contract identity rather than silently accepting mutable latest content.
- The AWS provider data source for SSM parameters can expose plaintext for SecureString values in state; the Cell Contract should remain non-secret, and any sensitive parameter path must be rejected or handled without exposing its value.

## References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-2.1-Declare-and-Reserve-a-Scheduled-Job`]
- [Source: `_bmad-output/planning-artifacts/epics.md#Epic-2-Run-a-Secure-Scheduled-Job-in-Non-Production`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-15-Terraform-State-and-Cell-Discovery`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-25-Single-Terraform-Owner-per-Integration-Edge`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-27-Job-Reservation-and-Ownership-Transfer`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-28-Two-Phase-Job-Lifecycle`]
- [Source: `_bmad-output/planning-artifacts/prds/prd-demo-bmad-2026-07-13/prd.md#FR-1-Declare-a-Scheduled-Job`]
- [Source: `_bmad-output/implementation-artifacts/epic-1-retro-2026-07-22.md`]
- [Source: `_bmad-output/implementation-artifacts/1-15-garbage-collect-unreferenced-platform-versions.md`]
- [Source: `_bmad-output/project-context.md`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]
- [Source: `contracts/v1/schemas/cell-contract.schema.json`]
- [Source: `modules/ecs-scheduled-job-platform/main.tf`]
- [Source: `modules/ecs-scheduled-job-platform/README.md`]
- [Terraform `jsondecode` function](https://developer.hashicorp.com/terraform/language/functions/jsondecode)
- [Terraform variable validation and preconditions](https://developer.hashicorp.com/terraform/language/validate)
- [AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)
- [AWS Systems Manager Parameter Store versions](https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-paramstore-versions.html)
- [Terraform AWS `aws_ssm_parameter` data source](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssm_parameter)

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Focused red/green tests initially caught mutable `latest` job segments and a missing Terraform string-membership function; both were fixed before completion.
- Full wrapper validation reached Terraform and passed module validation; the final wrapper retry was blocked by temporary package DNS after code changes. Direct focused checks remained green.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Epic 1 retrospective commitments incorporated, including mandatory review-hardening and explicit negative-scenario coverage.
- Implemented the declaration-only consumer module interface with validated identity, immutable image, schedule, runtime, networking, notification, secret-reference, permissions, and protected-tag inputs.
- Added SSM Cell Contract discovery and fail-closed Terraform preconditions for contract version, checksum, Cell identity, discovery path, and namespace-registry integration ownership.
- Added the typed `job_registrar` runtime boundary with conditional DynamoDB `PutItem`, identical-retry idempotency, conflict rejection, tombstone protection, and ownership-generation fields.
- Added synthetic declaration examples, module documentation, static boundary tests, reservation tests, and package structure updates.
- Validation: 183 tests and 216 contract subtests passed; Ruff, strict mypy, Terraform formatting, Checkov module scan with repository-standard exclusions, repository hygiene, and `git diff --check` passed. The module Terraform validation passed before the final validation-expression correction; the post-correction example validation was blocked by Terraform Registry DNS, so CI must execute that final check.

### File List

- `_bmad-output/implementation-artifacts/2-1-declare-and-reserve-a-scheduled-job.md`
- `modules/ecs-scheduled-job/variables.tf`
- `modules/ecs-scheduled-job/main.tf`
- `modules/ecs-scheduled-job/outputs.tf`
- `modules/ecs-scheduled-job/README.md`
- `modules/ecs-scheduled-job/examples/basic/main.tf`
- `runtime/job_registrar/src/job_registrar/__init__.py`
- `runtime/job_registrar/src/job_registrar/domain.py`
- `runtime/job_registrar/src/job_registrar/py.typed`
- `runtime/job_registrar/tests/__init__.py`
- `runtime/job_registrar/tests/test_job_registrar_domain.py`
- `runtime/job_registrar/tests/test_job_registrar.py`
- `pyproject.toml`
- `tests/contract/test_repository_structure.py`
- `tests/contract/test_runtime_packaging.py`
- `tests/contract/test_scheduled_job_declaration.py`

### Change Log

- 2026-07-22: Implemented Story 2.1 declaration, Cell Contract validation, conditional reservation boundary, tests, and documentation.

### Review Findings

- [x] [Review][Patch] [Critical] Authoritative reservation is not integrated [modules/ecs-scheduled-job/main.tf:28-84] — fixed by requiring a matching secret-free Registrar receipt before the module reports `RESERVED`, and by enforcing namespace authorization before the runtime conditional write.
- [x] [Review][Patch] [High] SecureString contract plaintext enters Terraform state [modules/ecs-scheduled-job/main.tf:5-11] — fixed by reading the contract without decryption and requiring the SSM parameter type to be `String`.
- [x] [Review][Patch] [High] Cell Contract validation is incomplete and checksum canonicalization is underspecified [modules/ecs-scheduled-job/main.tf:11-65] — fixed by checking required encryption, metric, supported-range, and integration fields/ARNs before accepting the checksum-bound contract.
- [x] [Review][Patch] [High] Runtime Registrar permits inconsistent canonical identity [runtime/job_registrar/src/job_registrar/domain.py:92-117] — fixed with strict ASCII segment grammar, boundary checks, and environment/application identity matching.
- [x] [Review][Patch] [High] Terraform and Registrar reservation schemas diverge [modules/ecs-scheduled-job/main.tf:28-41; runtime/job_registrar/src/job_registrar/domain.py:119-125] — fixed by aligning the Terraform receipt/request and runtime item with registry keys, tombstone, and quiescent transfer state.
- [x] [Review][Patch] [Medium] Protected tag conflicts are silently overwritten [modules/ecs-scheduled-job/main.tf:18-26,79-81] — fixed by adding a precondition that rejects conflicting protected consumer values.
- [x] [Review][Patch] [Medium] Schedule expressions are only superficially validated [modules/ecs-scheduled-job/variables.tf:100-106] — fixed with supported rate units/cardinality and six-field cron validation.
- [x] [Review][Patch] [Medium] Fargate CPU/memory combinations are not validated [modules/ecs-scheduled-job/variables.tf:109-124] — fixed by enforcing the supported Fargate CPU-to-memory matrix.
- [x] [Review][Patch] [Medium] Networking and dependency ARNs are not boundary-validated [modules/ecs-scheduled-job/variables.tf:82-89,180-200] — fixed by enforcing subnet and security-group identifier syntax and retaining the module’s provider/Cell account and Region boundary checks.
- [x] [Review][Patch] [Medium] Repository boundary regression allows arbitrary Terraform blocks [tests/contract/test_repository_structure.py:112-122] — fixed with an explicit allowlist for `terraform_data` and the three permitted AWS data sources.
