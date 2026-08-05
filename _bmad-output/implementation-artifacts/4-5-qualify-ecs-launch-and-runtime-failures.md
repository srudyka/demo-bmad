---
epic: 4
story: 4.5
title: Qualify ECS Launch and Runtime Failures
status: done
baseline_commit: 6f9eaf1
---

# Story 4.5: Qualify ECS Launch and Runtime Failures

Status: done

## Story

As a Platform Engineer,
I want the release candidate tested against ECS launch and runtime failure modes,
so that production jobs cannot be approved until task execution behavior is deterministic and observable.

## Acceptance Criteria

1. After Story 4.4 schedule qualification passes, run the same immutable release candidate through the standard trusted workflow in an isolated disposable non-production Cell using the platform-owned canary. Record the Compatibility Package, account, Region, Cell identity, task-definition ARN/revision, Deployment Identity, injected fault, expected result, and sanitized evidence checksums.
2. For `RunTask` HTTP errors, throttling, timeouts, and HTTP 200 responses with non-empty `failures[]`, record an attributable launch failure without claiming task acceptance. Retry only according to the bounded contract and never create an untracked or duplicate task.
3. If launch is accepted but the handler crashes, times out, or loses the response before persistence, reconciliation finds the accepted task using ECS-owned identity plus occurrence/Deployment Identity and converges on exactly one task; it must not blindly call `RunTask` again.
4. For image pull, secret retrieval, ENI allocation, capacity, execution-role, or task-definition start failures, retain task ARN when present, stop code, sanitized reason/error code, timestamps, and responsible boundary; route the correct job or Cell alert without secret values.
5. For unexpected exit, external stop, detection-only runtime threshold breach, or non-zero essential-container exit, reduce authoritative evidence to the canonical state machine and retain immutable runtime evidence. Never infer success from launch, start, or absence of an error event; maximum runtime remains detection-only and does not automatically stop the task.
6. A normally starting canary task with exit code zero records launch and runtime exactly once, but completion remains unresolved until the separate occurrence-bound completion contract is satisfied.
7. Duplicate, delayed, reordered, conflicting, cross-job, cross-generation, cross-account, cross-Region, or cross-Cell ECS evidence is deduplicated, rejected/quarantined, or reduced to `AMBIGUOUS` according to the Compatibility Package. It cannot satisfy or mutate the canary occurrence.
8. Every injected failure produces actionable evidence within five minutes of the ECS signal or runtime threshold, with owner, routing, failure plane, deduplication identity, occurrence/task metadata, Deployment Identity, and remediation/Runbook link matching the qualification manifest.
9. Twenty consecutive healthy launch/runtime cases each have exactly one accepted task, correct start/stop evidence, and no false launch/runtime or Cell-health alert. Missing task, extra task, unbounded retry, ambiguous state, or unattributed failure fails qualification.
10. Completion or abort safely removes injected faults and disposable resources, while retaining only required sanitized immutable evidence. Story 4.3 readiness evidence marks only ECS launch, reconciliation, runtime, timing, and healthy-run controls satisfied; completion, security, and recovery remain open.

## Tasks / Subtasks

- [x] Extend the existing qualification harness for ECS launch/runtime (AC: 1, 10)
  - [x] Reuse the Story 4.4 standard workflow, disposable Cell, platform-owned canary, release pin, sanitized manifest, checksum sealing, cleanup inventory, and evidence-retention policy.
  - [x] Add deterministic fault scenarios for API errors/throttling/timeouts, HTTP 200 `failures[]`, accepted-response loss, task-start failures, unexpected/external stops, non-zero exit, runtime threshold, duplicate/reordered/delayed/conflicting evidence, and healthy runs.
  - [x] Make cleanup fail closed; do not commit state, plans, credentials, secrets, raw application data, or production identifiers.
- [x] Verify launch idempotency and crash-window reconciliation (AC: 2, 3, 7)
  - [x] Extend `runtime/process_manager/src/process_manager/launch.py` and handler paths only through existing attempt-zero reservation, deterministic client token, exact CONFIG, task tags, cluster, and `startedBy` correlation.
  - [x] Assert `count=1`, private `awsvpc`, exact task definition, and exact platform tags on every real or simulated `RunTask` call.
  - [x] Treat HTTP 200 with non-empty `failures[]` as launch failure; if tasks and failures are mixed, preserve the task only when exact correlation proves one accepted task, otherwise fail closed as ambiguous.
  - [x] Reconcile by cluster and Cell/job/occurrence/config/attempt/Deployment Identity tags and task definition; multiple or mismatched tasks become `AMBIGUOUS`.
  - [x] Respect the safe retry deadline and ECS client-token TTL; after the deadline, do not call `RunTask` again without authoritative recovery.
