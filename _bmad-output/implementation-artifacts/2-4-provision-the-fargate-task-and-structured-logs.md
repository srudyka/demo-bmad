---
baseline_commit: 7f4ce8504638b3c7fb0b09de0b7c6f11349f7254
---

# Story 2.4: Provision the Fargate Task and Structured Logs

Status: done

## Story

As an Application Engineer,
I want the module to create a validated Fargate task definition and retained log group,
so that my job runs with an immutable identity and emits evidence the Cell can correlate.

## Acceptance Criteria

1. **Fargate task definition and roles**

   Given a reserved job and approved IAM roles, when the task definition is
   planned, then it uses `FARGATE`, `awsvpc`, explicit CPU and memory, an
   explicitly supported runtime platform, and the exact Story 2.2 execution and
   application-task role ARNs. Unsupported CPU/memory combinations, invalid
   ephemeral storage, missing required runtime settings, and incompatible
   platform values fail before apply.

2. **Immutable image and deployment identity**

   Given a container image is declared, when image policy runs, then an
   immutable digest or explicitly approved immutable reference is accepted and
   recorded in Deployment Identity. Mutable references such as `latest` remain
   blocking for production promotion and must not be silently normalized.

3. **Container input separation**

   Given command, entrypoint, and non-secret environment overrides are supplied,
   when container definitions are rendered, then the reviewed values are
   preserved exactly and remain separate from runtime occurrence overrides.
   Consumer inputs must not override reserved job, Occurrence ID, CONFIG,
   attempt, task, or Deployment Identity fields.

4. **ECS-agent secrets**

   Given ECS-agent secret references are supplied, when container definitions are
   rendered, then they use the ECS `secrets` contract with locator metadata only.
   No secret value may appear in ordinary environment variables, examples,
   task-definition JSON, CONFIG, plans, outputs, tags, or logs.

5. **Application-pull secrets**

   Given application-pull secret references are supplied, when container
   definitions are rendered, then only non-sensitive locator and mode metadata
   are available to the application. Story 2.2 task-role permissions and Story
   2.3 private-network evidence must validate before the task definition is
   deployable.

6. **Encrypted retained log group**

   Given a per-job CloudWatch log group is created, when logging configuration is
   applied, then the group is predictably named, encrypted with the approved KMS
   key, protected-tagged, and assigned explicit retention within platform
   guardrails. Defaults are 30 days for non-production and 90 days for
   production, unless the versioned policy requires stricter retention.

7. **Exact `awslogs` scope**

   Given the task uses the `awslogs` driver, when execution-role scope is
   evaluated, then every essential container writes only to the exact job log
   group with a discoverable stream prefix. The task must not omit log
   configuration or use another job's log group.

8. **Structured completion evidence**

   Given the Job Completion Contract applies, when application logging
   requirements are validated, then the declaration and example require
   structured start, success, and failure records asserting the supplied job,
   Occurrence ID, CONFIG, attempt, timestamps, status, exit code when available,
   and sanitized error reason. Documentation must state that a success marker or
   zero exit alone does not establish successful completion.

9. **Outputs and safe exposure**

   Given the task-definition revision is registered, when outputs are inspected,
   then they expose the full revision ARN, family, immutable image identity, log
   group, role ARNs, module version, source revision input, and protected
   metadata needed for later CONFIG publication. Secret values, raw sensitive
   container configuration, and unbounded operational data are excluded.

10. **Validation and rollback**

    Given task or logging configuration changes, when validation runs, then
    tests cover valid and invalid compute combinations, immutable and mutable
    images, command rendering, reserved-field collisions, both secret modes,
    log encryption and retention, exact permissions, and structured completion
    examples. The module and basic example pass formatting, backend-free
    validation, security scanning, and address-stability checks.

    Given a task-definition change must be rolled back, when the prior compatible
    configuration is restored, then Terraform registers or selects the known-good
    immutable revision without deleting log history or referenced prior
    revisions. Later cleanup remains governed by lifecycle proof rather than the
    rollback operation.

## Tasks / Subtasks

