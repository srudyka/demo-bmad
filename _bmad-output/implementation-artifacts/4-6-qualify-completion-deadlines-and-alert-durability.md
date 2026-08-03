---
epic: 4
story: 4.6
title: Qualify Completion, Deadlines, and Alert Durability
status: done
baseline_commit: 6cc79dd
---

# Story 4.6: Qualify Completion, Deadlines, and Alert Durability

Status: done

## Story

As an SRE,
I want the occurrence completion and alerting paths tested under failure, delay, and replay,
so that every production occurrence reaches a trustworthy result and actionable alerts are not silently lost.

## Acceptance Criteria

1. After Story 4.5 launch/runtime qualification passes, run the same immutable release candidate through the standard trusted workflow in an isolated disposable non-production Cell. Record the Compatibility Package, account, Region, Cell identity, canary/task configuration, policy versions, Deployment Identity, test clock, and sanitized evidence checksums.
2. A completion signal is accepted only when its authenticated source context and schema match the registered job, ownership generation, CONFIG/schedule generation, task ARN, attempt zero, expected occurrence, job name, start/completion timestamps, status, exit code, and configured success marker. `SUCCEEDED` requires both an occurrence-bound success marker and verified zero essential-container exit.
3. Zero exit without a valid marker, a marker without verified zero exit, a wrong/unknown/retired/future/cross-job occurrence ID, a mismatched task/generation, malformed timestamps, or sensitive/unauthorized payload is rejected or quarantined without mutating a valid occurrence and with a stable operator-safe diagnostic.
4. Duplicate, delayed, reordered, and replayed completion evidence is reduced through the existing immutable processed-event and occurrence reducer. Exact duplicates are idempotent; late evidence cannot erase an existing deadline decision or satisfy another occurrence; conflicting status, exit code, task, generation, or completion claims produce `AMBIGUOUS` and the correct alert obligation.
5. When a started occurrence has no valid completion by its configured completion deadline, the deadline scanner emits authenticated, deduplicated `DEADLINE_REACHED` evidence and the Process Manager reduces it to `OVERDUE`. An expected occurrence with no task becomes `MISSED`. The scanner uses its durable watermark, bounded lookback, deadline buckets, pagination, base-table verification, and restart-safe overlap; it never relies on one eventually consistent index read or performs an unbounded full-table scan.
6. Deadline evidence is idempotent and safe under stale/throttled/unavailable indexes, scanner restart, duplicate scans, late task/completion evidence, and sustained scanner lag. A bad record does not acknowledge or block unrelated records.
7. Every terminal failure (`FAILED`, `MISSED`, `OVERDUE`, `AMBIGUOUS`) creates exactly one durable alert outbox obligation atomically with the occurrence state transition. Stream/dispatcher retry, notification delivery, and reconciliation preserve the obligation across crashes before/after commit and publish, use the stable alert/deduplication identity, and record attempts and final disposition in the notification ledger.
8. Repeated alert-router or notification-target failure crosses the configured age/consecutive-failure threshold and activates an independently monitored Cell alert-pipeline alarm. Recovery replays pending obligations without suppressing or duplicating the original job alert.
9. Each completion/deadline/alert failure injection produces the expected state, alert, owner, route, runbook, deduplication identity, task/occurrence metadata, Deployment Identity, and receipt evidence within five minutes of the applicable signal, deadline, or pipeline threshold. No secret, raw application payload, or unbounded occurrence ID metric dimension is emitted.
10. Twenty consecutive healthy occurrences each have one accepted task, one zero-exit ECS result, one occurrence-bound success marker, one terminal `SUCCEEDED` state, and no failure or Cell-health alert. Duplicate processing, scanner overlap, alert reconciliation, and delayed delivery produce zero false positives or ambiguous completions.
11. Completion or abort disables the qualification path first, removes injected faults, tears down disposable schedules/tasks/roles/logs/expectations/resources, verifies the cleanup inventory, and retains only explicit sanitized immutable evidence. Cleanup failure fails the qualification and cannot publish readiness evidence.
12. Story 4.3 readiness evidence marks only completion correlation, deadline processing, missed-versus-overdue classification, durable alerting, alert-pipeline health, timing, and healthy-window categories as passed. Security and recovery categories remain blocked.