- [x] Verify ECS task-state and runtime reduction (AC: 4-6)
  - [x] Reuse `prepare_correlation`, the Process Manager reducer, canonical `task.state.v1`/completion contracts, and Ledger alert-outbox transactions; do not create a second state machine or task identity format.
  - [x] Validate ECS-owned ARN/account/Region/cluster/task-definition fields and tags before trusting body assertions. Retain `task_arn`, `last_status`, `stop_code`, sanitized `stopped_reason`, container exit code/reason, and observed timestamps.
  - [x] Cover `PENDING`/`RUNNING`/`STOPPED`, `TaskFailedToStart`, `ResourceInitializationError`, image/secret/network/capacity/role/task-definition failures, external stop, non-zero exit, zero exit, missing completion, and over-runtime detection.
  - [x] Ensure zero exit only contributes runtime evidence; it cannot produce `SUCCEEDED` without the separate occurrence-bound completion marker.
- [x] Qualify alerts, healthy runs, and readiness evidence (AC: 8-10)
  - [x] Assert five-minute detection/alert latency, bounded metric dimensions (`job_id`, `environment`, `state` only), durable alert outbox, deduplication, owner/Cell routing, and operator-safe messages.
  - [x] Require twenty unique occurrence IDs with exactly one task ARN and no false launch/runtime/Cell-health alerts; reject aggregate-only counters.
  - [x] Emit sealed Story 4.3-compatible `readiness-evidence` with exact artifact/binding checksums and only the launch-runtime control IDs permitted by the acceptance criteria.
  - [x] Add executable cleanup and evidence-integrity assertions and document the disposable qualification command, disable/rollback procedure, investigation queries, ownership, and retention in the existing canary Runbook if behavior changes.

## Developer Context

### Existing implementation to read and extend

Read these files completely before editing:

- `scripts/schedule_qualification.py`, `scripts/run_schedule_qualification.py`, and `.github/workflows/schedule-qualification.yml`: Story 4.4’s reusable qualification primitives, manifest/evidence model, runner, permissions, cleanup, and trusted workflow boundary. Extend the pattern; do not create a parallel deployment path.
- `scripts/readiness_gate.py`, `scripts/production_bundle.py`, and `scripts/production_apply.py`: readiness categories, exact checksum bindings, artifact manifest rules, and production-fixture rejection. Preserve Story 4.3 semantics.
- `runtime/process_manager/src/process_manager/launch.py`: `RunTask` request construction, private networking, tags, `startedBy`, HTTP-200 failure handling, task discovery, exact-task validation, and `LaunchUncertain` behavior.
- `runtime/process_manager/src/process_manager/domain.py`, `handler.py`, and `ledger.py`: attempt reservation, correlation validation, deterministic state reduction, terminal evidence, alert outbox, and conditional ledger writes. Only the Process Manager mutates occurrence/task/event state.
- `runtime/process_manager/tests/test_launch.py`, `test_process_manager.py`, `test_ledger.py`, and `test_alert_outbox.py`: established fake-client and conditional-write patterns to preserve and expand.
- `contracts/v1/schemas/payloads/task-launch-result.schema.json`, `occurrence-launch.schema.json`, task-state/completion schemas, `contracts/v1/catalogs/keys-and-correlation.json`, `metrics-alerts.json`, `reducer.json`, `event-types.json`, and relevant fixtures: normative bytes, fields, states, correlation, metrics, alerts, and bounded transition behavior.
- `docs/runbooks/canary-job-runbook.md`: existing operator evidence and cleanup guidance; update only if the new qualification workflow adds commands or failure investigations.

### Required architecture behavior