- [x] 1. Extend the job module interface for task and log configuration (AC: 1, 2, 3, 6, 9)
  - [x] Add descriptions and validation for platform version/OS and CPU architecture, ephemeral storage, entrypoint, log retention, KMS encryption, source revision, module version, and any completion-contract metadata required by the existing module conventions.
  - [x] Preserve existing Story 2.1–2.3 variable types, stable resource addresses, protected tags, reservation preconditions, secret-mode semantics, and networking outputs.
  - [x] Reject reserved runtime fields in consumer environment overrides and prevent sensitive values or secret-shaped inputs from entering the task definition.
  - [x] Keep the image digest requirement strict unless an explicitly cataloged immutable-reference exception is implemented with tests and production-blocking policy metadata.

- [x] 2. Create the Fargate task definition (AC: 1, 2, 3, 5, 9)
  - [x] Add only the job-owned `aws_ecs_task_definition` resource in the existing module; do not create an ECS cluster, service, Scheduler resource, CONFIG object, alarm, dashboard, shared Cell resource, or runtime ledger mutation.
  - [x] Use the canonical family derived from `local.name_prefix`, `requires_compatibilities = ["FARGATE"]`, `network_mode = "awsvpc"`, explicit task CPU/memory, validated runtime platform, and exact `aws_iam_role.execution.arn`/`aws_iam_role.task.arn` values.
  - [x] Render one essential application container from the immutable image, preserving reviewed command/entrypoint and non-secret environment values without allowing reserved-field collisions.
  - [x] Carry the job identity, deployment identity, and runtime correlation contract as controlled metadata only; occurrence-specific values must remain runtime-owned and must not be hardcoded into Terraform.
  - [x] Configure task-level ephemeral storage only within AWS Fargate-supported bounds and reject unsupported combinations before apply.

- [x] 3. Render both secret modes without secret leakage (AC: 4, 5)
  - [x] For `ecs-agent`, render only `secrets` entries with exact Secrets Manager/SSM locator ARNs and keep secret/KMS authority on the execution role as established by Story 2.2.
  - [x] For `application-pull`, do not inject application secrets through ordinary environment variables; preserve the non-sensitive mode/path handoff and rely on the task role/network contract from Stories 2.2 and 2.3.
  - [x] Add negative tests scanning rendered JSON, variables, outputs, examples, plans/fixtures, tags, and documentation for secret values, key/value secret syntax, or forbidden reserved fields.

- [x] 4. Create retained encrypted CloudWatch logging (AC: 6, 7, 8)
  - [x] Add one job-owned `aws_cloudwatch_log_group` at `/platform/jobs/<environment>-<application>-<job>` with explicit retention, approved KMS key, protected tags, deletion/rollback behavior that preserves referenced history, and stable naming.
  - [x] Configure `awslogs` for every container with the exact group name, target Region, and deterministic stream prefix such as the canonical job family; do not grant or configure another job's log scope.
  - [x] Define the structured completion contract in the README/example and validate required fields: job identity, Occurrence ID, CONFIG version, attempt, RFC 3339 UTC timestamp, status, optional exit code, and sanitized error reason.
  - [x] Make clear that log success is evidence for correlation and never authoritative completion by itself; ECS task state and Cell correlation remain required by later stories.

- [x] 5. Publish Deployment Identity and task handoff outputs (AC: 2, 9)
  - [x] Output full task-definition ARN including revision, family, revision, image digest, log-group name/ARN, execution/task/launch role ARNs, module version, source revision, protected tags, and the existing networking handoff.
  - [x] Keep outputs non-sensitive; do not expose rendered raw container JSON when it could include sensitive configuration or unbounded application data.
  - [x] Preserve output names and types already consumed by Story 2.5; add migration guidance if an output must change.

- [x] 6. Update documentation and rollback guidance (AC: 6, 8, 10)
  - [x] Update `modules/ecs-scheduled-job/README.md` with task/log ownership, inputs, outputs, retention/encryption assumptions, structured log examples, failure planes, observability handoff, validation, and rollback.
  - [x] Document that rollback selects/restores a known-good immutable task revision and retains log history and referenced revisions; it does not enable schedules, delete logs, or clean up resources still referenced by CONFIG/occurrences.
  - [x] Keep Scheduler, CONFIG publication, alarms, dashboards, and Cell acknowledgement explicitly deferred to Stories 2.5–2.6 and later operational stories.

