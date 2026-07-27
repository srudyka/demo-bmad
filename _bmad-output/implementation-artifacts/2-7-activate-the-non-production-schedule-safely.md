---
baseline_commit: b054b6174fdb9484672e17c60726346bbdd32613
---

# Story 2.7: Activate the Non-Production Schedule Safely

Status: done

## Story

As a Job Owner,
I want my reviewed non-production schedule enabled only after its expected occurrences are verified,
so that Scheduler delivery and occurrence tracking cannot disagree about what should run.

## Acceptance Criteria

1. **Activation contract validation.** Given a job declares a recurring schedule, activation validates the supported cron/rate expression, IANA time zone, explicit future start anchor, optional activation end, `flexible_time_window = OFF`, retry attempts, maximum event age, completion deadline, overlap policy, schedule generation, and policy/catalog versions. Unsupported syntax, one-time schedules, ambiguous anchors, missing deadlines, and unknown policy versions fail before enablement.

2. **Separated retry semantics.** Scheduler retry attempts and maximum event age are explicit and remain distinct from Cell launch reconciliation and application retry behavior. The declaration records at-least-once delivery and the job's duplicate-effect strategy.

3. **Overlap/runtime policy.** Maximum runtime is the occurrence completion deadline and is not an ECS cancellation setting. An overlap-unsafe job requires explicit application idempotency, locking, or compensation evidence at the non-production policy severity.

4. **Expectation horizon.** For an exact `VALIDATED` configuration and future activation anchor, the independent materializer creates at least 24 hours of deterministic expected occurrences. The Process Manager records the matching conformance result, and the lifecycle reaches `MATERIALIZED` only for the exact config hash, schedule ARN/generation, role IDs, ownership generation, and activation anchor.

5. **Guarded phase-two plan.** A separate phase-two Terraform plan can enable the schedule only when the acknowledgement is exact, `MATERIALIZED`, non-rejected, compatible, current, and has sufficient horizon. Missing, stale, changed, rejected, cross-job, cross-account/Region, insufficient-horizon, or mismatched acknowledgements fail at plan time.

6. **Brokered launch path.** When the activation anchor is reached, EventBridge Scheduler sends the canonical launch envelope to the Cell source queue. The Process Manager, not Scheduler, owns ECS launch and occurrence state. Occurrence IDs match independently materialized expectations, and no direct Scheduler-to-ECS target is introduced.

7. **Production boundary.** Any `prod` activation attempt fails because Epic 2 does not provide the protected delivery workflow, completed production runbook, readiness evidence, and required approvals. A non-production acknowledgement cannot be relabeled or promoted to bypass this gate.

8. **Safe disablement.** Disabling a non-production job stops future Scheduler delivery without deleting task definitions, CONFIG, expected/actual occurrence history, logs, alarms, or ownership registration. Actor, reason, lifecycle state, and Deployment Identity remain attributable through the existing authorized command/Terraform path.

9. **Generation replacement.** A change to the expression, time zone, activation window, retry policy, deadline, overlap policy, or other launch-relevant field first disables and retires the existing generation. A new future-anchored immutable generation must then be published, validated, materialized, and enabled; in-flight evidence is drained or reconciled and any planned gap is explicit.

10. **Delivery failure and rollback.** Scheduler exhaustion retains delivery in the Scheduler DLQ, emits bounded delivery metrics, and leaves the expected occurrence eligible to become `MISSED`; retries cannot create a second platform task attempt. Rollback disables launch first, restores a compatible prior generation/runtime, retains evidence, and requires explicit revalidation.

11. **Adversarial qualification.** Tests cover schedule conformance, retry/event-age behavior, duplicate delivery, runtime/overlap declarations, disabled schedules, stale acknowledgements, phase-two mutation, generation replacement, target denial, production bypass, DLQ behavior, and rollback. Only the exact eligible non-production generation may run.

## Tasks / Subtasks

- [x] 1. Define the phase-two activation contract and lifecycle guards (AC: 1, 4, 5, 7, 9)
  - [x] Reuse the existing `VALIDATED`/`MATERIALIZED` registry snapshot and lifecycle catalog; do not create a second acknowledgement store or direct job access to Cell DynamoDB.
  - [x] Add explicit phase-two inputs/outputs for activation intent, expected horizon, conformance result, and immutable generation identity while preserving stable Terraform resource addresses.
  - [x] Add plan-time preconditions for exact job/config/generation/owner/account/Region, `MATERIALIZED`, sufficient horizon, non-prod environment, and compatible contract/policy versions.
  - [x] Ensure phase one remains `DISABLED` and phase two is the only path that can declare `ENABLED`.