- Account-local Cell and separate job root remain authoritative. The qualification uses an approved existing ECS cluster, private subnets, security groups, task definition, launch role, execution role, task role, and notification target; it does not duplicate shared Cell resources or read Terraform state across roots.
- The canonical states are `EXPECTED`, `STARTED`, `SUCCEEDED`, `FAILED`, `OVERDUE`, `MISSED`, and `AMBIGUOUS`. Reduction is over immutable deduplicated evidence and must commute across arrival order. Conflicting task ARNs or terminal facts become `AMBIGUOUS`; no terminal state is silently overwritten.
- MVP allows exactly one platform ECS task attempt (`attempt_no=0`) per occurrence. Reserve it transactionally before `RunTask`, persist the deterministic token/config/first-request/safe-retry data, and reuse the same reservation on retries.
- ECS identity comes from AWS EventBridge task resource/detail fields and the exact task ARN; payload IDs are assertions. Correlate by task tags, cluster, task definition, `startedBy`, reserved occurrence/attempt, CONFIG, Cell, job, generation, and Deployment Identity. Early events remain orphan evidence until launch mapping is available.
- `SUCCEEDED` requires the separate accepted completion marker and zero essential-container exit. A successful `RunTask`, `RUNNING`, `STOPPED` with code zero, or success-looking log line is insufficient.
- `RunTask` failures and task-start failures are launch/runtime failures, not completion failures. Stop codes/reasons are diagnostic evidence; do not automate on brittle free-form reason strings. Normalize to stable machine error codes and retain operator-safe details.
- Maximum runtime is detection-only. The qualification may inject/observe the threshold but must not call `StopTask` as an automatic runtime policy.
- ECS task networking remains `awsvpc` with `assignPublicIp = DISABLED`, no task-SG ingress, and only explicit egress. Roles remain separated and least-privilege; no wildcard IAM, public exposure, or secrets in events/logs/manifests.
- Metrics never use `occurrence_id` as a dimension. Occurrence alerts carry occurrence/task context, failure plane, owner, account, Region, Deployment Identity, and Runbook; Cell-wide failures route once to Platform and occurrence failures to the Job Owner.

### Failure matrix the implementation must make executable

| Plane | Injection/evidence | Expected result |
| --- | --- | --- |
| API launch | 4xx permission/validation, 5xx/throttle, timeout, HTTP 200 `failures[]` | Attributable launch failure; no accepted task claim; bounded retry only for transient errors |
| Crash window | Accepted task, handler crash/timeout/response loss | Reconcile one exact task or fail closed `AMBIGUOUS`; never blind duplicate launch |
| Start | Image pull, secret retrieval, ENI/network, capacity, execution-role, task-definition failure | `FAILED` with ARN if known, stop code/reason/error code/timestamps, correct owner/Cell alert |
| Runtime | Non-zero essential exit, external stop, over-runtime threshold | Runtime failure or `OVERDUE` per reducer; immutable evidence and alert |
| Healthy | Start, stop, zero exit, completion not yet observed | Launch/runtime recorded once; completion remains unresolved |
| Correlation | Duplicate/reordered/delayed/conflicting or foreign task evidence | Deduplicate, quarantine/reject, or `AMBIGUOUS`; never mutate canary occurrence |

### AWS behavior to encode, not assume

- `RunTask` can return HTTP 200 with both `tasks` and `failures`; only successfully placed tasks appear in `tasks`. A client token is case-sensitive, supports up to 64 printable characters, and scopes idempotency to a cluster. The token TTL is the lower of 24 hours and resource lifetime plus one hour. Use the repository’s conservative safe-retry deadline and test the configured policy.
- ECS task state-change events use `detail-type: ECS Task State Change`; stopped events provide `stopCode` and `stoppedReason`, and timestamps are ISO-formatted. Event schemas may gain fields, so tolerate unknown additive fields while rejecting missing/invalid authoritative fields.
- Do not automate on exact stopped-reason strings: AWS documents that error messages can change while `stopCode` remains stable. Map stable stop codes/container exit facts to sanitized internal error codes.

### Testing and validation

- Use the repository-pinned toolchain from Story 4.4: uv `0.11.29`, Python `3.14.6`, Terraform `1.15.8`, AWS provider `6.54.0`, Ruff, mypy, pytest, JSON Schema, and Checkov. Do not upgrade dependencies as part of this story without an explicit compatibility change.
- Add focused tests for every row of the failure matrix, including mixed `tasks`/`failures`, transient/non-transient retry classification, client-token reuse, crash reconciliation, multiple/mismatched tasks, every start failure class, stop code/exit evidence, zero-exit-without-completion, cross-boundary evidence, permutation/idempotency, alert latency/deduplication, twenty healthy windows, cleanup, and readiness projection.
- Run focused launch/process-manager/qualification/readiness tests; `pytest tests runtime -q -p no:cacheprovider`; Ruff; mypy; `git diff --check`; and `./scripts/validate.sh`. Report Terraform Registry/PyPI DNS failures separately and never represent blocked validation as passing.
- If Terraform changes, run `terraform fmt -check` and backend-free `terraform validate` for every affected module/example, preserve stable addresses and provider lock files, and include plan impact plus rollback/disablement notes.

## Previous Story Intelligence

