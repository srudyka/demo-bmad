---
story_key: 1-14-recover-cell-state-safely
baseline_commit: dca32ae
---

# Story 1.14: Recover Cell State Safely

Status: done

## Story

As a Platform On-call Engineer,
I want an approved, rehearsable Cell recovery workflow,
so that corrupted control data can be restored without launching against a partial or inconsistent platform.

## Acceptance Criteria

1. Given an incident requires Cell data recovery, when the recovery command is authorized, then the workflow records actor, independent approval, reason, affected Cell, restore point, expected RPO/RTO, current Deployment Identity, and recovery generation; missing approval, unsupported source version, or an unverified restore point prevents recovery from starting.
2. Given recovery begins, when containment executes, then launch is disabled before state changes, schedule generations are quiesced, processors that mutate or consume affected state are paused, and in-flight evidence is drained or quarantined without deletion; original tables, queues, CONFIG, logs, and deployment evidence remain intact.
3. Given production DynamoDB PITR is available, when data is restored, then affected namespace, CONFIG, occurrence, checkpoint, outbox, and notification data are restored to new encrypted tables at the approved point rather than overwriting source tables; restored resources use protected tags, deletion safeguards, exact schema/index definitions, and a distinct attributable recovery identity.
4. Given restored tables are available, when integrity validation runs, then schemas, keys, CONFIG hashes, ownership generations, occurrence/task mappings, processed-event deduplication, deadline indexes, outbox references, notification records, and Deployment Identity are checked against the Compatibility Package; incompatible, incomplete, or internally inconsistent results block cutover.
5. Given integrity checks pass, when the Cell is moved to the recovery generation, then versioned Lambda aliases and Cell Contract pointers switch through a reviewed atomic or fail-closed procedure to compatible restored resources; consumers never receive a contract that mixes old and new table identities or unsupported schema versions.
6. Given retained evidence exists after the restore point, when replay begins, then queues are replayed through the same authenticated normalizer and Process Manager paths with original producer identity, event deduplication, and safe-retry limits; unresolved launch evidence past its conservative retry deadline cannot call `RunTask` and instead becomes `AMBIGUOUS`.
7. Given replay and cutover complete, when reconciliation runs, then the materializer rebuilds the expectation horizon, the scanner reconciles every nonterminal occurrence, task and completion evidence are remapped, and pending outbox records are delivered or surfaced; no terminal result is silently overwritten and no referenced CONFIG or task revision is removed.
8. Given the recovered Cell appears consistent, when pre-resume verification runs, then canary scheduling, exactly-one launch, ECS state, completion correlation, deadlines, queue health, logs, metrics, occurrence alerts, aggregate alarms, and notification delivery pass; launch remains disabled until all blocking checks and required approvals succeed.
9. Given recovery verification fails or the new generation regresses, when rollback is invoked, then launch remains disabled and aliases plus Cell Contract pointers return to the prior known-good compatible generation without deleting recovery evidence; failure, actions, resulting state, and next recovery decision remain attributable.
10. Given recovery authority is analyzed, when IAM-positive and IAM-negative tests run, then only the approved recovery role can create restored resources and switch versioned recovery references within the exact Cell; it cannot alter its own trust, bypass approval, assume workload roles, mutate source tables, delete evidence, or operate in another account/Region/Cell.
11. Given a disposable-Cell recovery exercise completes, when measured results are published, then actual data loss, restore duration, replay duration, reconciliation time, alert-verification time, and total RPO/RTO are recorded with known limitations; evidence is suitable for the later pilot gate without claiming automatic cross-Region failover.

## Tasks / Subtasks

- [x] 1. Extend the recovery command and Compatibility Package (AC: 1, 4-6, 10)
  - [x] Extend `contracts/v1/catalogs/commands.json` and the command schema/fixtures with recovery generation, restore-point, RPO/RTO, source-version, verification, and recovery-state fields; preserve the existing UUIDv7/manual identity and forbidden caller-field rules.
  - [x] Add stable recovery states and denial codes for missing approval, unsupported version, restore-point outside PITR, containment incomplete, integrity mismatch, mixed generation, replay unsafe, and verification failure.
  - [x] Make recovery authorization idempotent and append-only in the existing command authorization/audit path; never let a caller supply a recovery generation, Deployment Identity, table ARN, or restored resource name.