- [x] 7. Add contract, static, and module tests (AC: 1–10)
  - [x] Add positive/negative fixture cases for Fargate compatibility, supported CPU/memory, platform/architecture, ephemeral storage bounds, digest/mutable image policy, command/entrypoint/environment rendering, and reserved-field rejection.
  - [x] Test both secret modes and prove only the intended role receives secret/KMS permissions; assert no secret values or sensitive raw container JSON are exposed.
  - [x] Test log-group name, KMS key, retention defaults/overrides, protected tags, `awslogs` options, exact stream prefix, and structured completion fields.
  - [x] Test output identity and stable resource addresses, and statically prove no Scheduler, CONFIG, alarm, dashboard, shared-network, Cell-owned, or runtime-ledger resources are added.
  - [x] Reuse existing contract helpers and test style; do not create a parallel IAM or deployment-identity evaluator.

- [x] 8. Run all required quality gates (AC: 10)
  - [x] Run Terraform fmt, backend-free init/validate for the module and `examples/basic`, scoped/full Ruff, strict mypy, contract/runtime tests, Checkov, repository hygiene, and `git diff --check`.
  - [x] Keep credential-free validation separate from live AWS qualification. Do not claim deployed ECS, CloudWatch, IAM, secret retrieval, or completion-correlation behavior from local tests alone.

### Review Findings

- [x] [Review][Patch] Carry `platform_version` into the authoritative launch/CONFIG handoff; it is currently validated and output but not consumed by `aws_ecs_task_definition` [modules/ecs-scheduled-job/variables.tf:138]
- [x] [Review][Patch] Application-pull mode must not render ECS-agent `secrets` entries [modules/ecs-scheduled-job/task.tf:42]
- [x] [Review][Patch] Require `secret_environment_names` to match non-empty `secret_references` before task rendering [modules/ecs-scheduled-job/variables.tf:228]
- [x] [Review][Patch] Reserve controlled `SOURCE_REVISION` and `MODULE_VERSION` environment names [modules/ecs-scheduled-job/variables.tf:198]
- [x] [Review][Patch] Reject fractional CPU and memory values before Fargate matrix validation [modules/ecs-scheduled-job/variables.tf:116]
- [x] [Review][Patch] Validate the contract KMS ARN against the target account, Region, and partition before using it for log encryption [modules/ecs-scheduled-job/task.tf:3]
- [x] [Review][Patch] Add concrete structured start, success, and failure JSON examples and required-field tests for the completion contract [modules/ecs-scheduled-job/README.md:86]
- [x] [Review][Patch] Replace source-text-only task tests with rendered or fixture-backed coverage for both secret modes, runtime inputs, log settings, outputs, and rollback behavior [tests/contract/test_scheduled_job_task.py:9]

## Dev Notes

### Current baseline and ownership boundary

- Baseline commit before this story: `7f4ce85` (`Story 2.3` complete).
- `modules/ecs-scheduled-job` currently owns declaration/reservation validation,
  three job IAM roles, private-network validation, and an optional job-owned
  security group. It does not yet create a task definition or log group.
- Story 2.4 may add only the job-owned ECS task definition and per-job
  CloudWatch log group. The Cell root continues to own shared queues, DLQs,
  processors, event capture, metrics namespace, alarms, CONFIG registry/inbox,
  and Cell Contract. Scheduler, CONFIG publication, acknowledgement, and
  activation belong to later stories.
- Preserve `RESERVED`; creating a task definition does not grant launch
  authority or enable a schedule. The task revision is a published artifact
  for later phase-one CONFIG and Cell validation.

### Existing code to extend, not replace

- `modules/ecs-scheduled-job/main.tf`: preserve Cell Contract discovery,
  reservation preconditions, identity/tag checks, IAM identity checks, secret
  mode checks, network policy checks, and existing data lookups. Add task/log
  resources without weakening these guards.
- `modules/ecs-scheduled-job/iam.tf`: reuse `aws_iam_role.execution` and
  `aws_iam_role.task` ARNs. Do not create duplicate roles or broaden the
  execution/task policies. The execution policy already defines the exact job
  log-group ARN shape; the new log group name must match it exactly.
- `modules/ecs-scheduled-job/variables.tf`: existing `image` requires a
  sha256 digest, `cpu`/`memory` validate the supported Fargate matrix,
  `secret_references` are locator-only, `environment_variables` are non-secret,
  and `runtime.max_runtime_seconds`/`idempotency` are already declared.
