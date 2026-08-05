---
baseline_commit: 51842d8
---

# Story 2.5: Publish Phase-One Job Resources and CONFIG

Status: done

## Story

As an Application Engineer,
I want my job root to publish immutable launch resources while the schedule remains disabled,
so that the Cell can review exact AWS identities and configuration before any occurrence executes.

## Acceptance Criteria

1. With a valid reservation, task revision, IAM roles, log group, and private-network handoff, phase-one Terraform creates exactly one job-owned EventBridge Scheduler schedule in `DISABLED` state and one job-owned Scheduler delivery role. The schedule targets the exact Cell scheduler ingress queue through the approved target shape; it must not target ECS directly, enable launch, create shared Cell resources, or mutate the runtime ledger.
2. The delivery role trusts only `scheduler.amazonaws.com`, the target account, and the exact Cell schedule-group ARN. Its send permissions are limited to the exact Cell scheduler ingress queue and scheduler DLQ ARNs. Negative fixtures reject wrong account, wrong schedule group, stale role, cross-job queue, unrelated event type, and unapproved SQS actions/resources.
3. The disabled schedule contains the normalized recurring expression, IANA time zone, explicit future start anchor and activation window, `flexible_time_window.mode = "OFF"`, bounded retry attempts, maximum event age, and the canonical scheduled-time launch envelope required by the Compatibility Package. One-time schedules, unsupported expressions, ambiguous anchors, mutable payload identity, and missing retry semantics fail planning.
4. The module renders the canonical secret-free CONFIG body with job identity, ownership generation, normalized schedule/generation, activation window, task-definition revision ARN, ECS cluster, private subnets, security groups, public-IP-disabled policy, execution/task/launch roles, runtime deadline, overlap policy, log group, notification metadata, Deployment Identity, policy/contract versions, and only approved secret references. It must not include secret values or caller-generated occurrence IDs.
5. `config_version` is the lowercase SHA-256 of the exact canonical CONFIG body bytes. The CONFIG object key is exactly `jobs/<job_id>/config/<config_version>.json`; identical canonical inputs produce identical versions, and any launch-relevant change produces a new immutable generation.
6. Phase-one publication writes one encrypted CONFIG object only to the reserved job inbox prefix, uses create-only semantics, and reports lifecycle `PUBLISHED`. The job apply identity cannot overwrite another version, write another job prefix, or claim `VALIDATED`, `MATERIALIZED`, or `ENABLED`.
7. IAM-negative tests prove the apply identity can manage only this module's task, roles, logs, optional security group, disabled schedule, delivery role, and exact CONFIG prefix. It cannot write Cell namespace/registry/occurrence/outbox/notification/queue/processor/contract/protected state or another job's resources.
8. Outputs expose schedule ARN, schedule group ARN, delivery-role ARN and Role ID, task revision, launch-role ARN, CONFIG hash/key, owner generation, activation anchor, Deployment Identity, and lifecycle `PUBLISHED`, with no secret values. Outputs state that publication is not Cell acknowledgement or launch authorization.
9. Repeated plan/apply with unchanged launch inputs is idempotent: resource addresses remain stable and no extra schedule or CONFIG generation is created. Any address migration uses reviewed `moved` blocks or explicit migration guidance.
10. Rollback keeps the schedule disabled, reconciles partial job-owned resources, retains prior task revisions, CONFIG objects, logs, and ownership evidence, and never deletes shared Cell resources or implicitly enables a prior generation.

## Tasks / Subtasks

- [x] 1. Extend the job module interface for phase-one schedule and publication inputs (AC: 1, 3, 4, 9)
  - [x] Add validated IANA time zone, future start anchor, activation start/end, Scheduler retry attempts, maximum event age, and CONFIG schema/contract inputs using existing compatibility catalog values.
  - [x] Preserve Story 2.1–2.4 variables, stable resource addresses, reservation preconditions, private-network outputs, secret-mode behavior, and Deployment Identity.
  - [x] Validate recurring-only schedule semantics, unambiguous RFC 3339 UTC anchors/windows, bounded retry values, and overlap/runtime compatibility before resource creation.