## Tasks / Subtasks

- [x] Extend the Story 4.5 qualification harness and protected workflow (AC: 1, 11, 12)
  - [x] Read and reuse `scripts/ecs_qualification.py`, `scripts/run_ecs_qualification.py`, `.github/workflows/ecs-launch-runtime-qualification.yml`, and the Story 4.4 schedule qualification runner/workflow; do not create a second trusted deployment/evidence path.
  - [x] Add a completion/deadline qualification manifest bound to the same release, Compatibility Package, target, Cell, workflow, Deployment Identity, configuration, policy, and evidence provenance. Do not trust caller-supplied checksums or arbitrary readiness controls.
  - [x] Require live/attested disposable-Cell evidence or the repository’s approved protected evidence signature before projection; keep credential-free contract tests separate from live AWS qualification.
  - [x] Add disable-first, fail-closed cleanup with explicit retained/deleted inventories and no state files, plans, credentials, secrets, raw application payloads, or production identifiers.
- [x] Qualify completion correlation and reducer behavior (AC: 2-4, 10)
  - [x] Extend existing `prepare_correlation()` and the Process Manager reducer in `domain.py`/`handler.py`; do not create a second completion state machine, occurrence identity, or task identity format.
  - [x] Use the checked-in completion schemas and producer boundary: ECS task evidence is authoritative from AWS task metadata; completion evidence is authoritative from the authenticated CloudWatch Logs subscription/source context and registered job/task mapping. IDs in application text are assertions only.
  - [x] Cover valid success, zero-exit-without-marker, marker-without-zero-exit, wrong occurrence, unknown/retired/future occurrence, cross-job/generation/task, malformed timestamp, duplicate, reordered, delayed, conflicting, and replayed records.
  - [x] Preserve immutable processed-event records, conditional occurrence writes, evidence digests, monotonic terminal states, stable error codes, quarantine behavior, and alert outbox semantics.
- [x] Qualify deadline scanning and missed/overdue reduction (AC: 5, 6, 9, 10)
  - [x] Extend existing deadline contracts and `reduce_deadline_state()`; use `deadline_event_id()`, configured `completion_deadline`, scanner watermark, bounded lookback, deadline bucket pagination, and consistent base-table verification.
  - [x] Test no-start `MISSED`, started-without-completion `OVERDUE`, completion before deadline `SUCCEEDED`, completion after deadline preserving the prior decision, duplicate/late deadline evidence, stale GSI visibility, throttling, scanner restart, page boundaries, and sustained lag.
  - [x] Assert minute-cadence/under-five-minute timing evidence using a controlled test clock; do not stop tasks automatically or treat the runtime deadline as cancellation.
- [x] Qualify durable alert obligations and pipeline health (AC: 7-9)
  - [x] Reuse `Ledger.reduce_evidence()` and `occurrence_alert_outbox()`; assert state plus `ALERT_OUTBOX#<occurrence>#<policy>` are committed in one transaction with a condition preventing duplicate obligations.
  - [x] Exercise crashes before/after state commit, before/after outbox publish, duplicate stream delivery, router retry, notification target failure, notification-ledger conflict, reconciliation replay, and final disposition/attempt history.
  - [x] Verify alert fields and routing against `contracts/v1/schemas/alert.schema.json` and `contracts/v1/catalogs/metrics-alerts.json`: job, occurrence, state, failure plane, account, Region, Deployment Identity, owner, route, detection time, deduplication identity, and Runbook.
  - [x] Verify bounded metric dimensions (`job_id`, `environment`, `state` only), an independent Cell alert-pipeline alarm, delivery age/consecutive-failure threshold, and no false alerts in healthy windows.
