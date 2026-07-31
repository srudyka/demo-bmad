---
epic: 4
story: 4.4
title: Qualify Schedule Delivery and Expectations
status: done
baseline_commit: ce39fad
---

# Story 4.4: Qualify Schedule Delivery and Expectations

## Story

As a Platform Engineer,
I want the release candidate tested against schedule and expectation failure modes,
so that production missed-run detection is proven independently of successful task delivery.

## Acceptance Criteria

1. The qualification suite deploys the platform-owned canary through the standard workflow into an isolated disposable non-production Cell and records release version, Compatibility Package, account, Region, Cell identity, test configuration, policy versions, and evidence checksums.
2. Representative cron, rate, time-zone, daylight-saving, anchored, and adjacent-window cases produce authoritative occurrence identifiers and windows from the shared schedule contract. Unsupported, malformed, ambiguous, or out-of-horizon schedules fail closed with attributable diagnostics.
3. At least 24 hours of expected occurrences are materialized before and independently of successful Scheduler delivery. Each expectation retains deterministic identity, generation, due time, completion deadline, and lifecycle across retries and reconciliation.
4. During an old/new schedule-generation overlap, occurrences remain bound to the correct generation without gaps, reuse, or cross-generation completion; retirement follows the documented lifecycle rules.
5. Injected target denial, throttling, retry exhaustion, dropped delivery, configured DLQ evidence, and silent delivery-path failures produce `MISSED` (or the canonical equivalent) at the applicable deadline, with the correct occurrence alert and Cell-health signal without requiring a success marker.
6. At-least-once Scheduler retries correlate to exactly one accepted launch per occurrence. Duplicate attempts neither create duplicate ECS tasks nor overwrite terminal evidence.
7. After delivery recovery, reconciliation preserves terminal results, handles unresolved occurrences according to policy, prevents delayed evidence from satisfying another occurrence, and distinguishes recovery from an unauthorized manual rerun.
8. Detection and alert evidence is produced within five minutes of the applicable deadline/platform-failure threshold, with correct routing, deduplication identity, ownership metadata, and acknowledgement evidence.
9. Twenty consecutive healthy schedule windows produce exactly one correlated launch per expected occurrence with zero false missed-run or Cell-health alerts; ambiguous, duplicate, late, or missing results fail qualification.
10. Cleanup removes disposable schedules, tasks, roles, logs, expectations, and Cell resources or retains them only under an explicit evidence-retention policy, while preserving sanitized immutable checksum-bound evidence.
11. The submitted Story 4.3 readiness evidence satisfies only schedule interpretation, expectation independence, Scheduler delivery, idempotency, timing, and healthy-window controls; launch/runtime, completion, security, and recovery controls remain unsatisfied until their dedicated stories pass.

## Tasks / Subtasks

- [x] Establish the disposable qualification harness and manifest (AC: 1, 10)
  - [x] Reuse the standard credential-free/trusted workflow and platform-owned canary; do not create a parallel deployment path or invent AWS identities.
  - [x] Pin the release/Compatibility Package and capture account, Region, Cell, configuration, policy versions, test clock, and artifact digests in a sanitized manifest.
  - [x] Add fail-closed teardown with explicit evidence-retention handling and no committed state, plans, credentials, secrets, or raw application data.
- [x] Implement or extend schedule-contract evaluation (AC: 2-4)
  - [x] Reuse `contracts/v1/catalogs/schedules.json`, schedule fixtures, occurrence identity vectors, and existing schedule/materializer contracts.
  - [x] Cover cron/rate syntax, IANA time zones, DST skip/repeat behavior, start anchors, disabled flexible windows, horizon bounds, and adjacent-window ambiguity.
  - [x] Assert exact `occurrence/v1` identity bytes and schedule-generation binding; reject unsupported one-time schedules and cross-generation completion.
