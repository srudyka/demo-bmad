---
epic: 4
story: 4.8
title: Rehearse Job and Cell Recovery
status: done
baseline_commit: b9dbb9d
---

# Story 4.8: Rehearse Job and Cell Recovery

Status: done

## Story

As an On-Call Engineer,
I want rehearsed recovery procedures for job generations and shared Cell state,
so that rollback restores controlled service without duplicating work or misrepresenting application recovery.

## Acceptance Criteria

1. When a newly activated job generation is found defective, authorized operators disable new launches for that generation before infrastructure changes; in-flight tasks, unresolved occurrences, alert obligations, and possible side effects are inventoried and assigned explicit drain, quarantine, preserve, or compensate actions.
2. When rollback is planned against a known-good Deployment Identity, the exact version-pinned configuration produces a fresh reviewable plan bound to target account, Region, Environment, state, source, target manifest, and approvers. Stale plans, mutable images, direct state edits, schedule edits, and failed-plan reuse are rejected.
3. After the known-good generation is restored, CONFIG acknowledgement and activation complete, scheduling resumes only after the expected-occurrence horizon, task definition, IAM, networking, logging, completion contract, alarms, notification route, and generation ownership are verified. Old and new generations cannot launch the same occurrence.
4. If the failed generation launched tasks or changed application data, rollback preserves occurrence history and explicitly records unresolved, duplicate-risk, and partially completed work. Terraform or infrastructure recovery never claims to reverse application effects; owner-approved reconciliation or compensation is required.
5. If shared Cell state is corrupted, deleted, or inconsistent, recovery stops or fences new launch mutations, preserves forensic evidence, drains or quarantines ingress, maintains an independent alert path, and binds scope and action to an incident identity and immutable audit record.
6. When a valid point-in-time recovery point is selected, ledger, CONFIG, expectation, and alert state are restored into fresh encrypted tables or stores rather than overwriting damaged resources. Schemas, indexes, streams, TTL, PITR, encryption, tags, resource policies, deletion protection, and the Compatibility Package are verified before use.
7. When restored resources pass structural checks, traffic is redirected through the approved stable indirection or contract using an atomic or explicitly ordered switch that prevents split-brain writers. A failed cutover returns to previous isolated resources without losing preserved evidence.
8. When the recovery point precedes valid platform events, durable Scheduler, ECS, completion, command, and alert evidence is replayed through existing idempotent interfaces and missing future expectations are rematerialized. Occurrence IDs, terminal-state precedence, task correlation, and alert deduplication prevent duplicate launches or erased outcomes.
9. During Cell recovery, accepted, running, stopped, and unknown ECS tasks are matched to restored occurrences and affected Deployment Identities before launch is re-enabled. Ambiguity remains visible and requires an operator decision; it never triggers automatic replacement.
10. After restore and replay, the canary proves scheduling, exactly-one launch, logs, completion, deadlines, occurrence alerts, Cell alarms, operator commands, and retained audit history. Pending alert obligations are delivered with stable identity or explicitly reconciled with attributable disposition.
11. The rehearsal measures actual recovery time and recovery-point loss against documented RTO/RPO assumptions. An exceeded objective, unreconciled occurrence, duplicate task, lost alert, broken audit chain, or untested compensation blocks production readiness.
12. If any recovery step fails, launch remains disabled, the last coherent resources remain isolated and recoverable, and escalation identifies the next authorized restore point or forward fix. Repeated recovery cannot destroy prior backups, evidence, or the ability to determine application impact.
13. Published rehearsal evidence satisfies the Story 4.3 job rollback, Cell restore, replay, reconciliation, compensation, verification, RPO/RTO, and failed-recovery categories; it is sanitized, checksum-bound, access-controlled, and tied to the exact release candidate.

## Tasks / Subtasks

- [x] Define the recovery rehearsal contract and scenario matrix (AC: 1-13)
  - [x] Extend the existing recovery/readiness contracts and fixtures; do not create a second occurrence, generation, Deployment Identity, or recovery state-machine format.
  - [x] Bind every manifest and evidence item to incident, actor/session, approval, Cell, account, Region, Environment, source commit, workflow, exact release candidate, Compatibility Package, current and known-good Deployment Identities, generation, restore point, RPO/RTO, and immutable checksums.
  - [x] Keep credential-free contract evaluation separate from protected disposable-Cell/live qualification. Never accept caller-supplied passed flags, counters, checksums, result strings, artifact paths, or readiness claims as proof.
  - [x] Represent job rollback, Cell restore, cutover failure, replay, ECS ambiguity, alert reconciliation, compensation, RTO/RPO, and cleanup as individual controls with explicit negative cases.