- [x] Integrate readiness evidence, tests, and operator documentation (AC: 1-12)
  - [x] Add executable fixtures for every completion, deadline, partial-batch, replay, outbox, notification, timing, healthy-window, and cleanup case; include mixed valid/poison/unauthorized batches and assert valid records progress while failed records are retried or quarantined.
  - [x] Project only the Story 4.6 readiness control IDs and retain unrelated launch/runtime, security, and recovery controls as blocked. Seal the final controls into the manifest digest.
  - [x] Update `docs/runbooks/canary-job-runbook.md` with reproducible qualification commands, completion/deadline investigation queries, alert-pipeline checks, replay/rerun boundaries, disable/rollback steps, ownership/escalation, and cleanup verification if behavior or operations change.

### Review Findings

- [x] [Review][Patch] Workflow inputs are not materialized or provenance-checked [`.github/workflows/completion-deadline-alert-qualification.yml:48-60`] — `workflow_dispatch` receives string paths, but the job neither downloads nor materializes the evidence, configuration, or bindings artifacts; the runner then requires files already inside `$GITHUB_WORKSPACE`, so the protected qualification cannot consume its required artifacts safely.
- [x] [Review][Patch] Per-case completion expectations bypass trusted configuration [`scripts/completion_deadline_qualification.py:332-342`] — evidence can provide `case["expected"]` and redefine the job, occurrence, task, source, generation, or deployment binding; derive all expectations from authenticated configuration/bindings and reject caller overrides.
- [x] [Review][Patch] Marker-without-zero-exit is accepted by the qualification runner [`scripts/completion_deadline_qualification.py:343-346`] — `classify_completion()` returns `AMBIGUOUS` when ECS zero-exit evidence is absent, but the validator discards that result and continues; assert the classification and require rejection/quarantine for this negative case.
- [x] [Review][Patch] Completion qualification only accepts positive success-shaped cases [`scripts/completion_deadline_qualification.py:35-96,332-347`] — malformed, wrong-identity, failure-marker, marker-only, and replay/conflict cases cannot be represented as expected rejected/quarantined scenarios, so the required failure matrix is not actually exercised.
- [x] [Review][Patch] Completion fact reduction can certify success without paired authoritative facts [`scripts/completion_deadline_qualification.py:133-156`] — any `SUCCESS` fact yields `SUCCEEDED`, unknown kinds silently become `STARTED`, and SUCCESS plus FAILURE is reduced to FAILED; require validated same-occurrence/task facts and make conflicting or unknown facts ambiguous/rejected.
- [x] [Review][Patch] Terminal deadline states suppress conflicting evidence [`runtime/process_manager/src/process_manager/domain.py:247-263`] — `reduce_deadline_state()` returns the existing terminal state before evaluating conflicting task/completion/deadline facts, violating the requirement that conflicting claims become `AMBIGUOUS` while late valid evidence cannot erase the decision.
- [x] [Review][Patch] Deadline scanner behavior is not qualified [`scripts/completion_deadline_qualification.py:159-182`] — the change only classifies supplied deadline cases; it does not exercise watermark, bounded lookback, deadline-bucket pagination, base-table verification, throttling, restart overlap, page boundaries, or sustained lag required by AC 5/6/9.
- [x] [Review][Patch] Durable outbox and alert-pipeline health are asserted from caller result strings [`scripts/completion_deadline_qualification.py:296-324`] — `alert-pipeline: passed` is trusted without validating transactional outbox/notification-ledger behavior, retries, reconciliation, age/consecutive-failure thresholds, or the independent Cell alarm.
- [x] [Review][Patch] Alert evidence is optional and does not validate the normative alert contract [`scripts/completion_deadline_qualification.py:210-251,367-370`] — an empty alert list passes, and required schema fields such as account, Region, environment, notification target, operator-safe reason, and state/failure-plane enums are not checked.
- [x] [Review][Patch] Cleanup proof does not require explicit deleted inventories or forbidden-artifact checks [`scripts/completion_deadline_qualification.py:375`, `scripts/ecs_qualification.py:525-549`] — subset/count validation can pass without proving state files, plans, credentials, secrets, raw payloads, or production identifiers were absent, contrary to AC 11.
- [x] [Review][Patch] Readiness projection collapses seven Story 4.6 controls into one category [`scripts/completion_deadline_qualification.py:308-324`] — the manifest verifies seven internal result keys but returns only `completion-alerts: passed`, so the required individual completion/deadline/alert/timing/healthy control IDs are not preserved in readiness evidence.