- [x] 2. Implement fail-closed containment and recovery orchestration (AC: 1, 2, 8, 9)
  - [x] Extend the authenticated command/evidence path or add a narrowly scoped recovery controller under `runtime/`; do not add a public endpoint or allow the command handler to mutate occurrence state directly.
  - [x] Build an explicit state machine such as `REQUESTED -> APPROVED -> CONTAINING -> CONTAINED -> RESTORING -> VALIDATING -> CUTOVER_READY -> CUTOVER -> REPLAYING -> VERIFYING -> RESUMED`, with terminal `BLOCKED` and `ROLLED_BACK` states.
  - [x] Persist a recovery manifest/checkpoint containing recovery generation, source table identities, target table identities, source Deployment Identity, restore point, phase, actor, approval, timestamps, and failure code. Conditional writes must make retries idempotent.
  - [x] Disable launch before changing table/config references; capture and verify schedule state/generation before disabling it. Pause or disable only the affected Cell processors and event-source mappings, retaining queue/DLQ messages and evidence.
  - [x] Make every phase resumable and fail closed. A failed containment, restore, validation, cutover, replay, or verification phase must leave launch disabled and produce an actionable alert/runbook record.

- [x] 3. Restore and validate DynamoDB control data safely (AC: 3, 4, 5)
  - [ ] Use DynamoDB PITR restore-to-new-table for the namespace registry, configuration registry, occurrence ledger, deadline checkpoint, and notification ledger; restore only the approved point within each table’s actual `EarliestRestorableDateTime`/`LatestRestorableDateTime` range.
  - [ ] Treat the occurrence table’s alert outbox and processed-event records as part of the occurrence-ledger restore contract; do not restore only terminal rows or copy selected records in a way that breaks deduplication/index semantics.
  - [ ] Apply the exact expected key schema, GSIs, stream configuration, PITR/deletion-protection settings, KMS encryption, tags, and recovery-generation metadata. DynamoDB restored tables do not retain tags, so tagging and ABAC/IAM readiness must happen before consumers use them.
  - [ ] Validate table status, key definitions, index names/projections, stream view, encryption key, deletion protection, TTL where applicable, table identity, and compatibility major before proceeding.
  - [ ] Validate cross-table invariants: CONFIG hash/version and owner generation, occurrence `job_id`/`config_version`/`schedule_generation`, task mappings, processed-event identities, deadline GSI records, outbox keys/statuses, notification deduplication IDs, and Deployment Identity.

- [x] 4. Add generation-aware cutover and replay boundaries (AC: 5-7, 9)
  - [ ] Introduce one recovery-generation pointer/manifest that every participating consumer resolves before processing; reject a missing, stale, unsupported, or mixed table-generation set rather than silently falling back to source tables.
  - [ ] Publish immutable versioned Lambda code/config and aliases for the recovery-compatible processor set. Alias or pointer changes must be reviewable, conditional/idempotent, and reversible to the prior known-good generation.
  - [ ] Keep Terraform ownership boundaries intact: the Cell root owns shared tables, queues/DLQs, processors, policies, aliases, and Cell Contract; do not make a recovery script mutate Job-root resources or import another root’s state.
  - [ ] Replay only retained messages/evidence newer than the approved restore point, using original producer metadata and existing normalizer authority checks. Do not fabricate producer/event identities or bypass Process Manager conditional transitions.
  - [ ] Ensure unresolved launch attempts past `safe_retry_deadline` cannot invoke ECS and are reduced to `AMBIGUOUS`; preserve original occurrences and avoid duplicate tasks, terminal overwrites, or duplicate notifications.
  - [ ] Rebuild materializer horizon and scanner checkpoint from the recovered generation, then run bounded outbox reconciliation and surface every unresolved delivery.