- [x] Qualify job-generation rollback (AC: 1-4)
  - [x] Extend `scripts/deployment_evidence.py` and its contract tests for disable-first ordering, generation retirement, in-flight/task/occurrence/alert/side-effect inventory, explicit dispositions, fresh-plan enforcement, target bindings, and normal approval controls.
  - [x] Verify the plan is freshly generated from version-pinned configuration and the known-good Deployment Identity; reject mutable images, stale or failed plans, direct state edits, schedule edits, target mismatches, no-op rollbacks, and unreviewed address changes.
  - [x] Reuse authoritative occurrence, ECS task, completion, deadline, outbox, notification, and Deployment Identity evidence. Preserve terminal precedence and classify conflicting or unresolved work as `AMBIGUOUS` rather than repairing it by assertion.
  - [x] Record application side effects and Job Owner reconciliation/compensation disposition separately from infrastructure recovery; include catch-up/backfill decisions and latest acceptable business completion where applicable.

- [x] Implement and qualify Cell containment and fresh-resource restore (AC: 5-7, 12)
  - [x] Extend `runtime/command_handler/src/command_handler/recovery.py` and `recovery_handler.py` only through the existing fail-closed phase machine: containment precedes mutation, every phase checkpoints evidence, and failures block resume and invoke safe rollback.
  - [x] Confirm authorized recovery disables schedules/event sources and fences launch mutations before table, pointer, or state changes; preserve queues, DLQs, logs, audit records, backups, and forensic evidence and maintain an independent alert path.
  - [x] Restore every required Cell table/store to a fresh encrypted target using one restore point available to all sources. Verify key schema, indexes, streams, TTL, PITR, KMS key, tags, deletion protection, resource policies, and Compatibility Package before access.
  - [x] Implement or qualify stable indirection and ordered/atomic cutover so no consumer or writer can observe mixed generations. Exercise failed cutover/backout while retaining both source and recovery inventories and evidence.
  - [x] Keep all live recovery qualification account/Region/Environment-scoped to an approved disposable Cell or protected test target; never mutate production state during credential-free tests.

- [x] Replay durable evidence and reconcile ECS/application state (AC: 3, 4, 8-10)
  - [x] Replay Scheduler, ECS lifecycle, completion, command, deadline, and alert evidence through the existing normalizer, reducers, Process Manager, and alert outbox/notification ledger interfaces.
  - [x] Rematerialize missing future expectations and preserve occurrence IDs, processed-event deduplication, terminal-state precedence, stable alert identity, task correlation, and generation ownership under duplicate, reordered, delayed, and conflicting evidence.
  - [x] Reconcile accepted/running/stopped/unknown tasks against restored occurrences and Deployment Identities before launch resumes. Unknown or unsafe launch outcomes remain operator-visible and cannot call `RunTask` automatically.
  - [x] Verify pending alert obligations are delivered once with their original identity or have an attributable reconciled disposition; verify logs, completion, deadlines, Cell alarms, operator commands, and retained audit history with unique evidence identities, not aggregate counts.

- [x] Measure objectives, readiness, cleanup, and operations (AC: 10-13)
  - [x] Calculate restore, replay, reconciliation, alert verification, and total recovery durations plus the exact recovered point and data/event loss; compare actual RTO/RPO with job and Cell assumptions.
  - [x] Project each recovery control into Story 4.3 readiness evidence, preserving control IDs, provenance, freshness, source-run attestation, target bindings, sanitization, checksum sealing, access control, and exact release-candidate identity.
  - [x] Block readiness for exceeded objectives, duplicate launch, unreconciled occurrence, lost alert, broken audit chain, untested compensation, failed verification, failed cleanup, or ambiguous evidence.
  - [x] Exercise failed recovery and repeated recovery attempts: launch remains disabled, prior resources/evidence remain recoverable, and the runbook identifies next restore point, forward fix, escalation, retention, and application-impact review.
  - [x] Update `docs/runbooks/cell-recovery.md`, `docs/runbooks/operator-commands.md`, and the canary runbook only for implemented behavior, including prerequisites, evidence queries, RPO/RTO measurement, compensation ownership, cleanup inventories, and rollback/backout steps.