Story 4.4 established the required foundation:

- Reuse its standard workflow, isolated disposable Cell, platform canary, sanitized checksum-bound manifest, cleanup inventory, and `epic4` versus `disposable-fixture` provenance. Its review explicitly rejected credential-free in-memory-only evidence, caller-supplied checksums, aggregate healthy counters, and prose-only Runbook guidance.
- Extend—not duplicate—schedule qualification and readiness helpers. Story 4.4’s `scripts/schedule_qualification.py` and workflow are recent code paths and must be read before introducing a shared abstraction.
- Preserve exact Story 4.3 bindings, artifact references, freshness, approvals, production-fixture rejection, and the rule that unrelated readiness categories stay blocked.
- Prior work found validation can be blocked by PyPI/Terraform Registry DNS; record this as an environment limitation rather than a passed check.

## Git Intelligence

Recent commits established the delivery pattern:

- `6f9eaf1 fix: allow schedule qualification workflow artifacts` adjusted validation allowlisting for controlled workflow artifacts.
- `0131863 feat: qualify schedule delivery expectations` added the Story 4.4 qualification module, runner, workflow, tests, Runbook evidence, and sprint status update.
- `ce39fad feat: harden production readiness gate` added sealed readiness evidence, production apply preflight, contracts, and negative tests.

Follow the same small, reviewable change pattern and keep controlled artifacts separate from generated state, credentials, saved plans, and raw data.

## References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-4.5-Qualify-ECS-Launch-and-Runtime-Failures`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-7` through `#AD-14`, `#AD-19`, `#AD-22`, `#AD-23`, `#AD-27`, `#AD-29`]
- [Source: `_bmad-output/implementation-artifacts/4-3-automate-the-production-readiness-gate.md`]
- [Source: `_bmad-output/implementation-artifacts/4-4-qualify-schedule-delivery-and-expectations.md`]
- [Source: `_bmad-output/project-context.md`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]
- [Source: `runtime/process_manager/src/process_manager/launch.py`]
- [Source: `runtime/process_manager/src/process_manager/domain.py`]
- [Source: `runtime/process_manager/src/process_manager/handler.py`]
- [Source: `runtime/process_manager/src/process_manager/ledger.py`]
- [Source: `contracts/v1/schemas/payloads/task-launch-result.schema.json`]
- [Source: `contracts/v1/catalogs/keys-and-correlation.json`]
- [AWS RunTask API reference](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_RunTask.html)
- [AWS ECS idempotency guidance](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_Idempotency.html)
- [AWS ECS task state-change events](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_task_events.html)
- [AWS stopped-task error guidance](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/stopped-tasks-error-messages-updates.html)

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Implemented credential-free ECS launch/runtime qualification primitives and protected workflow.
- Added strict `RunTask` response classification, crash-window reconciliation deadline enforcement, task-bound evidence validation, runtime reduction, healthy-window qualification, checksum-bound manifest projection, and readiness gating.
- Full validation passed: `367 passed, 361 subtests`; Ruff format/lint; mypy; Terraform format/validate; Checkov with zero failed checks; repository hygiene.
- Terraform validation emitted existing deprecation warnings for AWS provider arguments (`name`, `range_key`, `hash_key`); no Terraform files were changed by this story.

### File List