- [x] 5. Add pre-resume verification, rollback, IAM, and runbook evidence (AC: 8-11)
  - [ ] Add a credential-free recovery simulator/fakes for containment, restore metadata, integrity failures, mixed generations, cutover, replay, reconciliation, verification failure, and rollback; include IAM-positive and IAM-negative policy assertions.
  - [ ] Add a disposable-Cell exercise or deterministic evidence harness that records restore duration, replay duration, reconciliation duration, alert verification, data loss, and measured RPO/RTO. Clearly label live-AWS and cross-Region limitations.
  - [ ] Add alarms/metrics/logs for recovery phase, blocked recovery, restore failure, integrity failure, mixed generation, replay failure, verification failure, and prolonged containment. Dimensions must remain bounded to Cell, component, generation/state class, and environment.
  - [ ] Update the platform README and a recovery runbook with prerequisites, approval path, exact containment order, PITR point selection, table mapping, integrity checks, replay limits, pre-resume checks, rollback, evidence retention, ownership, escalation, and application-side-effect compensation.
  - [ ] Run `./scripts/validate.sh`, strict mypy, Ruff, all contract/runtime tests, Terraform format/backend-free validation, Checkov/hygiene checks, and `git diff --check`; do not commit state, plans, credentials, or generated recovery artifacts.

## Dev Notes

### Architecture and scope guardrails

- This story implements account/Region-local Cell recovery for the existing platform. Automatic cross-Region failover, active/active replication, application-level data compensation, and destructive source cleanup are out of scope.
- Recovery must follow AD-26: disable launch, pause processors, restore DynamoDB PITR to new tables, validate, switch compatible versioned processors/contract pointers, replay retained queues, rebuild expectations, reconcile, verify alerts, then re-enable launch.
- Process Manager remains the only occurrence-state writer. Recovery must not directly set occurrence state, create attempts, launch ECS tasks, delete source tables, or bypass normalizer authority and deduplication.
- Accepted recovery command evidence means only that recovery intake was authorized. It does not mean restore, replay, cutover, verification, or application recovery completed.
- Keep source tables, queues, DLQs, CONFIG objects, logs, CloudTrail records, deployment evidence, and prior generation pointers intact until recovery and any Job Owner side-effect compensation are confirmed.

### Existing components to reuse

- `runtime/command_handler` already authenticates operator context, validates approval/scope, persists idempotent authorization, and emits canonical command evidence. Extend its `RECOVER` path rather than creating another human-access path.
- `runtime/evidence_normalizer` must remain the authority boundary for command/replay evidence. Reuse its source registration, canonical envelope, quarantine, partial-batch, and stable denial patterns.
- `runtime/process_manager` owns conditional occurrence reduction, safe retry deadlines, ECS launch reservation, task mapping, and terminal/outbox writes. Reuse those paths for replay and reconciliation.
- `runtime/occurrence_materializer`, `runtime/deadline_scanner`, and `runtime/alert_router` already provide horizon rebuild, deadline evidence, outbox delivery/reconciliation, and notification-ledger semantics. Recovery orchestration should call their existing bounded entry points or emit authenticated evidence, not duplicate state machines.
- `modules/ecs-scheduled-job-platform/main.tf` owns Cell tables, queues/DLQs, Lambda functions, IAM, KMS, PITR, deletion protection, aliases/pointers, alarms, and Cell Contract resources. Preserve stable Terraform addresses and add only explicit recovery interfaces/resources.
- `contracts/` is normative. Every recovery manifest, state, table mapping, generation pointer, and event schema must be versioned and checked by the existing manifest/release integrity tests.

### Recovery data and ordering requirements