## Dev Notes

### Existing implementation to read and extend

- `runtime/command_handler/src/command_handler/recovery.py` and `recovery_handler.py`: the existing Cell-scoped recovery phases, PITR restore adapter, validation digest, pointer cutover, replay, reconciliation, verification, and fail-closed rollback boundary.
- `scripts/deployment_evidence.py`: `validate_recovery_plan`, `plan_recovery_execution`, `validate_recovery_execution`, and verification helpers for fresh plans, target bindings, evidence reconciliation, and pre-apply ordering.
- `.github/workflows/production-recovery.yml`: protected ordered recovery gate and access-controlled recovery evidence publication. Workflow-dispatch inputs are untrusted and must be validated against authoritative evidence.
- `docs/runbooks/cell-recovery.md` and `docs/runbooks/operator-commands.md`: current disable-first, fresh-table, single-pointer, replay, ambiguity, compensation, and backout procedure.
- `scripts/readiness_gate.py`, `scripts/production_bundle.py`, and existing Story 4.3-4.7 qualification runners: exact bindings, freshness, cleanup, manifest sealing, protected workflow provenance, and per-control readiness projection.
- `runtime/job_registrar`, `runtime/process_manager`, `runtime/evidence_normalizer`, `runtime/alert_router`, `runtime/deadline_scanner`, and `runtime/config_publisher`: authoritative generation, occurrence, task, completion, deadline, alert, and CONFIG boundaries. Extend these rather than inventing parallel identity or replay paths.
- `modules/ecs-scheduled-job-platform/main.tf`, `variables.tf`, and `outputs.tf`: existing Cell tables, PITR, encryption, deletion protection, recovery pointer, alarms, and outputs. Any Terraform change must preserve least privilege, private networking, tags, retention, and no-secret/no-state rules.
- `contracts/v1/schemas/command.schema.json`, `readiness-evidence.schema.json`, `occurrence-record.schema.json`, `processed-event.schema.json`, `alert.schema.json`, and the related lifecycle, reducer, keys/correlation, metrics/alerts, and recovery fixtures.

### Recovery invariants

1. Containment and evidence preservation precede every resource mutation.
2. Recovery is bound to an incident, actor, approval, Cell, target, generation, Deployment Identity, restore point, and exact release candidate.
3. Restore creates fresh encrypted resources; damaged resources are never overwritten.
4. A single coherent generation owns writers and launches; split-brain and duplicate occurrence launch are blocking failures.
5. Infrastructure rollback does not reverse application data; unresolved effects require owner-approved reconciliation or compensation.
6. Unknown ECS launch state is visible and must not be auto-replaced.
7. Every phase is fail-closed, auditable, checksum-bound, and resumable only after independent verification.
8. Cleanup and evidence retention are explicit inventories; a cleanup claim based only on counts or caller prose is invalid.

### AWS and toolchain notes

- Use DynamoDB PITR restore-to-new-table semantics and verify post-restore table settings before cutover: [RestoreTableToPointInTime](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_RestoreTableToPointInTime.html).
- Use authoritative ECS task state/stop-code/container evidence for reconciliation: [ECS task state change events](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_task_events.html).
- Preserve the repository-pinned toolchain: uv `0.11.29`, Python `3.14.6`, Terraform `1.15.8`, AWS provider `6.54.0`, Ruff `0.15.21`, mypy `2.3.0`, pytest `9.1.1`, and Checkov `3.3.8`.
- Do not create credentials, Terraform state, plans, raw application payloads, production identifiers, or unbounded metric dimensions in fixtures or published evidence.

### Dependencies and scope

Dependencies are Stories 4.3 through 4.7 plus the Cell Contract, CONFIG registry, occurrence ledger, Process Manager, alert router, Deployment Identity, and Compatibility Package foundations. This story qualifies and completes recovery rehearsal boundaries; it does not automate pilot measurement (4.9) or publish the pilot launch decision (4.10).

### Rollback notes