- [x] 2. Create the job-owned Scheduler delivery role and disabled schedule (AC: 1, 2, 3, 7, 9)
  - [x] Add one delivery role with the existing permissions boundary and exact Scheduler trust conditions.
  - [x] Add one `aws_scheduler_schedule` in the Cell schedule group with `state = "DISABLED"`, exact normalized timing, retry policy, DLQ, and future activation anchor.
  - [x] Target the exact Cell scheduler ingress queue using the approved Scheduler target/envelope; do not create a direct ECS target or enable the schedule.
  - [x] Scope `sqs:SendMessage` to only the Cell scheduler ingress and DLQ ARNs, with no wildcard or cross-job resource.

- [x] 3. Build and validate canonical CONFIG (AC: 4, 5, 8, 9)
  - [x] Construct a deterministic secret-free CONFIG body from sorted/normalized values and the exact task/log/network/IAM handoff outputs.
  - [x] Derive lowercase `config_version` from canonical body bytes and publish the exact `jobs/<job_id>/config/<config_version>.json` key.
  - [x] Include approved secret locators only; exclude values, raw container JSON, occurrence IDs, mutable aliases, and caller-controlled identity fields.
  - [x] Validate the rendered object against `contracts/v1/schemas/config.schema.json` and add positive/negative canonicalization fixtures.

- [x] 4. Publish exactly one encrypted CONFIG object with least privilege (AC: 5, 6, 7, 10)
  - [x] Use the Cell Contract's config-inbox integration and encryption metadata; require create-only/object-lock semantics and prevent overwrite.
  - [x] Add only the job-side publication permission for its exact reserved prefix and content-addressed key; do not grant registry or Cell-state writes.
  - [x] Preserve prior CONFIG versions and task revisions during retries, replacement, and rollback.

- [x] 5. Publish phase-one outputs and documentation (AC: 8, 10)
  - [x] Output schedule/delivery-role identities, CONFIG hash/key, ownership generation, activation anchor, Deployment Identity, and `PUBLISHED` lifecycle.
  - [x] Document disabled-by-default behavior, Cell validation boundary, retry/DLQ semantics, idempotency, failure modes, validation commands, and rollback procedure in the module README.
  - [x] Keep Scheduler, CONFIG acknowledgement, materialization, alarms, dashboards, and Cell-owned resources within their existing ownership boundaries.

- [x] 6. Add contract, IAM, static, and module tests (AC: 1–10)
  - [x] Add schedule fixtures for exact group/account/queue trust, disabled state, timing, retry, DLQ, future anchor, and forbidden direct ECS target.
  - [x] Add CONFIG fixtures for canonical hash/key determinism, secret safety, required fields, ownership generation, and launch-relevant version changes.
  - [x] Add IAM positive/negative tests for stale roles, wrong account/group, cross-job queue/prefix, overwrite attempts, and protected Cell resources.
  - [x] Add stable-address/idempotency/rollback assertions and keep examples synthetic, credential-free, and secret-free.

- [x] 7. Run all required quality gates (AC: 10)
  - [x] Run Terraform format/validate for the module and example, Ruff, strict mypy, contract/runtime tests, Checkov, repository hygiene, manifest/checksum validation, and `git diff --check`.
  - [x] Keep credential-free validation separate from live AWS qualification and record any unavailable provider/network checks explicitly.

### Review Findings