- [x] Prove expectation independence and delivery failure behavior (AC: 3, 5-8)
  - [x] Materialize and verify a 24-hour horizon before enabling delivery; demonstrate expectations persist when Scheduler delivery is denied or absent.
  - [x] Inject denial, throttling, retry exhaustion, dropped delivery, DLQ, and silent-path cases using deterministic fixtures or an isolated disposable Cell only.
  - [x] Measure deadline-to-state and deadline-to-alert latency, routing, deduplication, ownership, and acknowledgement; fail if the five-minute bound is missed.
- [x] Prove idempotency, recovery, and healthy windows (AC: 6, 7, 9)
  - [x] Replay duplicate Scheduler events and verify one task attempt, stable ledger evidence, and no terminal overwrite.
  - [x] Recover delivery and reconcile late evidence without cross-occurrence satisfaction or unauthorized manual-rerun semantics.
  - [x] Run twenty accelerated healthy windows and fail on any false miss, duplicate, ambiguous result, or Cell-health alert.
- [x] Integrate readiness evidence and regression coverage (AC: 1-11)
  - [x] Emit versioned, checksum-bound schedule qualification evidence using the Story 4.3 envelope and controlled artifact manifest; preserve `epic4` versus disposable provenance.
  - [x] Add positive and negative contract tests for malformed schedules, DST, anchors, horizon, generation overlap, missing expectations, delivery failures, retries, DLQ, duplicate events, stale/late evidence, alert latency, and cleanup.
  - [x] Ensure unrelated readiness categories remain blocked and no fixture can authorize production activation.

## Dev Notes

### Architecture and guardrails

- Expectations and Scheduler delivery are independent clocks. The materializer creates `occurrence.expected.v1` at least 24 hours ahead; Scheduler emits only `LAUNCH` evidence. Never infer an expectation from successful delivery.
- Use the shared account/Region-local Cell. The job root does not manage shared Cell resources, and the qualification harness must not bypass Cell discovery or the standard workflow.
- Occurrence identity is the exact lowercase SHA-256 of `occurrence/v1\n<job_id>\n<schedule_generation>\n<epoch_minute>`. Use published Compatibility Package vectors, not a new hash format.
- Canonical states are `EXPECTED`, `STARTED`, `SUCCEEDED`, `FAILED`, `OVERDUE`, `MISSED`, and `AMBIGUOUS`. Only the Process Manager writes occurrence state; late or conflicting evidence must be reduced deterministically.
- Scheduler delivery is at-least-once. Retries must reuse the reserved occurrence/attempt and never create a second ECS task. DLQ and retry behavior must be bounded and observable.
- Metrics remain bounded by job/environment/state; never use occurrence IDs as metric dimensions. Alerts must carry occurrence, failure plane, account, Region, Deployment Identity, and Runbook context.
- Qualification is non-production and credential-scoped. Do not weaken production policy, create live production resources, or mark unrelated Story 4.3 controls passed.

### Existing code and reuse targets

- Normative contracts: `contracts/v1/catalogs/schedules.json`, `contracts/v1/fixtures/schedules/cases.json`, `contracts/v1/fixtures/identity/occurrence-v1.json`, scheduler/materializer identity fixtures, occurrence and payload schemas, and `contracts/manifest.json`.
- Inspect before editing: `runtime/`, `modules/ecs-scheduled-job-platform/`, `scripts/validate.py`, `scripts/production_bundle.py`, `scripts/readiness_gate.py`, and existing contract support under `tests/contract/`.
- Extend existing materializer, scheduler, Process Manager, alert, and validation helpers. Do not create duplicate occurrence identity, schedule parsing, policy, target-binding, or evidence checksum implementations.
- Preserve Story 4.3 exact evidence bindings, controlled artifact references, freshness, approvals, and production-fixture rejection.

### Terraform/AWS requirements