The rehearsal itself must be disable-first and confined to an approved disposable or protected test target. If any step fails, leave launch disabled, retain isolated source/recovery resources and sanitized evidence, restore only the last coherent pointer through the approved backout path, and escalate for the next restore point or forward fix. Do not delete recovery evidence until application impact and compensation decisions are complete.

## References

- [Epic 4 Story 4.8](/Users/srudyka/slower/demo-bmad/_bmad-output/planning-artifacts/epics.md:2809)
- [Project context](/Users/srudyka/slower/demo-bmad/_bmad-output/project-context.md)
- [AWS Terraform implementation standard](/Users/srudyka/slower/demo-bmad/_bmad/custom/standards/aws-terraform-implementation.md)
- [Architecture spine](/Users/srudyka/slower/demo-bmad/_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md:174)
- [PRD recovery and rollback requirements](/Users/srudyka/slower/demo-bmad/_bmad-output/planning-artifacts/prds/prd-demo-bmad-2026-07-13/prd.md:301)
- [Story 4.7 implementation context](/Users/srudyka/slower/demo-bmad/_bmad-output/implementation-artifacts/4-7-prove-security-and-delivery-boundaries.md)
- [Cell recovery runbook](/Users/srudyka/slower/demo-bmad/docs/runbooks/cell-recovery.md)
- [Protected production recovery workflow](/Users/srudyka/slower/demo-bmad/.github/workflows/production-recovery.yml)
- [Recovery state machine](/Users/srudyka/slower/demo-bmad/runtime/command_handler/src/command_handler/recovery.py)
- [Recovery evidence validators](/Users/srudyka/slower/demo-bmad/scripts/deployment_evidence.py:546)

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Implementation Plan

- Add a credential-free, schema-backed recovery evidence evaluator with exact
  release/target bindings, per-control results, derived task/occurrence/alert
  checks, and explicit cleanup inventories.
- Extend trusted rollback validation with authoritative inventory
  dispositions, immutable image references, and schedule-edit rejection.
- Harden the existing Cell recovery adapter for identity-bound replay and
  reconciliation, safe pointer backout, concurrent checkpoint protection, and
  operational recovery alarms.
- Update recovery/operator runbooks and validate focused contracts, runtime
  behavior, Terraform formatting/validation/security, and repository-wide
  regression tests.

### Debug Log References

- Initial recovery contract tests failed at collection because the evaluator
  did not exist; implemented the evaluator and fixture contract.
- Recovery evidence tests initially classified the safe
  `credential-free-fixture` mode and cleanup marker as sensitive; reordered
  fail-closed structural checks and exempted the safe mode enum.
- Contract manifest validation exposed the required release semantic-surface
  and release-artifact checksum updates; both were refreshed from exact bytes.
- Runtime handler tests exposed unsafe `INITIAL` pointer fallback and
  unbound replay/reconciliation payloads; both were corrected and re-tested.

### Completion Notes List

- Loaded project context, AWS Terraform standards, Epic 4 story contract, architecture recovery invariants, PRD rollback/recovery requirements, current recovery implementation, runbooks, protected workflow, readiness gate, and prior Story 4.3-4.7 lessons.
- Preserved the existing recovery state machine, evidence boundary, authoritative identity model, and fail-closed semantics as implementation constraints.
- Added recovery evidence contracts, fixtures, credential-free evaluator/runner, readiness projection, and exact release manifest registration.
- Added disable-first rollback inventory validation with explicit drain/quarantine/preserve/compensate dispositions, compensation ownership, immutable image checks, and schedule-edit rejection.
- Bound replay and reconciliation invocations to recovery identity, rejected unknown prior-pointer backout, protected manifest checkpoints against generation overwrite, and added recovery queue age/DLQ alarm definitions.
- Updated Cell recovery and operator runbooks with evaluator usage, RPO/RTO measurement, compensation boundaries, and safe backout semantics.
- No live AWS resources, production state, credentials, Terraform state, or plans were used or created.
- Validation passed: `406 passed, 373 subtests`, Terraform format/validate for affected roots and examples, Checkov job module (118), platform Cell (798), canary fixture (98), Ruff format/lint, mypy, and repository hygiene.
- Terraform emitted existing deprecation warnings for `aws_region.name` and DynamoDB `hash_key`/`range_key`; no new validation failures remain.

### Change Log