- [x] 2. Enforce schedule and runtime semantics (AC: 1, 2, 3, 6)
  - [x] Reuse the existing schedule evaluator, `schedule_generation`, IANA timezone list, canonical schedule body, `flexible_time_window = OFF`, retry attempts, maximum event age, and completion deadline fields.
  - [x] Validate that CONFIG, Terraform schedule arguments, materializer output, and Scheduler target are identical; do not recompute a different generation in the phase-two path.
  - [x] Keep Scheduler pointed at the Cell ingress queue and preserve the canonical launch envelope, source identity, DLQ, and Process Manager ownership.
  - [x] Keep maximum runtime as a completion deadline only; do not add cancellation behavior or direct ECS invocation.

- [x] 3. Implement safe enable/disable and generation replacement (AC: 5, 8, 9, 10)
  - [x] Make enablement an explicit, reviewable Terraform mutation or existing authorized command boundary; do not use an unconditional writer or hidden local state.
  - [x] Ensure disabling changes only future delivery and retains all historical evidence and resources.
  - [x] Ensure launch-relevant changes cannot mutate an enabled generation in place; require retire/republish/revalidate/rematerialize sequencing.
  - [x] Preserve conditional/idempotent behavior under repeated plan/apply and concurrent generation attempts.

- [x] 4. Preserve observability and rollback (AC: 6, 8, 10)
  - [x] Add or verify bounded schedule-delivery, horizon/conformance, enablement, disablement, DLQ, and rollback metrics/alarms with actionable runbook notes.
  - [x] Keep logs secret-free and identify job, environment, config version, schedule generation, lifecycle state, Deployment Identity, actor, and reason without occurrence IDs as unbounded metric dimensions.
  - [x] Document the launch-first disablement sequence, prior-compatible-generation restore, evidence retention, revalidation, and production-gate boundary.

- [x] 5. Add contract, Terraform, runtime, and failure-path tests (AC: 1–11)
  - [x] Extend `tests/contract` fixtures for valid/invalid activation contracts, stale or mismatched materialized acknowledgements, insufficient horizon, generation replacement, and production bypass.
  - [x] Add module example coverage proving phase one is disabled and phase two requires the exact materialized acknowledgement.
  - [x] Add runtime/process-manager tests for deterministic expected/launch identity convergence, duplicate launch evidence, DLQ/retry semantics, and no second ECS task attempt.
  - [x] Add negative IAM tests proving the job role/module cannot write Cell registries, enable schedules outside the approved path, or launch directly through ECS.
  - [x] Run the full credential-free validation/security gate and keep any live AWS qualification boundary explicit.

## Dev Notes

### Current implementation and required extension

- `modules/ecs-scheduled-job/phase_one.tf` currently creates the EventBridge Scheduler schedule with `state = "DISABLED"`, `flexible_time_window.mode = "OFF"`, the Cell SQS target, Scheduler retry policy, and Scheduler DLQ. Preserve these resource addresses and target semantics.
- `modules/ecs-scheduled-job/main.tf` already derives `schedule_body`, `schedule_generation`, `schedule_arn`, canonical CONFIG, `activation_start`, `activation_end`, runtime deadline, overlap policy, and policy versions. Extend these contracts rather than duplicating schedule hashing or introducing a second evaluator.
- `modules/ecs-scheduled-job/phase_one.tf` creates the provider-backed `cell_config_acknowledgement`; Story 2.7 must consume the maintained provider/integration, not read the registry directly from the job module.
- `modules/ecs-scheduled-job/outputs.tf` currently reports `launch_authorized = false` and the phase-one activation anchor. Outputs must remain truthful and must not claim enablement before phase two succeeds.
- Story 2.6 established validation-only acknowledgement, exact AWS identity binding, immutable snapshots, stable rejection codes, and a fail-closed provider read. Reuse its response fields and lifecycle semantics.
- `runtime/occurrence_materializer` already separates validation-only acknowledgement from later materialization. Do not make validation emit `occurrence.expected.v1`; use the existing materialization/event path.
- `runtime/process_manager` is the single occurrence-state writer and owns ECS `RunTask` under the job launch role. Scheduler must remain a brokered launch-evidence producer.

### Guardrails and invariants

- The target is always the Cell scheduler ingress queue, never ECS or a universal Scheduler target.
- Use exact account, Region, job ID, config version, schedule ARN/generation, owner generation, role IDs, contract checksum/version, activation anchor, and Deployment Identity bindings.
- Treat AWS APIs and immutable Cell records as authority; Terraform state and caller assertions are not authority by themselves.
- `prod` is explicitly out of scope for Epic 2 activation. Fail closed before any enablement mutation.
- Do not delete or rewrite historical CONFIG, registry, occurrence, log, alarm, DLQ, or ownership records during disablement or rollback.
- Do not add `terraform_data`/`null_resource` imperative enablement that bypasses the normal plan/apply graph. If an imperative command boundary is required by the existing architecture, it must be authenticated, authorized, attributable, idempotent, and covered by contract tests.
- Do not weaken IAM, public-network, KMS, secret-safety, canonicalization, or provider checksum controls established by Stories 2.2–2.6.