- [x] [Review][Resolved] Use a Cell publisher API/provider that supports the required `If-None-Match: *` create-only precondition. The dedicated publisher role and required job identity tag are wired, but AWS provider 6.54's `aws_s3_object` resource cannot send that header [modules/ecs-scheduled-job/phase_one.tf:98]
- [x] [Review][Patch] Gate CONFIG publication on declaration and Cell-contract validation [modules/ecs-scheduled-job/phase_one.tf:98]
- [x] [Review][Patch] Render CONFIG secret references as the structured provider/version locator objects required by the normative schema [modules/ecs-scheduled-job/main.tf:143]
- [x] [Review][Patch] Include complete launch provenance in CONFIG, including Deployment Identity metadata, contract/policy versions, network policy version, and notification runbook metadata [modules/ecs-scheduled-job/main.tf:118]
- [x] [Review][Patch] Require canonical millisecond UTC timestamps and a genuinely future activation anchor [modules/ecs-scheduled-job/variables.tf:122]
- [x] [Review][Patch] Validate schedule expressions against the Compatibility Package grammar and reject unknown IANA time zones before planning [modules/ecs-scheduled-job/variables.tf:100]
- [x] [Review][Patch] Apply the exclusive activation end to the Scheduler resource [modules/ecs-scheduled-job/phase_one.tf:49]
- [x] [Review][Patch] Grant the Scheduler delivery role narrowly scoped KMS data-key permissions for the encrypted Cell queues, with queue encryption-context conditions [modules/ecs-scheduled-job/phase_one.tf:34]
- [x] [Review][Patch] Make CONFIG hashing and its test vector use the repository’s RFC8785/NFC canonicalization contract [modules/ecs-scheduled-job/main.tf:115]
- [x] [Review][Patch] Add effective IAM-negative coverage for wrong-job prefixes, protected Cell state, overwrite attempts, stale identities, and cross-account/group inputs [tests/contract/test_scheduled_job_phase_one.py:10]
- [x] [Review][Patch] Remove stale Story 2.4 ownership claims from the README and correct the example timestamp format [modules/ecs-scheduled-job/README.md:7]
- [x] [Review][Patch] Guard schedule-group ARN parsing and document a disabled replacement/migration path for the `prevent_destroy` schedule [modules/ecs-scheduled-job/main.tf:116]

#### Review pass: 2026-07-24

- [x] [Review][Patch] Make the publisher role assumable by the Terraform provider's same-account invocation identity; the role currently trusts only `lambda.amazonaws.com`, so the provider's explicit STS assumption fails before publication. [modules/ecs-scheduled-job-platform/main.tf:1042; tools/terraform-provider-cell/main.go:137]
- [x] [Review][Patch] Correct the private API endpoint path; the contract endpoint uses stage `publish` while the API resource path is also `publish`, requiring `/publish/publish` rather than the currently advertised `/publish`. [modules/ecs-scheduled-job-platform/main.tf:1167; modules/ecs-scheduled-job-platform/main.tf:1218]
- [x] [Review][Patch] Enforce the complete Registrar ownership state before publication, including `lifecycle`, `tombstoned`, and `transfer_state`, not only account, Region, and generation. [runtime/config_publisher/src/config_publisher/handler.py:93]
- [x] [Review][Patch] Bind the job's declared `config_publisher_role_arn` to the provider configuration and enforce the exact effective role; it is currently validated but not wired into `cell_config_publication`. [modules/ecs-scheduled-job/phase_one.tf:112]
- [x] [Review][Patch] Add a deterministic API Gateway deployment trigger so publisher Lambda/integration changes produce a new deployed stage instead of leaving stale code live. [modules/ecs-scheduled-job-platform/main.tf:1212]
- [x] [Review][Patch] Reject activation windows where `activation_end` is not strictly after `activation_start`. [modules/ecs-scheduled-job/variables.tf:142]
- [x] [Review][Patch] Validate actual IANA time-zone availability rather than accepting syntactically shaped but nonexistent zones. [modules/ecs-scheduled-job/variables.tf:123]
- [x] [Review][Patch] Require `protocol_version` in the runtime request and validate the submitted contract version against the discovered Cell Contract rather than accepting any `1.x.y` value. [runtime/config_publisher/src/config_publisher/domain.py:121]
- [x] [Review][Patch] Validate response `contract_version` and `ownership_generation` against the publication request before accepting provider success. [tools/terraform-provider-cell/main.go:102]
- [x] [Review][Patch] Implement provider refresh behavior for a missing CONFIG object instead of making `Read` a no-op that preserves stale Terraform state. [tools/terraform-provider-cell/main.go:44]
- [x] [Review][Patch] Prevent publisher rejection/error bodies from echoing arbitrary response data into Terraform diagnostics. [tools/terraform-provider-cell/main.go:99]
- [x] [Review][Patch] Extend the response schema to model stable rejection responses as well as successful publication responses. [contracts/v1/schemas/config-publisher-response.schema.json:8]
- [x] [Review][Patch] Convert malformed Registrar `owner_generation` data into a stable authorization rejection instead of an internal error. [runtime/config_publisher/src/config_publisher/handler.py:105]
- [x] [Review][Patch] Cover early validation and authorization failures with bounded metrics/structured telemetry and add the required validation and latency alarm coverage. [runtime/config_publisher/src/config_publisher/handler.py:120; modules/ecs-scheduled-job-platform/main.tf:1246]
- [x] [Review][Patch] Add effective IAM-negative tests for the configured apply/provider roles, exact CONFIG prefixes, overwrite attempts, and protected Cell resources rather than only text/fixture assertions. [tests/contract/test_scheduled_job_phase_one.py:8]
- [x] [Review][Patch] Restore exact provider compatibility assertions and explicit child-module validation coverage instead of relying on generic substring checks and a validation skip. [scripts/validate.py:214; tests/contract/test_terraform_compatibility.py:25]