## Dev Notes

### Existing implementation to read and extend

Read these files completely before editing:

- `scripts/ecs_qualification.py`, `scripts/run_ecs_qualification.py`, `.github/workflows/ecs-launch-runtime-qualification.yml`: Story 4.5’s protected evidence boundary, HMAC/provenance checks, manifest sealing, cleanup evidence, task evidence validation, completion-marker primitive, and readiness projection. Extend the pattern instead of duplicating it.
- `scripts/schedule_qualification.py`, `scripts/run_schedule_qualification.py`, `.github/workflows/schedule-qualification.yml`: Story 4.4’s trusted qualification structure, schedule/expectation evidence, cleanup inventory, and standard workflow conventions.
- `scripts/readiness_gate.py`, `scripts/production_bundle.py`, and `scripts/production_apply.py`: Story 4.3 exact bindings, freshness, category IDs, artifact rules, and production-fixture rejection. Preserve unrelated categories as blocked.
- `runtime/process_manager/src/process_manager/domain.py`: `prepare_correlation()`, `prepare_deadline()`, `reduce_deadline_state()`, occurrence preparation, processed-event identity, completion payload handling, and canonical state reduction.
- `runtime/process_manager/src/process_manager/handler.py`: correlation/deadline dispatch, partial-batch response, quarantine path, retry classification, and conditional reducer invocation.
- `runtime/process_manager/src/process_manager/ledger.py`: conditional evidence writes, terminal-state protection, transactional alert outbox construction, stable alert identity, and notification fields.
- `runtime/process_manager/src/process_manager/contracts.py`: canonical JSON profile, occurrence/deadline/launch event IDs, and timestamp validation.
- `runtime/process_manager/tests/test_process_manager.py`, `test_ledger.py`, `test_alert_outbox.py`: established reducer, deadline, quarantine, conditional-write, and alert-outbox fixtures.
- `contracts/v1/schemas/completion-signal.schema.json`, `contracts/v1/schemas/payloads/completion-observed.schema.json`, `contracts/v1/schemas/payloads/deadline-reached.schema.json`, `contracts/v1/schemas/alert.schema.json`, `contracts/v1/schemas/occurrence-record.schema.json`, `contracts/v1/schemas/processed-event.schema.json`: normative fields and validation boundary.
- `contracts/v1/catalogs/event-types.json`, `keys-and-correlation.json`, `metrics-alerts.json`, `queue-lambda-constraints.json`, `reducer.json`, and `contracts/v1/fixtures/reducer/cases.json`: producer identity, keys, bounded queue behavior, transition precedence, and commutative reducer vectors.
- `docs/runbooks/canary-job-runbook.md`: current operator evidence, cleanup, alerts, and qualification commands. Update only for concrete Story 4.6 behavior.

### Architecture guardrails

- Account-local Cell and separate job root remain authoritative. Do not duplicate Cell resources, bypass Cell discovery, read Terraform state from qualification code, or invent production identities.
- Only the Process Manager mutates occurrence/task/processed-event state. Materializer, ECS capture, log ingestor, deadline scanner, replay, and operator paths emit authenticated evidence through their distinct source boundaries; they do not write the ledger directly.
- `SUCCEEDED` requires one accepted occurrence-bound completion marker and zero essential-container exit for attempt zero. Launch success, `RUNNING`, `STOPPED` with code zero, a log count, or a caller-stamped marker alone is insufficient.
- Deadline evaluation is detection-only. The Cell must not call `StopTask` automatically, extend deadlines, or let late evidence erase `MISSED`/`OVERDUE`.
- The canonical states are `EXPECTED`, `STARTED`, `SUCCEEDED`, `FAILED`, `OVERDUE`, `MISSED`, and `AMBIGUOUS`. Reduction is over immutable deduplicated facts and must be arrival-order independent; conflicting terminal facts are explicit `AMBIGUOUS`.
- Terminal failure state and alert outbox obligation are one DynamoDB transaction. A stream/dispatcher and reconciliation scan must recover stranded outbox records; notification delivery is deduplicated separately through the retry horizon.
- Metrics use only bounded dimensions `job_id`, `environment`, and `state`; never use `occurrence_id` as a metric dimension. Occurrence alerts carry rich context in the alert payload, not metric dimensions.
- SQS evidence consumers use encrypted standard queues, `ReportBatchItemFailures`, bounded visibility/retry/redrive settings, and an explicit quarantine path. A malformed record must not cause valid records in the same batch to be acknowledged or indefinitely blocked.
- Production readiness requires explicit log retention, alarms, ownership, Runbook, rollback/disablement, evidence provenance, and no secrets/raw customer data in logs, manifests, alerts, artifacts, or test fixtures.