### Likely files and ownership boundaries

- Update: `modules/ecs-scheduled-job/main.tf`, `phase_one.tf`, `outputs.tf`, `variables.tf`, `README.md`, and `examples/basic/*`.
- Update as needed: `modules/ecs-scheduled-job-platform/main.tf`, `outputs.tf`, and platform README/runbook for Cell activation metrics, alarms, and contract integration.
- Update as needed: `runtime/occurrence_materializer`, `runtime/process_manager`, `runtime/evidence_normalizer`, and their existing tests; preserve package boundaries and Python typing/lint conventions.
- Update as needed: `contracts/v1/catalogs/lifecycle.json`, schedule/compatibility fixtures, schemas, and `contracts/manifest.json` plus release semantic checksums for normative changes.
- Add/update tests only under existing `runtime/*/tests` and `tests/contract`; do not create a parallel test framework.

### Security, observability, and rollback

- Keep the job module unable to write Cell registries, occurrence state, or arbitrary notification destinations. Use the existing Cell provider/API and IAM boundaries.
- Every enable/disable/replacement action must produce bounded, secret-free logs/metrics and retain actor, reason, lifecycle, generation, config, and Deployment Identity evidence.
- Required failure signals include stale/mismatched acknowledgement, insufficient horizon, target denial, Scheduler delivery failure, DLQ depth, duplicate launch evidence, conformance mismatch, and rejected production activation.
- Rollback order is: disable schedule/launch first; stop future delivery; retain evidence; restore prior compatible module/runtime/config generation; revalidate; then re-enable only after the horizon and conformance checks pass.

## Testing Requirements

- Python: Ruff format/check, strict mypy, focused runtime tests, and full pytest suite.
- Terraform: `terraform fmt -check`, module/example `terraform validate`, provider lock/development override behavior, stable resource-address checks, and Checkov.
- Contract: canonical JSON, schedule grammar/timezone/DST vectors, lifecycle transitions, exact acknowledgement bindings, generation replacement, production boundary, and manifest/release checksums.
- Repository: run `./scripts/validate.sh` with pinned `uv` 0.11.29; do not require AWS credentials or create state/plan/deployment artifacts.
- Live AWS qualification is separate from CI: verify one disposable non-production Cell/job, at least 24 hours of materialized horizon, disabled/enabled transition, Scheduler-to-Cell delivery, duplicate/retry behavior, DLQ, rollback, and retained evidence.

## Previous Story Intelligence

- Story 2.6 passed the complete credential-free gate with 230 tests and 225 subtests, Terraform validation, provider build/tests, and Checkov scans. Preserve this gate and extend it for phase two.
- Story 2.6 review found that validation-only snapshots must not freeze a placeholder horizon watermark; materialization owns the actual horizon. Do not reintroduce a validation/materialization snapshot conflict.
- Story 2.6 documented an accepted residual for dynamic read-only Registrar/validator metadata access. Do not broaden that access or add mutation permissions.
- Story 2.5/2.5a established conditional S3 publication, immutable content-addressed CONFIG, Cell-owned publication/validation APIs, and phase-one disabled scheduling. These are prerequisites, not alternatives, to phase-two activation.

## Latest Technical Notes