## Dev Notes

### Scope and ownership

Story 2.5 is the phase-one publication boundary. It may add the job-owned
Scheduler delivery role, disabled Scheduler schedule, and job-side CONFIG
publication/handoff. It must not create or mutate the Cell-owned queues, DLQ,
schedule group, S3 bucket, DynamoDB registry, namespace reservation, runtime
ledger, alarms, dashboards, or occurrence state. Story 2.6 owns Cell validation
and acknowledgement; Story 2.7 owns safe activation.

The prior story leaves `modules/ecs-scheduled-job` with declaration, IAM,
private networking, task definition, retained encrypted logs, notification
metadata, reservation receipt, and Deployment Identity outputs. Extend those
interfaces; do not duplicate roles, task definitions, networking, or Cell
resources. The existing Cell Contract is discovered from SSM and exposes
`integrations.config_inbox`, `integrations.scheduler_ingress`,
`integrations.scheduler_dlq`, and `integrations.scheduler_schedule_group`.

### Canonical CONFIG contract

Use `contracts/v1/schemas/config.schema.json` as normative. Required top-level
fields are `schema_version`, `config_version`, and `config`. Required CONFIG
fields include `job_id`, `owner_generation`, `schedule`, `schedule_arn`,
`schedule_generation`, `scheduler_delivery_role_id`, `task_definition_arn`,
`cluster_arn`, private `network`, exact `role_arns`,
`completion_window_seconds`, normalized `overlap_policy`, `logs`,
`notification_target_arn`, `secret_references`, and `deployment_identity_id`.
The canonical body is secret-free and must be hashed from its exact canonical
JSON bytes, not from Terraform state or an unordered representation.

Use the registered key contract exactly: `jobs/<job_id>/config/<config_version>.json`.
The Cell-owned config inbox policy already demonstrates exact SHA-256 key
scoping, KMS encryption-context conditions, and create-only `s3:if-none-match`
semantics; consume its published integration and do not broaden it.

### Scheduler and IAM guardrails

EventBridge Scheduler must remain disabled. The target is the Cell scheduler
ingress queue, not ECS. Use the exact schedule-group ARN from the Cell Contract
as the trust `aws:SourceArn` condition and the exact target account as
`aws:SourceAccount`. The delivery role may send only to the contract's
Scheduler ingress and DLQ ARNs. The scheduled envelope must retain the AWS
scheduled-time authority for later normalization; callers never supply an
Occurrence ID.

The existing `contracts/v1/fixtures/iam/cases.json` already contains positive
and negative scheduler trust/action examples. Reuse its fixture vocabulary and
extend it only when a new contract field is required. Keep the delivery role
separate from the job launch, ECS execution, task, Terraform apply, and Cell
roles.

### Schedule semantics

Only the Compatibility Package's recurring `rate(...)` and supported six-field
`cron(...)` forms are valid. Require an explicit IANA time zone, RFC 3339 UTC
start anchor, inclusive activation start, optional exclusive activation end,
`flexible_time_window.mode = "OFF"`, and bounded retry/max-event-age values.
Use `contracts/v1/catalogs/schedules.json` and schedule fixtures for evaluator
version `schedule-evaluator/1.0.0`, IANA release `2026b`, and generation rule.
Do not silently coerce local timestamps, one-time expressions, `LATEST`,
missing retry values, or ambiguous activation windows.

### Terraform and testing guidance