- The recovery manifest is the durable source of truth for one recovery generation. Include `recovery_id`, `recovery_generation`, Cell/account/Region, actor/session, approval reference, reason, source Deployment Identity, target Deployment Identity, restore point, expected/actual RPO/RTO, source-to-target table map, phase, phase timestamps, validation digest, replay watermark, verification result, rollback generation, and stable failure code.
- Restore point validation must use each table’s actual PITR availability window; a point valid for one table but unavailable for another blocks recovery. Do not silently choose the nearest point or mix restore points unless the manifest records and validates the intentional skew.
- A restored table is a new table. Apply KMS, deletion protection, PITR, tags, TTL, streams, and exact indexes before granting any consumer access. Never use a restored table before it is `ACTIVE` and integrity-validated.
- Generation cutover must be all-or-nothing from the consumer’s point of view. If AWS cannot provide a single atomic multi-resource switch, use a durable pointer with conditional version checks and make each consumer reject an incomplete/mixed generation.
- Queue replay must preserve original message bytes, producer/source metadata, event IDs, and accepted timestamps. Replayed delivery is at-least-once; conditional writes and existing identities must prevent duplicate occurrences, tasks, terminal transitions, and notifications.
- The first recovered canary must remain launch-disabled until all pre-resume checks pass. Verify that a successful canary reaches expectation, launch reservation, ECS evidence, completion correlation, terminal reduction, heartbeat, alerts, and notification delivery.

### AWS/Terraform implementation constraints

- DynamoDB PITR restores to a new table and restored tables do not retain tags; the recovery role must apply tags before ABAC/IAM-dependent access. Use customer-managed KMS encryption and preserve deletion protection/PITR.
- EventBridge Scheduler `UpdateSchedule` requires the complete schedule configuration; read and persist the current schedule before disabling or re-enabling it. Do not use a partial update that resets target, retry, timezone, or flexible-window fields.
- Lambda aliases point to published function versions and can be updated back to the prior version. Do not use weighted traffic for control-plane recovery unless the story adds an explicit fail-closed readiness contract; recovery cutover should route 100% to one compatible generation.
- Do not use Terraform state as the runtime recovery manifest, and do not create ad hoc `null_resource`/provisioner recovery steps. Runtime recovery API calls belong behind the approved recovery role and durable audit evidence; Terraform should own stable contracts, permissions, alarms, and required alias/pointer resources.
- Recovery IAM must be separate from operator diagnosis and workload roles. Scope DynamoDB restore/create/tag/update, Lambda alias/version, SSM/Contract pointer, EventBridge schedule disablement, SQS event-source pause, and read-only validation actions to the exact Cell resources and recovery-generation conditions. It must not grant source-table writes/deletes, ECS launch, `iam:PassRole`, trust/policy mutation, or cross-account access.
- Apply required tags (`Environment`, `Application`, `Service`, `Owner`, `ManagedBy`, plus applicable `Repository`/`CostCenter`) and explicit log retention. Add confused-deputy protections to service policies and keep wildcard actions/resources justified and condition-scoped.

### Testing requirements

- Unit-test restore-point validation, state transitions, idempotent retries, stable denial codes, table-map validation, schema/index/stream checks, cross-table invariants, mixed-generation rejection, and rollback.
- Test no-side-effect failures: missing approval, stale approval, unsupported source/target version, PITR window miss, unavailable table, KMS mismatch, missing tag, index mismatch, CONFIG hash mismatch, owner-generation mismatch, duplicate recovery request, replay after deadline, verification failure, and unauthorized IAM action.
- Test replay with duplicate records and delayed records through the actual normalizer/Process Manager fakes. Assert original producer identity, no caller-supplied IDs, no duplicate launch, no terminal overwrite, and explicit `AMBIGUOUS` for unresolved launch evidence.
- Test the recovery order explicitly: launch disabled before state mutation; processors paused before replay; no consumer sees a mixed generation; launch remains disabled after any failed phase; rollback retains evidence.
- Run the repository validator and record live-AWS limitations. A simulator-only pass must not be described as successful production restore; the disposable-Cell exercise must publish measured RPO/RTO evidence.

### Previous story intelligence

- Story 1.13 established the only approved human command ingress and `RECOVER` command type. Do not add a second operator role, public API, static credential path, or direct table mutation path.
- Story 1.13 review fixes require authenticated caller context, independent approval, exact Cell/job binding, stable sanitized denial codes, idempotent authorization records, partial-batch handling, and negative IAM tests. Recovery must preserve all of them.
- Story 1.12 review fixes require durable evidence, bounded metrics, exact IAM key conditions, generation-safe notification delivery, and explicit rollback/retention notes. Recovery alarms and checkpoints must follow those patterns.
- Recent validation uses `uv 0.11.29`, Python 3.14.6, Terraform 1.15.8, AWS provider 6.54.0, Ruff, mypy, pytest, Checkov, backend-free validation, and repository hygiene. Keep package boundaries self-contained and avoid runtime import cycles.