### Completion and deadline data flow

1. ECS task-state evidence and authenticated completion-log evidence enter their distinct source queues.
2. Source-specific normalization derives authority from AWS metadata (`task ARN`, `account`, `Region`, EventBridge resource, or CloudWatch subscription log-group/stream) and compares body assertions against registered CONFIG and occurrence coordinates.
3. `prepare_correlation()` or `prepare_deadline()` validates schema, producer, payload hash, occurrence identity, CONFIG generation, timestamps, and event identity before the handler touches the ledger.
4. The Process Manager conditionally records the immutable processed event and reduces the occurrence. Completion success requires both task zero-exit and marker success; deadline evidence selects `MISSED` versus `OVERDUE` without cancellation.
5. A newly accepted terminal failure writes one alert outbox item in the same transaction. Dispatcher/router delivery and notification-ledger acknowledgement are independently retryable and reconciled.

### Failure matrix that must be executable

| Plane | Injection/evidence | Expected result |
| --- | --- | --- |
| Completion success | ECS zero exit plus exact marker for same task/occurrence/generation | `SUCCEEDED`, one immutable completion fact, no failure alert |
| Completion contract | Missing marker, marker without zero exit, wrong/unknown/retired/future occurrence, cross-job/generation/task, malformed/sensitive payload | Reject/quarantine; valid occurrence unchanged; stable diagnostic |
| Completion ordering | Duplicate, replay, delayed, reordered, late-after-deadline, conflicting status/exit/task | Idempotent duplicate; late evidence cannot erase deadline; conflict becomes `AMBIGUOUS` and alerts |
| Deadline | No task at launch deadline; started task without valid completion at completion deadline | `MISSED` versus `OVERDUE`, distinct evidence and alerts |
| Scanner | Stale/throttled index, missing page, restart, duplicate scan, sustained lag | Bounded rescan/base-table verification finds due records; no permanent skip or duplicate transition |
| Batch/quarantine | Valid plus poison/unauthorized/malformed records in one SQS batch | Valid records succeed; only failed message IDs retry/quarantine; no whole-batch acknowledgement |
| Alert outbox | Crash before/after transaction, before/after publish, duplicate dispatch, notification failure, ledger conflict | One durable alert obligation, replayable delivery, bounded deduplication, pipeline alarm |
| Healthy path | Twenty consecutive exact task/zero-exit/marker/deadline/alert cases | Twenty `SUCCEEDED`, no false job/Cell alerts, no ambiguous state |
| Cleanup | Abort or completion with fault/resource cleanup failure | Disable first; cleanup verified; failed cleanup blocks evidence publication |

### AWS behavior to encode, not assume

- CloudWatch Logs subscription delivery is compressed/base64 encoded and can retry retryable destination errors for up to 24 hours; qualify subscription/ingestor failure and alert on delivery health rather than assuming a matched log line was durable. Source: [CloudWatch Logs subscriptions](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Subscriptions.html).
- Lambda SQS partial batch handling requires `FunctionResponseTypes = ReportBatchItemFailures` and a response containing valid `itemIdentifier` values. Invalid identifiers or an exception can make the whole batch fail; test mixed valid/poison batches and monitor queue age/deletion behavior. Source: [Lambda SQS error handling](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html).
- ECS task state-change events are EventBridge events with `detail-type` `ECS Task State Change`; stopped events include `stopCode`, `stoppedReason`, and ISO timestamps. AWS may add event fields, so tolerate additive fields while rejecting missing authoritative identity. Source: [ECS task state-change events](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_task_events.html).
- Do not automate on brittle free-form stopped reasons. Normalize stable stop codes, container exit facts, and source metadata to operator-safe internal codes.