Use stable resource addresses and explicit descriptions/validations. Prefer
`aws_scheduler_schedule` and IAM data policy documents. Preserve task/log
`skip_destroy` behavior. Never use provisioners, `null_resource`, wildcard IAM,
secret-bearing `jsonencode`, mutable image tags, or direct shared-state reads.
Static tests alone are insufficient: render or fixture-evaluate schedule,
CONFIG, IAM, hash, S3 key, secret-safety, idempotency, and rollback behavior.

### Previous story intelligence

Story 2.4 required review hardening for secret-mode separation, controlled
metadata collisions, exact input validation, KMS identity validation, stable
task revisions, and fixture coverage. Preserve those fixes. Its validation
pattern passed Terraform module/example validation, 204 tests with 218
subtests, scoped Ruff, strict mypy, and diff checks. The full repository
validator may require the pinned `uv` tool and network/provider cache.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-2.5-Publish-Phase-One-Job-Resources-and-CONFIG`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-5-Versioned-Event-and-Configuration-Contracts`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-12-Explicit-IAM-Boundaries`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-15-Terraform-State-and-Cell-Discovery`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-18-Two-phase-Schedule-Change-and-Rollback`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-25-Single-Terraform-Owner-per-Integration-Edge`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-28-Globally-Registered-Job-Ownership`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-29-Publish-Validate-Materialize-Enable-Handshake`]
- [Source: `contracts/v1/schemas/config.schema.json`]
- [Source: `contracts/v1/catalogs/schedules.json`]
- [Source: `contracts/v1/fixtures/iam/cases.json`]
- [Source: `modules/ecs-scheduled-job-platform/main.tf`]
- [Source: `_bmad-output/project-context.md`]
- [AWS EventBridge Scheduler schedule configuration](https://docs.aws.amazon.com/scheduler/latest/UserGuide/managing-schedule.html)
- [AWS Scheduler flexible time windows](https://docs.aws.amazon.com/scheduler/latest/UserGuide/managing-schedule-flexible-time-windows.html)
- [AWS Scheduler dead-letter queues](https://docs.aws.amazon.com/scheduler/latest/UserGuide/configuring-schedule-dlq.html)
- [Terraform `aws_scheduler_schedule`](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/scheduler_schedule)

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Context built from Epic 2, Story 2.4 implementation/review record, project
  context, AWS Terraform standard, architecture spine, CONFIG schema,
  schedule catalog, IAM fixtures, Cell platform outputs, and current module.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Implemented phase-one disabled Scheduler delivery, exact Cell queue/DLQ IAM,
  deterministic schedule generation, secret-free canonical CONFIG hashing, and
  encrypted content-addressed S3 publication.
- Added phase-one outputs, README ownership/rollback guidance, schedule and
  CONFIG fixtures, and boundary/IAM/static tests.
- Validation: Terraform module/example valid; 209 tests and 219 subtests pass;
  scoped Ruff format/lint, strict mypy, Checkov (117 passed, 0 failed after the
  documented CKV2_AWS_5 module-boundary skip), manifest integrity, and
  `git diff --check` pass. Live AWS delivery and Cell acknowledgement remain
  separately qualified.

### File List

- `_bmad-output/implementation-artifacts/2-5-publish-phase-one-job-resources-and-config.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `contracts/manifest.json`
- `contracts/v1/fixtures/phase-one/cases.json`
- `modules/ecs-scheduled-job/variables.tf`
- `modules/ecs-scheduled-job/main.tf`
- `modules/ecs-scheduled-job/phase_one.tf`
- `modules/ecs-scheduled-job/outputs.tf`
- `modules/ecs-scheduled-job/README.md`
- `modules/ecs-scheduled-job/examples/basic/main.tf`
- `tests/contract/test_repository_structure.py`
- `tests/contract/test_scheduled_job_declaration.py`
- `tests/contract/test_scheduled_job_iam.py`
- `tests/contract/test_scheduled_job_task.py`
- `tests/contract/test_scheduled_job_phase_one.py`

### Change Log

- 2026-07-24: Created comprehensive Story 2.5 implementation context.
- 2026-07-24: Implemented and validated phase-one resources and CONFIG;
- 2026-07-24: Applied 11 review patches and wired the dedicated publisher
  identity. One create-only publication item remains deferred because AWS
  provider 6.54 cannot send `If-None-Match: *` from `aws_s3_object`.
  moved story to review.