- `modules/ecs-scheduled-job/outputs.tf`: preserve `job_id`, `cell`,
  `reservation`, `protected_tags`, `normalized_schedule`, `job_iam`, and
  `networking`; add task/log/deployment identity outputs in a compatible shape.
- `modules/ecs-scheduled-job/examples/basic/main.tf`: keep synthetic IDs and
  no secrets. Extend it with the minimum task/log/completion-contract inputs
  needed to prove the interface.
- `tests/contract/`: reuse current static boundary tests, IAM helpers, manifest
  integrity checks, and fixture patterns. Do not introduce a second evaluator.

### Required task-definition contract

- Family must be the stable job family derived from the canonical job identity;
  no random names or mutable aliases.
- Required task settings are `requires_compatibilities = ["FARGATE"]`,
  `network_mode = "awsvpc"`, explicit task CPU/memory, exact execution/task
  role ARNs, and an explicitly validated runtime platform. Public IP remains
  disabled in the existing networking handoff; this story must not add a public
  interface escape hatch.
- Use the immutable image digest already enforced by the module. Record the
  image identity as deployment evidence, not as an unbounded arbitrary string.
- Container environment is non-secret configuration only. Reserve names for
  `JOB_ID`, `OCCURRENCE_ID`, `CONFIG_VERSION`, `ATTEMPT_NO`, `TASK_ARN`, and
  Deployment Identity fields so later runtime integration cannot be shadowed by
  consumer input. Occurrence/task values are supplied by the launch/runtime
  path, not frozen into Terraform.
- ECS `secrets` entries must use only full Secrets Manager or SSM locator ARNs;
  never convert references into ordinary `environment` entries. Application-
  pull mode exposes only non-sensitive mode/path metadata and must retain the
  exact Story 2.2/2.3 preconditions.

### Logging and completion contract

- Log group name must be `/platform/jobs/<environment>-<application>-<job>` so
  it matches the IAM execution-policy scope established in Story 2.2.
- Use `awslogs` with the exact group, target Region, and stable stream prefix.
  Every essential container must be covered. Do not use firelens, a shared
  wildcard log group, or an implicit group created by the ECS agent.
- Log group retention must be explicit and policy-bounded: 30 days
  non-production, 90 days production by default, with validation against an
  allowed retention list. Encrypt with the approved customer-managed KMS key
  already represented by the Cell Contract or an explicitly governed log key.
- Structured records are application-owned JSON evidence. Required assertions
  are `job_id`, `occurrence_id`, `config_version`, `attempt_no`, `timestamp`,
  `status`, and sanitized `error_reason`; include `exit_code` when available.
  Provide start, success, and failure examples without real secrets. A zero exit
  code or success marker is not sufficient for `SUCCEEDED`; later Cell services
  correlate ECS state and logs under the Job Completion Contract.

### Deployment Identity and rollback

- Deployment Identity must be sufficient to identify source revision, module
  version, workflow/deployment revision input, image digest, target account,
  Region/environment, and task-definition family/revision. Keep this metadata
  secret-free and bounded.
- Task-definition revisions are append-only while referenced by CONFIG,
  occurrences, queues, investigations, or rollback windows. Do not use
  `track_latest` or destroy a referenced prior revision as a shortcut.
- Rollback disables/keeps launch disabled in the later workflow, restores the
  known-good task-definition revision and compatible configuration, preserves
  log history, and revalidates networking/IAM before any later enablement.
  This story itself must not create or enable a schedule.

### AWS Terraform standards to carry forward

- Terraform `>= 1.10, < 2.0`; AWS provider `>= 6.0, < 7.0`; use the committed
  lock convention and backend-free validation.
- Every new variable/output needs a description, explicit type, meaningful
  validation, and a secret-free example. Do not hardcode account IDs, Regions,
  ARNs, credentials, or environment-specific values.
- Use small, reviewable resources and stable addresses. Avoid provisioners,
  `null_resource`, remote state, generated state, `.tfvars`, mutable images,
  public networking, broad IAM, and unrelated refactors.
- Preserve mandatory tags: `Environment`, `Application`, `Service`, `Owner`,
  `ManagedBy`, `Repository`, and applicable `CostCenter`.