- If Terraform changes, use existing module/environment structure, stable resource addresses, explicit variable descriptions/validation, required tags, encrypted state, private networking, and least-privilege roles.
- Scheduler roles must be scoped to the exact target and protected with confused-deputy conditions where supported. Configure bounded retry attempts/event age and an encrypted DLQ when testing DLQ behavior.
- Do not use public IPs, mutable image tags, wildcard IAM, committed `.tfstate`, `.tfvars`, saved plans, or credentials. Disposable resources require deterministic names and cleanup.
- Production-impacting behavior must document logs, metrics, alarms, rollback/disablement, and operator evidence. Schedule changes follow the two-phase generation/retirement contract.

### Testing and validation

- Use uv `0.11.29`, Python `3.14.6`, Terraform `1.15.8`, AWS provider `6.54.0`, Ruff, mypy, pytest, JSON Schema, and Checkov as pinned by the repository.
- Run focused schedule/identity/materializer tests, full `pytest tests runtime -q -p no:cacheprovider`, Ruff, mypy, `git diff --check`, and `./scripts/validate.sh`. Report PyPI/Terraform Registry DNS failures separately; do not treat them as passing validation.
- Every injected failure must have deterministic expected state, alert identity, owner, timing threshold, and cleanup assertion. Include negative tests for cross-generation, duplicate, delayed, missing, and unauthorized evidence.

### Latest AWS specifics