### Latest technical specifics

- DynamoDB PITR is available only between the table’s `EarliestRestorableDateTime` and `LatestRestorableDateTime`; restore always creates a new table. Restored tables require tags and access-control settings to be reapplied before use.
- EventBridge Scheduler schedules have enabled/disabled state, but `UpdateSchedule` replaces the schedule configuration and requires all required fields; recovery must snapshot the complete schedule before changing state.
- Lambda aliases point to published versions and can be updated to a prior compatible version for rollback. Keep recovery cutover at one fully selected version/generation unless a separate canary contract is implemented.

### Project Structure Notes

- Expected new runtime code belongs under `runtime/` using the existing Lambda package layout and adapter/domain separation; extend `runtime/command_handler` only when the behavior is authenticated command validation, and use a separate recovery package/controller for orchestration if phase state becomes substantial.
- Shared Terraform changes belong in `modules/ecs-scheduled-job-platform/{main.tf,variables.tf,outputs.tf,README.md}` and `examples/basic/*`; do not modify the per-job module to own shared recovery tables or Cell pointers.
- Contract changes belong under `contracts/v1`, with `contracts/manifest.json` and `contracts/releases/1.0.0.json` updated through the existing integrity workflow.
- Operational instructions belong in `docs/runbooks/` and the platform README. Do not commit restore exports, table snapshots, Terraform state, plans, credentials, or generated AWS responses.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-1.14-Recover-Cell-State-Safely`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-26-Recover-the-Cell-Before-Resuming-Launch`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-18-Two-phase-Schedule-Change-and-Rollback`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-20-Delivery-and-Operator-Authority`]
- [Source: `_bmad-output/implementation-artifacts/1-13-authorize-operator-access-and-commands.md`]
- [Source: `_bmad-output/implementation-artifacts/1-12-monitor-cell-health-with-the-canary.md`]
- [Source: `_bmad-output/project-context.md`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]
- [Source: `contracts/v1/catalogs/commands.json`]
- [Source: `modules/ecs-scheduled-job-platform/main.tf`]
- [AWS: DynamoDB point-in-time recovery](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/PointInTimeRecovery_Howitworks.html)
- [AWS: DynamoDB backup and restore](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Backup-and-Restore.html)
- [AWS: EventBridge Scheduler UpdateSchedule](https://docs.aws.amazon.com/scheduler/latest/APIReference/API_UpdateSchedule.html)
- [AWS: Lambda aliases](https://docs.aws.amazon.com/lambda/latest/dg/configuration-aliases.html)

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- AWS recovery API constraints were checked for PITR restore-to-new-table behavior, restored-table tagging, complete Scheduler updates, and Lambda alias rollback.
- Added authenticated RECOVER command fields, fail-closed state machine, Cell-scoped Lambda recovery controller, PITR restore/tag/PITR configuration, generation pointer, manifest table, recovery queue, bounded metrics, and IAM boundaries.
- Added deterministic recovery-order/failure tests, runbook and platform README guidance, and updated contract inventories and release integrity hashes.
- Validation passed: Terraform format/validate, Ruff, mypy, 166 tests plus 199 contract subtests, Checkov (615 platform checks and 98 canary checks), and repository hygiene.
- Scope limitation: this story provides the account/Region-local recovery controller and pointer contract; automatic cross-Region failover and live disposable-Cell measurements remain explicitly out of scope.
- Applied all actionable review fixes: real Cell mapping containment/replay, generation-pointer resolution by consumers, bounded PITR polling, scheduler-safe updates, durable phase checkpoints, idempotent duplicate suppression, prior-pointer rollback, expanded integrity checks, scoped IAM/trust/logging, conditional RECOVER schema requirements, failure metrics, and measured RPO/RTO fields.

### Change Log

- 2026-07-22: Implemented Story 1.14 recovery contracts, orchestration, Terraform resources/IAM/observability, tests, and operational documentation.

### File List

- `_bmad-output/implementation-artifacts/1-14-recover-cell-state-safely.md`
- `contracts/manifest.json`
- `contracts/releases/1.0.0.json`
- `contracts/v1/catalogs/commands.json`
- `contracts/v1/catalogs/metrics-alerts.json`
- `contracts/v1/schemas/command.schema.json`
- `docs/runbooks/cell-recovery.md`
- `modules/ecs-scheduled-job-platform/main.tf`
- `modules/ecs-scheduled-job-platform/README.md`
- `modules/ecs-scheduled-job-platform/outputs.tf`
- `runtime/alert_router/src/alert_router/handler.py`
- `runtime/command_handler/src/command_handler/domain.py`
- `runtime/command_handler/src/command_handler/recovery.py`
- `runtime/command_handler/src/command_handler/recovery_handler.py`
- `runtime/deadline_scanner/src/deadline_scanner/handler.py`
- `runtime/evidence_normalizer/src/evidence_normalizer/handler.py`
- `runtime/log_ingestor/src/log_ingestor/handler.py`
- `runtime/occurrence_materializer/src/occurrence_materializer/handler.py`
- `runtime/process_manager/src/process_manager/handler.py`
- `runtime/command_handler/tests/test_command_domain.py`
- `runtime/command_handler/tests/test_recovery.py`

### Review Findings

- [x] [Review][Patch] Terraform deploys real Cell schedule and event-source mapping configuration, making containment and replay effective [modules/ecs-scheduled-job-platform/main.tf:2977-2998]
- [x] [Review][Patch] Cutover publishes a generation pointer resolved by state-consuming Lambda adapters [runtime/command_handler/src/command_handler/recovery_handler.py:184-211]
- [x] [Review][Patch] Verification validates the generation pointer and all restored tables without invoking an unsupported Process Manager payload [runtime/command_handler/src/command_handler/recovery_handler.py:213-248]
- [x] [Review][Patch] PITR restore waits with bounded polling for each target table to become `ACTIVE` [runtime/command_handler/src/command_handler/recovery_handler.py:123-164]
- [x] [Review][Patch] Scheduler containment and resume pass only supported complete schedule fields [runtime/command_handler/src/command_handler/recovery_handler.py:52-72]
- [x] [Review][Patch] Recovery manifests checkpoint phase transitions and suppress duplicate command retries [runtime/command_handler/src/command_handler/recovery.py:170-231; runtime/command_handler/src/command_handler/recovery_handler.py:407-430]
- [x] [Review][Patch] Rollback restores the captured prior pointer and records rollback failure distinctly [runtime/command_handler/src/command_handler/recovery_handler.py:276-298; runtime/command_handler/src/command_handler/recovery.py:208-231]
- [x] [Review][Patch] Integrity validation covers schema, operational metadata, encryption, PITR, deletion protection, and required tags [runtime/command_handler/src/command_handler/recovery_handler.py:180-260]
- [x] [Review][Patch] Recovery IAM is restricted to recovery-table ARNs, exact Cell mappings, and Cell consumer roles [modules/ecs-scheduled-job-platform/main.tf:2890-3025]
- [x] [Review][Patch] Recovery trust uses source-account protection and the controller can write its dedicated log group [modules/ecs-scheduled-job-platform/main.tf:2870-2885,3020-3045]
- [x] [Review][Patch] Canonical RECOVER commands require recovery request fields in the schema [contracts/v1/schemas/command.schema.json:45-175]
- [x] [Review][Patch] Recovery rejection and rollback failures are checkpointed with stable failure codes [runtime/command_handler/src/command_handler/recovery.py:208-231]
- [x] [Review][Patch] Recovery replay/reconciliation wiring, failure metrics, and measured timing fields are implemented [runtime/command_handler/src/command_handler/recovery_handler.py:230-248,449-540; contracts/v1/catalogs/metrics-alerts.json:39-75]