- Update README/runbook material, include validation evidence and expected plan
  impact, and document rollback before review. Production observability remains
  a later handoff unless this story's log group/structured completion contract
  requires the documented evidence shape.

## Previous Story Intelligence

### Story 2.3 review lessons

- Review hardening required provider-backed network evidence rather than
  consumer assertions, safe catalog loading, all-provider secret-path
  consistency, fixture-backed positive/negative tests, protected created-group
  rollback, and an auditable Checkov exception. Apply the same fail-closed
  posture here: do not rely on source-text assertions alone and do not accept
  unchecked task/log inputs.
- The module's Checkov scan currently uses a centralized `CKV2_AWS_5`
  sequencing exception because the optional security group is not yet attached
  to a task. Story 2.4 must keep the exception structurally scoped, then remove
  it if the new task definition allows the check to pass.
- Previous validation used pinned `uv 0.11.29`, Terraform 1.15.8, AWS provider
  6.54.0, 198 tests, 217 subtests, strict mypy, Ruff, Checkov, hygiene, and
  direct module/example validation. CI provider-download resets were an
  environmental limitation; record similar limitations separately from code
  failures.

### Prior IAM contract lessons

- Do not duplicate or alter the three IAM roles. The execution role's log-write
  scope must match the new log-group ARN exactly, while task permissions remain
  application-only and secret mode remains exclusive.
- Preserve stable policy statement IDs, role paths, protected tags, boundaries,
  outputs, and exact Cell Contract identity checks. Any intentional migration
  needs a `moved` block or explicit migration guidance.

## Architecture Compliance

- **AD-1/AD-2:** account-local Cell and job-root ownership; no shared Cell
  resources in this module.
- **AD-5/AD-9:** task and completion metadata are versioned, secret-free, and
  correlatable; application IDs are assertions, not authority.
- **AD-8:** task-definition identity must support idempotent Process Manager
  launch and exact family/revision handoff.
- **AD-12:** separate execution/task roles remain intact; no new launch or
  control-plane permissions.
- **AD-13:** Fargate `awsvpc` and private-network outputs from Story 2.3 are
  consumed; no public IP or new networking resources.
- **AD-17:** immutable image and provider/module lock conventions are mandatory.
- **AD-18/AD-24:** revisions/logs remain compatible and retained during rollback.
- **AD-23:** consume the checked-in Compatibility Package and completion/task
  correlation contracts; update manifest/checksums when controlled artifacts
  change.
- **AD-25:** job root owns only its task definition and log group; Cell root owns
  shared event capture, queues, processors, metrics, alarms, and contracts.
- **AD-28/AD-29:** this is a published task artifact only; reservation remains
  authoritative and Scheduler/CONFIG enablement is deferred.

## Validation Requirements

Minimum evidence before review:

1. Module and basic example `terraform fmt`, backend-free init, and validate.
2. Positive/negative task-definition contract tests for Fargate settings,
   compute/platform/storage bounds, immutable images, reserved fields, and
   command/environment rendering.
3. Secret-mode tests proving correct ECS `secrets` rendering and no values in
   ordinary environment, outputs, examples, or logs.
4. Log-group tests for exact name, encryption, retention, protected tags,
   `awslogs` options, stream prefix, and structured completion examples.
5. Output/address-stability and static ownership tests proving no Scheduler,
   CONFIG, alarm, dashboard, shared network, Cell-owned, or runtime-ledger
   resources are created.
6. Ruff format/check, strict mypy, contract/runtime tests, Checkov, repository
   hygiene, manifest/checksum validation, and `git diff --check`.

Tests use synthetic ARNs/IDs and fake policy inputs. They do not claim live ECS
launch, CloudWatch delivery, IAM enforcement, secret retrieval, or completion
correlation without separately credentialed AWS qualification.