- `_bmad-output/implementation-artifacts/4-5-qualify-ecs-launch-and-runtime-failures.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `.github/workflows/ecs-launch-runtime-qualification.yml`
- `scripts/ecs_qualification.py`
- `scripts/run_ecs_qualification.py`
- `scripts/validate.py`
- `runtime/process_manager/src/process_manager/handler.py`
- `runtime/process_manager/src/process_manager/launch.py`
- `runtime/process_manager/tests/test_launch.py`
- `docs/runbooks/canary-job-runbook.md`
- `tests/contract/test_ecs_qualification.py`

### Change Log

- 2026-08-03: Created implementation-ready context for Story 4.5.
- 2026-08-03: Implemented ECS launch/runtime qualification, evidence validation, retry-deadline enforcement, workflow projection, and regression tests; marked story ready for review.
- 2026-08-03: Applied all 13 review patches and marked the story done.

### Review Findings

- [x] [Review][Patch] Make the protected workflow execute or cryptographically authenticate ECS qualification evidence — [AC 1-9; `.github/workflows/ecs-launch-runtime-qualification.yml:35-53`, `scripts/run_ecs_qualification.py:30-49`] — the workflow only runs contract tests and projects caller-selected JSON; supplied bindings are compared with themselves, so fabricated results can publish a launch/runtime-passed manifest without a disposable Cell run, fault injection, alert observation, healthy-run proof, or trusted prior schedule qualification.
- [x] [Review][Patch] Bind the published controls into the manifest integrity boundary — [AC 1/10; `scripts/ecs_qualification.py:123-132`, `scripts/run_ecs_qualification.py:48-53`] — `manifest_sha256` is computed before `controls` is added, leaving the readiness projection outside the checksum-covered body.
- [x] [Review][Patch] Implement fail-closed cleanup and abort handling — [AC 10; `.github/workflows/ecs-launch-runtime-qualification.yml:44-59`, `docs/runbooks/canary-job-runbook.md`] — no workflow `always()` cleanup, disable-first ordering, injected-fault removal, disposable-resource teardown, cleanup inventory verification, or failure-on-cleanup-error path exists; the Runbook is prose-only.
- [x] [Review][Patch] Validate accepted `RunTask` task identity before ledger mapping — [AC 2/3; `runtime/process_manager/src/process_manager/launch.py:120-125`] — a successful response accepts any non-empty `taskArn`; `_valid_task_arn()` is only used during reconciliation, so malformed or foreign identities can be persisted as accepted tasks.
- [x] [Review][Patch] Fail closed when the retry deadline is missing or invalid — [AC 3; `runtime/process_manager/src/process_manager/launch.py:25-46`, `runtime/process_manager/src/process_manager/handler.py:660-672`] — missing `safe_retry_deadline` returns `True`, preserving blind retries, while malformed deadline input raises outside the handler’s protected exception path and can escape without reconciliation or `AMBIGUOUS` evidence.
- [x] [Review][Patch] Reconcile accepted tasks while still `PENDING` — [AC 3; `runtime/process_manager/src/process_manager/launch.py:128-148`] — reconciliation searches only `RUNNING` and `STOPPED`, so an accepted task in `PENDING` can be missed and incorrectly marked ambiguous.
- [x] [Review][Patch] Enforce complete ECS boundary correlation — [AC 4/7; `scripts/ecs_qualification.py:172-247`] — task ARN shape is generic, cluster validation only checks `arn:`, and the evidence contract does not require parsed account/Region/cluster/task-definition agreement or ECS `startedBy`; matching body fields and tags can therefore admit foreign task evidence.
- [x] [Review][Patch] Route task observations through the canonical deduplicating reducer — [AC 5-7; `scripts/ecs_qualification.py:265-322`] — `classify_task_runtime()` reduces one caller-supplied observation at a time and has no event identity, duplicate/reorder/conflict handling, quarantine path, or conditional Ledger write, so exactly-once evidence and monotonic state are not qualified.
- [x] [Review][Patch] Require real task identity and evidence, not aggregate healthy counters — [AC 9; `scripts/ecs_qualification.py:325-366`, `tests/contract/test_ecs_qualification.py`] — twenty synthetic records containing only counts, occurrence labels, and booleans pass without task ARNs, correlated start/stop timestamps, or consecutive-window evidence.
- [x] [Review][Patch] Implement five-minute alert and operator-metadata qualification — [AC 4/8; `scripts/ecs_qualification.py:325-366`, `scripts/ecs_qualification.py:369-396`] — the implementation checks only zero alert counters; it does not verify signal-to-alert timestamps, durable outbox delivery, bounded metric dimensions, owner/routing, failure plane, deduplication identity, Deployment Identity, or Runbook links.
- [x] [Review][Patch] Require an occurrence-bound completion marker — [AC 5/6; `scripts/ecs_qualification.py:265-322`] — `completion_observed=True` is a caller-supplied boolean with no marker schema, task/occurrence binding, or evidence digest, allowing zero-exit task evidence to become `SUCCEEDED` without the separate completion contract.
- [x] [Review][Patch] Fail closed for unknown or newly introduced stop codes — [AC 4/5; `scripts/ecs_qualification.py:250-322`] — a stopped task with zero essential-container exit and an unrecognized stop code falls through to `STARTED`, which can hide an AWS failure mode as an active task.
- [x] [Review][Patch] Harden workflow artifact paths and task-start fault coverage — [AC 2/4; `.github/workflows/ecs-launch-runtime-qualification.yml:44-53`, `scripts/ecs_qualification.py:250-262`] — workflow-dispatch paths are interpolated into shell commands without dedicated-directory/regular-file validation, and the qualification has no distinct executable scenarios or stable evidence assertions for image pull, secret retrieval, ENI/network, capacity, execution-role, and task-definition failures.