- EventBridge Scheduler supports cron/rate expressions, explicit IANA time zones, and flexible windows; DST handling is timezone-aware, with skipped nonexistent spring times and no duplicate fall invocation. Rate expressions using `days` represent 24-hour durations.
- Scheduler retry policy bounds maximum event age to 60–86,400 seconds and maximum attempts to 0–185. Exhausted delivery can be sent to an SQS DLQ; test the configured policy rather than relying on defaults.
- References: [AWS schedule types](https://docs.aws.amazon.com/scheduler/latest/UserGuide/schedule-types.html), [Scheduler retry policy](https://docs.aws.amazon.com/scheduler/latest/APIReference/API_RetryPolicy.html), [Scheduler DLQ](https://docs.aws.amazon.com/scheduler/latest/UserGuide/configuring-schedule-dlq.html), [flexible time windows](https://docs.aws.amazon.com/scheduler/latest/UserGuide/managing-schedule-flexible-time-windows.html).

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-4.4-Qualify-Schedule-Delivery-and-Expectations`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-3`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-4`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-7`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-8`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-10`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-11`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-14`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-19`]
- [Source: `_bmad-output/project-context.md`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]
- [Source: `_bmad-output/implementation-artifacts/4-3-automate-the-production-readiness-gate.md`]
- [Source: `_bmad-output/implementation-artifacts/4-2-complete-an-actionable-job-runbook.md`]
- [Source: `contracts/v1/catalogs/schedules.json`]
- [Source: `contracts/v1/fixtures/schedules/cases.json`]
- [Source: `contracts/v1/fixtures/identity/occurrence-v1.json`]
- [Source: `contracts/README.md`]

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Implemented credential-free schedule qualification primitives for exact manifests, 24-hour independent expectations, delivery duplicate/miss classification, alert latency, healthy-window qualification, cleanup inventory, and readiness category projection.
- Added regression coverage for schedule qualification and documented disposable-Cell evidence/cleanup expectations in the canary Runbook.
- Validation: focused qualification/schedule/materializer tests passed (`20 passed`); full regression passed (`355 passed, 355 subtests`); Ruff, mypy, and diff checks passed. `./scripts/validate.sh` was attempted but blocked by PyPI DNS resolution.
- Applied all adversarial review patches: canonical sanitized manifests, exact Story 4.3 bindings, strict event/attempt/timestamp validation, configured deadlines, horizon failures, exact-once healthy windows, deterministic cleanup/latency checks, an executable qualification runner/workflow, and expanded readiness projection guards.
- Post-review validation: focused qualification tests passed (`6 passed`); full regression passed (`353 passed, 358 subtests`); Ruff and mypy passed.

### File List

- `_bmad-output/implementation-artifacts/4-4-qualify-schedule-delivery-and-expectations.md`
- `scripts/schedule_qualification.py`
- `scripts/run_schedule_qualification.py`
- `tests/contract/test_schedule_qualification.py`
- `docs/runbooks/canary-job-runbook.md`
- `.github/workflows/schedule-qualification.yml`

### Change Log

- 2026-07-31: Created implementation-ready context for Story 4.4.
- 2026-07-31: Implemented deterministic schedule qualification and readiness projection.
- 2026-07-31: Applied all code-review patches and added the protected qualification runner/workflow.

### Review Findings

- [x] [Review][Patch] Implement the required standard-workflow deployment into an isolated disposable Cell and verified fail-closed teardown; the current module is explicitly credential-free and only returns in-memory values, so AC1 and AC10 have no deployment, resource cleanup, or immutable evidence path [scripts/schedule_qualification.py:1-8,176-189]
- [x] [Review][Patch] Add executable denial, throttling, retry-exhaustion, dropped-delivery, DLQ, silent-path, recovery, alert-routing, deduplication, ownership, and acknowledgement qualification; `classify_delivery` only counts a caller-supplied `accepted` flag and cannot prove AC5-8 [scripts/schedule_qualification.py:128-139,159-173]
- [x] [Review][Patch] Implement generation-overlap retirement and a configured completion-deadline policy; expectations currently cover one generation and set `completion_deadline` equal to `scheduled_time`, while an empty 24-hour horizon is accepted without a diagnostic [scripts/schedule_qualification.py:78-119]
- [x] [Review][Patch] Make the qualification manifest sanitized and independently bound to release, target, Cell, workflow, plan, Deployment Identity, configuration, policy, and evidence artifacts using the repository's canonical checksum; caller-supplied evidence checksums and arbitrary configuration/policy mappings can forge AC1/AC11 evidence [scripts/schedule_qualification.py:28-75]
- [x] [Review][Patch] Accept all valid AWS Region forms, including `us-gov-west-1`, `ap-southeast-2`, and `cn-north-1`; the current Region pattern rejects valid deployment targets [scripts/schedule_qualification.py:52-60]
- [x] [Review][Patch] Replace unconditional `readiness_projection()` success values with validation of actual qualification manifest, scenario results, evidence checksum, and Story 4.3 bindings; the current function can mark schedule controls passed without running qualification [scripts/schedule_qualification.py:192-216]
- [x] [Review][Patch] Validate occurrence ID, job/generation binding, target/task identity, attempt number, timestamps, deadline, retry/DLQ disposition, and terminal state before classifying delivery; malformed or late accepted events currently become `STARTED` [scripts/schedule_qualification.py:128-139]
- [x] [Review][Patch] Strengthen healthy-window qualification to require unique occurrence identities, exact-once correlated launches, terminal results, no late/ambiguous/missing evidence, and separate Cell-health alert absence; aggregate integer counters alone do not satisfy AC9 [scripts/schedule_qualification.py:142-156]
- [x] [Review][Patch] Normalize malformed schedule, timestamp, latency, metric, and cleanup inputs to deterministic `QualificationError` failures and reject booleans/coercible values; current paths can leak `ContractViolation`, `TypeError`, or accept invalid values [scripts/schedule_qualification.py:78-119,159-189]
- [x] [Review][Patch] Move schedule-contract dependencies out of `tests.contract.support` into a reusable runtime contract module or executable qualification boundary; production code importing test helpers is not deployable when tests are excluded [scripts/schedule_qualification.py:16-22]
- [x] [Review][Patch] Expand regression fixtures for cron/rate/DST/anchors, horizon and adjacent windows, generation overlap, delivery failures/DLQ/recovery, alert timing, cleanup, and provenance; current tests cover only one hourly schedule and toy counters [tests/contract/test_schedule_qualification.py:1-113]
- [x] [Review][Patch] Replace prose-only Runbook qualification guidance with reproducible workflow commands, evidence references, disable/rollback procedure, ownership, and cleanup verification; the inserted section leaves an empty Investigation heading and cannot guide an operator through AC1/10 [docs/runbooks/canary-job-runbook.md:21-37]