- 2026-08-03: Implemented recovery rehearsal contracts, rollback inventory controls, runtime recovery hardening, operational alarms, and runbook guidance; full validation passed.

### File List

- `_bmad-output/implementation-artifacts/4-8-rehearse-job-and-cell-recovery.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `contracts/manifest.json`
- `contracts/releases/1.0.0.json`
- `contracts/v1/fixtures/recovery/cases.json`
- `contracts/v1/schemas/recovery-evidence.schema.json`
- `docs/runbooks/cell-recovery.md`
- `docs/runbooks/operator-commands.md`
- `modules/ecs-scheduled-job-platform/main.tf`
- `runtime/command_handler/src/command_handler/recovery_handler.py`
- `runtime/command_handler/tests/test_recovery_handler.py`
- `scripts/deployment_evidence.py`
- `scripts/recovery_qualification.py`
- `scripts/run_recovery_qualification.py`
- `tests/contract/test_recovery_inventory.py`
- `tests/contract/test_recovery_qualification.py`
- `tests/contract/test_contract_schemas.py`

### Review Findings

- [x] [Review][Patch] Recovery qualification accepts caller-asserted control results and normalizes individual control digests instead of validating the underlying evidence, so fabricated or altered passed controls can produce a passed readiness projection [scripts/recovery_qualification.py:312]
- [x] [Review][Patch] The credential-free recovery runner uses a hard-coded fallback evaluation timestamp and copies caller bindings while only overriding commit/run fields; it does not enforce freshness or emit a protected live-attestation requirement before publishing passed readiness [scripts/run_recovery_qualification.py:54]
- [x] [Review][Patch] Recovery timing is measured with `finished_at` captured before `execute_recovery`, and RPO is calculated as wall-clock time from restore point rather than validated data/event watermark loss [runtime/command_handler/src/command_handler/recovery_handler.py:482]
- [x] [Review][Patch] Replay invokes `RECOVERY_REPLAY_FUNCTIONS`, but the deployed Terraform environment configures no replay function ARNs, leaving production replay as mapping re-enable only [modules/ecs-scheduled-job-platform/main.tf:4127]
- [x] [Review][Patch] Recovery pointer cutover and rollback use unconditional SSM overwrite after a non-atomic read; concurrent cutovers or a stale rollback can clobber a newer generation [runtime/command_handler/src/command_handler/recovery_handler.py:270]
- [x] [Review][Patch] Manifest checkpoints allow any same-generation write, so a conflicting checkpoint for the same recovery generation can overwrite the authoritative record [runtime/command_handler/src/command_handler/recovery_handler.py:387]
- [x] [Review][Patch] The disable-first inventory validator is not wired into the recovery runner, workflow, or readiness path, and the evaluator accepts empty observations; the required task/occurrence/alert inventory therefore does not block readiness when absent [scripts/deployment_evidence.py:639; scripts/recovery_qualification.py:322]
- [x] [Review][Patch] Recovery-plan image references default to an empty list, allowing a plan without any immutable image digest despite the acceptance requirement for exact version-pinned configuration [scripts/deployment_evidence.py:596]
- [x] [Review][Patch] Runtime structural verification does not validate resource policies or the Compatibility Package, while the evidence evaluator can satisfy those controls from caller-provided string markers [runtime/command_handler/src/command_handler/recovery_handler.py:334; scripts/recovery_qualification.py:250]
- [x] [Review][Patch] The recovery evidence contract does not require Deployment Identity matching, authoritative ECS stop/container evidence, or an operator decision for ambiguous task-to-occurrence reconciliation [scripts/recovery_qualification.py:181]
- [x] [Review][Patch] Sanitized recovery evidence validates only that retained artifacts are a list and contain no forbidden markers; it lacks an explicit retained-artifact allowlist/type and sensitive-field policy [scripts/recovery_qualification.py:323]
- [x] [Review][Patch] Protected security qualification accepts any completed successful workflow whose path matches `*qualification.yml`, rather than the exact protected producer workflow, allowing provenance substitution [.github/workflows/security-boundary-qualification.yml:80]
- [x] [Review][Patch] Security attestation checks HMAC over caller-supplied evidence and a caller-supplied proof digest but never recomputes or dereferences the proof against live IAM/security results, so a key holder can mint a passing attestation without the claimed protected observation [scripts/security_qualification.py:255]