## References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-2.4-Provision-the-Fargate-Task-and-Structured-Logs`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-8-Idempotent-Job-scoped-ECS-Launch`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-9-Correlated-Completion-Truth`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-13-Private-Workload-Networking`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-25-Single-Terraform-Owner-per-Integration-Edge`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-29-Publish-Validate-Materialize-Enable-Handshake`]
- [Source: `_bmad-output/planning-artifacts/prds/prd-demo-bmad-2026-07-13/prd.md#FR-5-Run-the-Immutable-Job-Image`]
- [Source: `_bmad-output/planning-artifacts/prds/prd-demo-bmad-2026-07-13/prd.md#FR-14-Emit-Correlated-Completion-Evidence`]
- [Source: `_bmad-output/planning-artifacts/prds/prd-demo-bmad-2026-07-13/prd.md#FR-24-Record-Deployment-Identity-and-Rollback-Evidence`]
- [Source: `_bmad-output/implementation-artifacts/2-2-create-least-privilege-job-iam-roles.md`]
- [Source: `_bmad-output/implementation-artifacts/2-3-enforce-private-task-networking.md`]
- [Source: `_bmad-output/project-context.md`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]
- [AWS ECS task definitions](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definitions.html)
- [AWS ECS Fargate task-definition parameters](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html)
- [AWS ECS task-definition differences for Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-tasks-services.html)
- [AWS ECS example for CloudWatch `awslogs`](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/specify-log-config.html)
- [AWS ECS task IAM roles](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html)
- [Terraform `aws_ecs_task_definition`](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecs_task_definition)
- [Terraform `aws_cloudwatch_log_group`](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_group)

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Context built from Epic 2, architecture spine, project context, AWS Terraform
  standards, Stories 2.2/2.3, current module code, contract fixtures, and
  current AWS/Terraform documentation.

### Implementation Plan

- Extended the existing declaration/IAM/networking module interface with
  validated Fargate runtime, secret-name, log-retention, and Deployment Identity
  inputs while preserving existing role and network contracts.
- Added one job-owned encrypted retained log group and one Fargate task
  definition using exact Story 2.2 roles, immutable image, `awsvpc`, `awslogs`,
  secret locators, and bounded controlled metadata.
- Added compatible task/log/deployment outputs, documentation, synthetic
  task-definition fixtures, and ownership/secret-safety tests.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story 2.4 remains limited to task-definition and log-group ownership; later
  schedule, CONFIG, acknowledgement, and operational stories remain separate.
- Implemented Fargate task definition and encrypted retained log group with
  exact execution/task roles, immutable image, runtime platform, ephemeral
  storage, `awslogs`, secret locator rendering, and reserved-field guards.
- Added Deployment Identity and task/log handoff outputs without exposing raw
  container JSON or secret values.
- Added task-definition fixture cases and updated legacy boundary tests for the
  intentional Story 2.4 ownership expansion.
- Validation: Terraform module/example valid; 203 tests and 218 subtests pass;
  Ruff format/lint, strict mypy, Checkov (87 passed, 0 failed), repository
  hygiene, and `git diff --check` pass. The full repository validator reached
  canary provider initialization/validation but did not emit a final status in
  this environment; direct equivalent gates passed and no code assertion failed.
- Review hardening carried the pinned platform version into Deployment Identity,
  separated application-pull locator metadata from ECS-agent injection, added
  secret mapping and whole-number Fargate guards, protected deployment metadata
  names, validated the log KMS identity, documented structured JSON completion
  records, preserved task revisions, and expanded fixture coverage.
- Review validation: Terraform module/example valid; 204 tests and 218
  subtests pass; scoped Ruff format/lint and `git diff --check` pass.

### File List

- `_bmad-output/implementation-artifacts/2-4-provision-the-fargate-task-and-structured-logs.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `contracts/manifest.json`
- `contracts/v1/fixtures/task-definition/cases.json`
- `modules/ecs-scheduled-job/variables.tf`
- `modules/ecs-scheduled-job/main.tf`
- `modules/ecs-scheduled-job/task.tf`
- `modules/ecs-scheduled-job/outputs.tf`
- `modules/ecs-scheduled-job/README.md`
- `modules/ecs-scheduled-job/examples/basic/main.tf`
- `tests/contract/test_repository_structure.py`
- `tests/contract/test_scheduled_job_declaration.py`
- `tests/contract/test_scheduled_job_iam.py`
- `tests/contract/test_scheduled_job_task.py`

### Change Log

- 2026-07-24: Created comprehensive Story 2.4 implementation context.
- 2026-07-24: Implemented Story 2.4 task definition, encrypted retained logs,
  Deployment Identity outputs, secret-safe rendering, fixtures, tests, and
  documentation; moved story to review.
- 2026-07-24: Applied all code-review hardening patches and moved story to done.