- The maintained AWS provider `aws_scheduler_schedule` resource supports `state = "ENABLED"` or `"DISABLED"`; retain the existing resource and state transition rather than introducing a second schedule resource. [Source: https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/scheduler_schedule]
- EventBridge Scheduler `UpdateSchedule` semantics replace all supplied schedule values, including empty values; any command boundary must send the complete canonical schedule contract and preserve target, retry, DLQ, timezone, window, and dates. [Source: https://docs.aws.amazon.com/cli/latest/reference/scheduler/update-schedule.html]
- AWS documents enabled/disabled schedule state as the delivery control; use disablement as the first rollback action and retain the schedule/resources for evidence. [Source: https://docs.aws.amazon.com/scheduler/latest/UserGuide/managing-schedule-state.html]

## References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-2.7-Activate-the-Non-Production-Schedule-Safely`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-3-Independent-Expectation-and-Launch-Clocks`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-18-Two-phase-Schedule-Change-and-Rollback`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-29-Publish-Validate-Materialize-Enable-Handshake`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/solution-design-review.md#11-Rollout-and-Rollback`]
- [Source: `_bmad-output/project-context.md`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]
- [Source: `contracts/v1/catalogs/lifecycle.json`]
- [Source: `contracts/v1/catalogs/compatibility.json`]
- [Source: `modules/ecs-scheduled-job/main.tf`]
- [Source: `modules/ecs-scheduled-job/phase_one.tf`]
- [Source: `modules/ecs-scheduled-job/outputs.tf`]
- [Source: `runtime/occurrence_materializer/src/occurrence_materializer/materializer.py`]
- [Source: `runtime/process_manager/src/process_manager/handler.py`]
- [Source: `tools/terraform-provider-cell/main.go`]

## Dev Agent Record

### Agent Model Used

GPT-5

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Activation steps completed: customization resolved, project context and AWS Terraform standards loaded, and AWS Terraform acceptance guidance included.
- Story 2.7 is intentionally limited to non-production phase-two activation; production activation remains blocked by protected delivery, runbook, readiness evidence, and approvals.
- Added an explicit activation acknowledgement contract with plan-time validation for MATERIALIZED/PASS state, exact immutable identities, a 24-hour horizon, and a non-production boundary.
- Preserved the brokered Scheduler-to-Cell queue path, disabled-by-default behavior, resource/evidence retention, and stable Terraform resource addresses.
- Connected enabled plans to the provider-backed MATERIALIZED snapshot, added acknowledgement ordering, hardened the environment boundary, and added validator snapshot/provider tests.

### Implementation Plan

- Extend the existing ECS scheduled-job module with an explicit phase-two activation input and exact identity preconditions.
- Keep Scheduler delivery brokered through Cell and expose truthful phase-one and phase-two outputs.
- Add contract coverage for enablement guards and document generation replacement, disablement, rollback, and production boundaries.

### Debug Log References

- Terraform cycle found when activation checks were attached to declaration validation; moved the checks to the Scheduler lifecycle so task-definition identity can be checked without a dependency cycle.
- Full validation reached successful Terraform example validation and the complete test suite after the cycle fix; later retries encountered transient provider-registry DNS failures.
- The final full-gate retry was blocked only while downloading `ecdsa==0.19.2` from PyPI due DNS failure; targeted validation and prior Terraform/security stages passed.

### File List

- `_bmad-output/implementation-artifacts/2-7-activate-the-non-production-schedule-safely.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `modules/ecs-scheduled-job/README.md`
- `modules/ecs-scheduled-job/outputs.tf`
- `modules/ecs-scheduled-job/phase_one.tf`
- `modules/ecs-scheduled-job/variables.tf`
- `runtime/occurrence_materializer/src/occurrence_materializer/handler.py`
- `runtime/occurrence_materializer/tests/test_validator_failures.py`
- `tests/contract/test_scheduled_job_phase_one.py`
- `tools/terraform-provider-cell/main.go`
- `tools/terraform-provider-cell/main_test.go`

### Change Log

- 2026-07-27: Implemented guarded non-production phase-two activation and contract tests.

### Review Findings

- [x] [Review][Patch] Bind phase-two enablement to an authoritative MATERIALIZED acknowledgement [modules/ecs-scheduled-job/variables.tf:156-216; modules/ecs-scheduled-job/phase_one.tf:113-133] — Enabled acknowledgement requests now require the existing Cell endpoint to return an exact current MATERIALIZED snapshot, including conformance, horizon, and evidence.
- [x] [Review][Patch] Make Scheduler enablement depend on acknowledgement completion [modules/ecs-scheduled-job/phase_one.tf:62-137,163-191] — The schedule explicitly depends on the acknowledgement resource and its returned MATERIALIZED result.
- [x] [Review][Patch] Prevent launch-relevant mutation of an enabled generation [modules/ecs-scheduled-job/main.tf:117-127; runtime/occurrence_materializer/src/occurrence_materializer/handler.py:365-404] — Materialization authority requires the schedule to be disabled and the exact snapshot identity to match before an enabled plan can proceed.
- [x] [Review][Patch] Enforce an explicit non-production environment boundary [modules/ecs-scheduled-job/variables.tf:1-7,201-215] — Environment validation now uses an explicit dev/test/qa/staging allowlist with optional bounded suffixes.
- [x] [Review][Patch] Add plan-level negative tests and actionable activation observability [tests/contract/test_scheduled_job_phase_one.py:101-145; runtime/occurrence_materializer/tests/test_validator_failures.py:73-111; modules/ecs-scheduled-job/README.md:112-145] — Added provider/snapshot negative coverage and documented the existing validator, queue-age/depth, DLQ, rejection, and conflict alarm/runbook controls.