### Testing and validation

- Use the repository-pinned toolchain: uv `0.11.29`, Python `3.14.6`, Terraform `1.15.8`, AWS provider `6.54.0`, Ruff, mypy, pytest, JSON Schema, and Checkov. Do not upgrade dependencies for this story without an explicit compatibility change.
- Add focused tests for completion schema/correlation, zero-exit/marker combinations, wrong and future occurrences, replay/order/conflict reduction, deadline state permutations, scanner pagination/watermark/restart/staleness, mixed SQS batches, quarantine, outbox atomicity, notification deduplication, alert-pipeline thresholds, timing, twenty healthy windows, cleanup, manifest sealing, and readiness category blocking.
- Run focused Process Manager/ledger/alert/qualification/readiness tests; `pytest tests runtime -q -p no:cacheprovider`; Ruff format/lint; mypy; `git diff --check`; and `./scripts/validate.sh`. Report PyPI/Terraform Registry DNS failures separately and never present blocked validation as passing.
- This story is expected to modify Python/runtime, contracts/fixtures, workflow/qualification, and documentation—not Terraform infrastructure unless a missing alert/queue resource is genuinely owned here. If Terraform changes, run `terraform fmt -check` and backend-free `terraform validate` for each affected root/example, preserve stable addresses/provider locks, and document plan impact plus rollback/disablement.

### Project structure and scope boundaries

- Extend existing Process Manager, contract, qualification, workflow, test, and Runbook paths. Do not add a second ledger, completion API, notification system, state machine, or readiness projector.
- Keep reusable contract logic in production/runtime modules, not under `tests/contract/support`.
- Keep protected workflow inputs under a dedicated artifact root, regular-file/symlink checks, pinned Actions, least-privilege permissions, and protected-environment secret boundaries. Never interpolate untrusted inputs directly into shell syntax.
- Preserve existing Story 4.5 HMAC/provenance evidence boundary and final manifest checksum semantics; Story 4.6 adds a distinct control projection and must not mark launch/runtime, security, or recovery as passed.
- No committed `.tfstate`, `.terraform/`, `.tfvars`, saved plans, credentials, raw logs, raw CONFIG, private keys, or generated environment artifacts.

## Previous Story Intelligence

Story 4.5 established the protected qualification foundation:

- It added `scripts/ecs_qualification.py`, `scripts/run_ecs_qualification.py`, `.github/workflows/ecs-launch-runtime-qualification.yml`, contract tests, Runbook evidence, and readiness projection. Extend those paths rather than cloning them.
- Its review required fail-closed evidence provenance, final-control checksum sealing, safe artifact roots, cleanup inventory validation, strict ECS boundary correlation, occurrence-bound completion markers, unknown stop-code handling, and twenty real task identities/timestamps. These are prerequisites, not optional patterns.
- The last implementation commit is `6cc79dd`; the story’s full file list and review findings identify the exact behavior already covered. Preserve its `ECS_QUALIFICATION_PROOF_KEY` protected-environment boundary and do not weaken it for completion evidence.
- Full validation previously passed with existing Terraform deprecation warnings for AWS provider `name`, `range_key`, and `hash_key`; do not mix unrelated deprecation cleanup into this story.

Story 4.4 established the standard qualification shape:

- Reuse the standard workflow, isolated disposable Cell, platform canary, sanitized checksum-bound manifest, controlled artifact provenance, cleanup inventory, and `epic4` versus disposable-fixture distinction.
- Qualification must fail closed on missing evidence, fabricated checksums, aggregate-only healthy counters, arbitrary configuration, missing cleanup, or unbounded readiness projection.

## Git Intelligence

- `6cc79dd Qualify ECS launch and runtime failures`: current baseline; added ECS qualification and protected workflow.
- `6f9eaf1 fix: allow schedule qualification workflow artifacts`: controlled workflow artifact allowlisting.
- `0131863 feat: qualify schedule delivery expectations`: standard schedule qualification runner, tests, Runbook, and workflow pattern.
- `ce39fad feat: harden production readiness gate`: exact readiness bindings, sealed evidence, production fixture rejection, and negative tests.
- `2ef3c7e docs: complete actionable job runbook`: current ownership, alerts, investigation, disablement, rollback, and operational documentation conventions.

## References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-4.6-Qualify-Completion-Deadlines-and-Alert-Durability`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-7` through `#AD-14`, `#AD-19`, `#AD-22`, `#AD-23`, `#AD-27`, `#AD-29`]
- [Source: `_bmad-output/implementation-artifacts/4-3-automate-the-production-readiness-gate.md`]
- [Source: `_bmad-output/implementation-artifacts/4-4-qualify-schedule-delivery-and-expectations.md`]
- [Source: `_bmad-output/implementation-artifacts/4-5-qualify-ecs-launch-and-runtime-failures.md`]
- [Source: `_bmad-output/project-context.md`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]
- [Source: `runtime/process_manager/src/process_manager/domain.py`]
- [Source: `runtime/process_manager/src/process_manager/handler.py`]
- [Source: `runtime/process_manager/src/process_manager/ledger.py`]
- [Source: `runtime/process_manager/src/process_manager/contracts.py`]
- [Source: `contracts/v1/schemas/completion-signal.schema.json`]
- [Source: `contracts/v1/schemas/payloads/completion-observed.schema.json`]
- [Source: `contracts/v1/schemas/payloads/deadline-reached.schema.json`]
- [Source: `contracts/v1/schemas/alert.schema.json`]
- [Source: `contracts/v1/catalogs/event-types.json`]
- [Source: `contracts/v1/catalogs/keys-and-correlation.json`]
- [Source: `contracts/v1/catalogs/metrics-alerts.json`]
- [Source: `contracts/v1/catalogs/queue-lambda-constraints.json`]
- [Source: `contracts/v1/catalogs/reducer.json`]
- [Source: `contracts/v1/fixtures/reducer/cases.json`]
- [AWS Lambda SQS error handling](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html)
- [CloudWatch Logs subscriptions](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Subscriptions.html)
- [Amazon ECS task state-change events](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_task_events.html)

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

- Added strict completion payload validation and terminal deadline-state preservation after red-team test failures.
- Full repository validation passed with existing Terraform deprecation/provider-override warnings.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Loaded the Epic 4 story contract, architecture spine, project context, AWS Terraform standard, Stories 4.4 and 4.5, current Process Manager/runtime contracts, ledger/outbox implementation, contract catalogs/fixtures, recent git history, and current AWS operational guidance.
- Added the Story 4.6 qualification primitives, protected workflow, completion boundary checks, deadline classifications, partial-batch behavior, alert durability/timing checks, healthy-window checks, and readiness projection.
- Preserved fail-closed cleanup and readiness blocking for launch-runtime, security, and recovery categories.
- Validation: `./scripts/validate.sh`; `380 passed, 364 subtests passed`; Ruff and mypy passed.
- Applied all 11 review patches: protected artifact downloads, trusted configuration bindings, negative completion matrix, strict fact/deadline/alert/scanner/pipeline/cleanup evidence, and per-control readiness projection.

### File List

- `_bmad-output/implementation-artifacts/4-6-qualify-completion-deadlines-and-alert-durability.md`
- `.github/workflows/completion-deadline-alert-qualification.yml`
- `scripts/completion_deadline_qualification.py`
- `scripts/run_completion_deadline_qualification.py`
- `scripts/validate.py`
- `runtime/process_manager/src/process_manager/domain.py`
- `runtime/process_manager/tests/test_process_manager.py`
- `tests/contract/test_completion_deadline_qualification.py`
- `docs/runbooks/canary-job-runbook.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-08-03: Created comprehensive implementation-ready context for Story 4.6.
- 2026-08-03: Implemented completion, deadline, alert durability, cleanup, and readiness qualification coverage; moved story to review.
- 2026-08-03: Applied adversarial code-review patches and moved the story to done.
