---
story_key: 1-8-launch-exactly-one-canary-task-per-occurrence
baseline_commit: 6dce912
---

# Story 1.8: Launch Exactly One Canary Task per Occurrence

Status: done

## Story

As a Job Owner,
I want each valid canary occurrence to launch no more than one ECS task,
so that Scheduler retries or Process Manager crashes cannot create duplicate workload effects.

## Acceptance Criteria

1. **Given** the canary generation is `MATERIALIZED` and its expected occurrences are queryable, **when** controlled non-production activation is planned, **then** preconditions require the exact acknowledged CONFIG hash, schedule ARN, Role ID, ownership generation, activation anchor, and horizon watermark; **and** changed, stale, rejected, incompatible, or insufficient-horizon acknowledgements keep the schedule disabled.

2. **Given** activation preconditions pass, **when** the canary schedule is enabled at its reviewed anchor, **then** Scheduler sends `LAUNCH` evidence through the existing authenticated source path rather than invoking ECS directly; **and** the same canonical scheduled time reduces to the same Occurrence ID already created by the materializer.

3. **Given** canonical `EXPECTED` and `LAUNCH` evidence exist for an eligible occurrence, **when** the Process Manager prepares launch, **then** it revalidates the exact immutable CONFIG and transactionally reserves task attempt zero, deterministic client token, first-request time, conservative retry deadline, and launch-pending state; **and** concurrent, duplicate, or reordered launch evidence cannot reserve another task attempt.

4. **Given** attempt zero is reserved, **when** the Process Manager invokes ECS, **then** it assumes only the canary's bound launch role and calls `RunTask` with the exact task revision, cluster, private subnets, security groups, public-IP-disabled configuration, capacity settings, and runtime deadline from verified CONFIG; **and** it supplies reserved job, occurrence, CONFIG, attempt, and Deployment Identity values through platform-owned task tags and container overrides.

5. **Given** ECS accepts the task, **when** the response is recorded, **then** the task ARN is conditionally indexed to the reserved occurrence and attempt, and the ledger retains launch timing, task revision, client token, role identity, and Deployment Identity; **and** the task-ARN access pattern is introduced with this story without accepting identity from application output.

6. **Given** ECS returns an HTTP error or HTTP 200 with a non-empty `failures[]` and no task, **when** the response is processed, **then** the occurrence reduces to `FAILED` with a stable sanitized launch-failure code and reason; **and** failure evidence is durable even though no ECS task exists to emit a lifecycle event.

7. **Given** the Process Manager crashes after ECS accepts launch but before task mapping commits, **when** canonical ingress retries the same evidence, **then** the same client token is reused and the original task is reconciled by cluster, Cell tags, and `startedBy=occurrence_id`; **and** exactly one matching task repairs the mapping without another logical launch.

8. **Given** launch outcome remains unresolved or conflicts, **when** the conservative safe-retry deadline passes, multiple task ARNs are found, parameters differ, or the token conflicts, **then** the Process Manager makes no further `RunTask` call and reduces the occurrence to `AMBIGUOUS`; **and** recovery requires a separately authorized synthetic rerun rather than an automatic attempt one.

9. **Given** Process Manager and canary launch-role permissions are analyzed, **when** positive and negative IAM tests run, **then** the Process Manager may assume only the registered canary launch role, while that role may `RunTask` only the canary task family on the exact cluster and `PassRole` only its execution and task roles; **and** direct ECS access, unrelated task families, clusters, roles, boundary removal, trust mutation, or authorization-path changes are denied.

10. **Given** launch behavior is tested in a disposable Cell, **when** duplicate delivery, concurrent delivery, `RunTask` errors, HTTP-200 failures, crash windows, delayed reconciliation, multiple-task conflict, stale CONFIG, and safe-retry expiry are exercised, **then** no scheduled occurrence creates more than one ECS task; **and** each outcome reaches the documented durable state with attributable logs and bounded metrics.

## Tasks / Subtasks

- [x] 1. Extend the normative contracts and reducer vectors (AC: 2-10)
  - [x] Preserve the existing canonical envelope, occurrence identity algorithm, `occurrence/v1` major, and Process Manager single-writer boundary. Add the launch evidence/result fields needed for this story without creating a second identity implementation.
  - [x] Complete the existing task-attempt record contract for `attempt_no=0`, including immutable occurrence/config/generation coordinates, `PENDING`/`SUCCEEDED`/`FAILED`/`AMBIGUOUS` launch state, deterministic client token, first request timestamp, safe retry deadline, task ARN, cluster, exact task definition revision, launch-role identity, Deployment Identity, and bounded failure/evidence fields.
  - [x] Define the exact keys and access pattern: `PK=JOB#<job_id>; SK=ATTEMPT#<occurrence_id>#0`, plus a narrowly scoped task-ARN lookup index that cannot replace a strongly consistent base-table read for correctness. Make task ARN mapping conditional and immutable.
  - [x] Extend reducer fixtures for launch success, launch failure, duplicate/reordered launch, task-ARN conflicts, token/parameter conflicts, and `AMBIGUOUS`; prove all permutations converge without creating attempt one.
  - [x] Update `iam.json`, `ownership.json`, `producers.json`, queue/lambda constraints, metric catalogs, schema fixtures, manifest, and checksums only when their canonical bytes change. Keep producer authority authenticated and do not grant future completion/deadline/alert authority.

- [x] 2. Implement launch validation, reservation, and deterministic reduction (AC: 2-8, 10)
  - [x] Extend `runtime/process_manager/` using the existing pure-domain-plus-narrow-AWS-adapter pattern. Validate strict canonical `LAUNCH` evidence, authenticated source metadata, supported schema major, exact job/schedule/owner generation/config hash, and recomputed Occurrence ID before writes or AWS calls.
  - [x] Require a verified immutable `MATERIALIZED` CONFIG snapshot and revalidate activation anchor, horizon, task definition revision, cluster, private network, role IDs, capacity, completion window, and Deployment Identity immediately before reservation.
  - [x] Atomically record the processed launch event and reserve attempt zero with a conditional DynamoDB transaction. Derive the client token from exact canonical launch identity bytes as a lowercase hexadecimal SHA-256 value no longer than 64 printable ASCII characters; reuse it for every retry of that occurrence.
  - [x] Use a bounded safe-retry deadline no later than the configured one-hour ECS idempotency recovery window. Record `launch_pending` before `RunTask`; never perform ECS calls inside the DynamoDB transaction and never reserve a second logical attempt.
  - [x] Add an adapter that assumes only the registered launch role and invokes `RunTask` with `count=1`, exact task definition/cluster, `awsvpc` private subnets and security groups, `assignPublicIp=DISABLED`, configured capacity, `startedBy=<occurrence_id>`, and platform-owned tags/overrides. Application-provided identity fields are assertions only.
  - [x] Treat HTTP 200 with non-empty `failures[]` or no task as a durable sanitized `FAILED` result. Treat transport/API uncertainty as reconciliation work, not proof of failure or permission to launch again.
  - [x] On crash-window retry, query the exact cluster using `startedBy` and Cell tags, verify all immutable launch parameters, and conditionally map exactly one task ARN. Zero matches may retry with the same token only before the safe deadline; multiple matches, mismatched parameters, token conflicts, or expiry produce durable `AMBIGUOUS` and stop further `RunTask` calls.
  - [x] Preserve record-local quarantine, partial-batch behavior, real UTC timestamps, secret-free bounded logs, and bounded metrics from Story 1.7. Do not use occurrence IDs, task ARNs, producer IDs, or raw exception text as metric dimensions.

- [x] 3. Add the Cell and canary Terraform wiring (AC: 1, 4, 5, 9, 10)
  - [x] Preserve existing resource addresses and extend the occurrence ledger with only the task-attempt attributes/index needed by this story. Keep encryption, PITR, deletion protection, retention, tags, and KMS context rules intact.
  - [x] Extend Process Manager artifact inputs, environment, outputs, event routing, and IAM for authenticated launch evidence, exact CONFIG reads, conditional attempt/index writes, bounded reconciliation reads, and `sts:AssumeRole` only for registered canary launch roles. Do not grant direct ECS, `iam:PassRole`, Scheduler mutation, CONFIG writes, trust/boundary mutation, or self-policy changes to the Process Manager role.
  - [x] Extend the canary launch role with `ecs:RunTask` constrained to the exact cluster and canary task definition/family, while retaining exact execution/task-role `iam:PassRole`, `iam:PassedToService=ecs-tasks.amazonaws.com`, trust to the stable Cell Process Manager role, and the configured permissions boundary.
  - [x] Make platform-owned task tags and overrides explicit for `PlatformCell`, `JobId`, `OccurrenceId`, `ConfigVersion`, `AttemptNo`, and Deployment Identity. Keep task networking private and public IP disabled.
  - [x] Add an explicit activation acknowledgement contract to the canary fixture. Keep the schedule disabled by default and require exact hash, schedule ARN, scheduler Role ID, owner generation, activation anchor, materialization state, and horizon watermark before any enabled plan is valid.
  - [x] Keep the `modules/ecs-scheduled-job` ownership boundary explicit: use the existing canary fixture exception unless a reviewed interface moves concrete launch resources into the module. Do not silently duplicate task definitions or roles.

- [x] 4. Prove correctness, security, and operations (AC: 1-10)
  - [x] Add runtime tests for reservation races, duplicate/reordered evidence, stale CONFIG, activation mismatch, deterministic tokens, successful launch, HTTP errors, HTTP-200 failures, no-task responses, crash-window reconciliation, delayed visibility, multiple-task conflict, parameter/token conflict, safe-retry expiry, and durable failure/ambiguity.
  - [x] Add contract, Terraform static, and IAM-negative tests proving one task maximum per occurrence, exact cluster/task-family/role scope, private networking, tag/override provenance, task-ARN lookup, no direct Process Manager ECS authority, and no future-story authority.
  - [x] Add disposable-Cell tests with fake STS/ECS/DynamoDB adapters and clearly mark credential-free tests as unable to prove live AWS delivery, ECS idempotency, or IAM enforcement. Run focused and full validation, including Terraform format/validate, Ruff, mypy, contract/runtime tests, Checkov, hygiene, and `git diff --check`.
  - [x] Update Process Manager, Cell, canary, and runbook documentation with launch states, retry/reconciliation behavior, activation checklist, bounded observability, safe rollback, and the rule that rollback disables schedule/launch intake while preserving ledger evidence and does not automatically stop or relaunch an already accepted ECS task.

## Dev Notes

### Architecture and Scope Boundaries

- The Process Manager remains the only runtime-ledger writer. Materializer, normalizer, and Scheduler emit authenticated evidence; Scheduler never invokes ECS directly.
- The ledger is a deterministic reduction of immutable, deduplicated facts. Launch processing adds attempt-zero reservation and task mapping; completion correlation, deadline scanning, alerts, operator commands, and recovery remain later stories.
- A `RunTask` uncertainty is not evidence that no task exists. Reconcile before retrying, reuse the same token, and fail closed to `AMBIGUOUS` when the evidence cannot prove a single task.
- Do not use task application output as identity authority. ECS task ARN, cluster, tags, `startedBy`, registered log identity, and the ledger task-ARN index are authoritative; container fields are assertions.

### Previous Story Intelligence

- Story 1.7's review required dedicated Process Manager routing, runtime-owned contract primitives, authenticated provenance, complete schema validation, exact CONFIG hash/owner checks, schema-conformant records, idempotent existing-record reduction, retained quarantine/conflicts, real runtime timestamps, no silent discard, broader tests, and bounded queue visibility. Preserve all of these constraints while extending the handler.
- The current Process Manager role intentionally has no ECS or role-assumption authority. Add only the reviewed launch-role assumption edge and keep the job launch role as the sole holder of `RunTask` and `PassRole`.
- The canary already has separate launch, execution, and task roles, immutable task image/config fields, private-network inputs, and a disabled schedule. Extend those resources without changing their ownership or enabling the schedule by default.

### Web-verified AWS Notes

- ECS `RunTask` client tokens are printable ASCII, limited to 64 characters, and idempotent for identical parameters within the documented token lifetime; conflicting parameters for the same token are rejected. See [Amazon ECS idempotency](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_Idempotency.html).
- ECS `RunTask` can return HTTP 200 with a non-empty `failures[]`; `startedBy` and task tags provide supported correlation inputs for reconciliation. See [ECS RunTask API](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_RunTask.html).
- SQS-triggered Lambda processing must retain `ReportBatchItemFailures` and record-local retry behavior from Story 1.7. See [Handling errors for an SQS event source in Lambda](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html).

### Expected File Areas

- `runtime/process_manager/**`
- `modules/ecs-scheduled-job-platform/{main.tf,variables.tf,outputs.tf,README.md,examples/basic/*}`
- `modules/ecs-scheduled-job/{main.tf,variables.tf,README.md}` only if the ownership interface is deliberately activated
- `fixtures/canary/{main.tf,variables.tf,README.md}`
- `contracts/**`, `tests/contract/**`, `docs/runbooks/README.md`

Do not add generated state, plans, credentials, secrets, a broad IAM wildcard, an unreviewed remote-state link, or a new queue family unless the contract and acceptance criteria require it.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-1.8-Launch-Exactly-One-Canary-Task-per-Occurrence`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-4-to-AD-9`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-11-to-AD-14`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-25-and-AD-29`]
- [Source: `_bmad-output/implementation-artifacts/1-7-record-deterministic-occurrence-state.md`]
- [Source: `contracts/v1/schemas/task-attempt-record.schema.json`]
- [Source: `contracts/v1/schemas/payloads/occurrence-launch.schema.json`]
- [Source: `contracts/v1/catalogs/keys-and-correlation.json`]
- [Source: `contracts/v1/catalogs/iam.json`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Terraform canary validation passed with the locked AWS provider. The isolated platform-root validation reached provider initialization but failed during the local AWS provider plugin handshake (`Failed to read any lines from plugin's stdout`); no AWS plan, state, or credentials were created.
- Checkov passed with the repository's documented platform-only skips: 254 platform checks and 98 canary checks. The Checkov service-guideline lookup was unavailable because network DNS is restricted, but local checks completed.

### Completion Notes List

- Story context created from the first backlog story after committed Story 1.7.
- The story preserves Story 1.7's review fixes and incorporates the existing launch contract vocabulary, ownership model, and canary IAM/resource boundaries.
- This artifact contains no generated state, plan, credentials, or live-AWS claim; implementation validation is recorded below.
- Implemented deterministic Scheduler launch validation, attempt-zero reservation, same-token ECS launch/reconciliation, durable failure/ambiguity handling, exact launch-role IAM, task-ARN indexing, activation acknowledgement gating, tests, and rollback documentation.
- Validation passed: 137 tests plus 182 subtests, strict mypy, Ruff, repository hygiene, Terraform format, and Checkov. Live AWS delivery, ECS idempotency, and IAM enforcement remain unproven by credential-free tests.

### File List

- `contracts/manifest.json`
- `contracts/releases/1.0.0.json`
- `contracts/v1/catalogs/iam.json`
- `contracts/v1/catalogs/keys-and-correlation.json`
- `contracts/v1/schemas/task-attempt-record.schema.json`
- `docs/runbooks/README.md`
- `fixtures/canary/{README.md,main.tf,variables.tf}`
- `modules/ecs-scheduled-job-platform/{README.md,main.tf,outputs.tf,variables.tf}`
- `modules/ecs-scheduled-job-platform/examples/basic/variables.tf`
- `runtime/process_manager/README.md`
- `runtime/process_manager/src/process_manager/{__init__.py,contracts.py,domain.py,handler.py,launch.py,ledger.py}`
- `runtime/process_manager/tests/{test_ledger.py,test_launch.py,test_process_manager.py}`
- `tests/contract/test_canary_fixture.py`

### Change Log

- 2026-07-20: Created implementation-ready Story 1.8 from the Epic 1 acceptance criteria and committed Story 1.7 baseline.
- 2026-07-20: Implemented Story 1.8 launch authority, idempotency, reconciliation, Terraform guardrails, tests, and operational documentation; moved story to review.

### Review Findings

- [x] [Review][Patch] Terminal attempt states are not terminal in the launch handler — when duplicate launch evidence finds an existing `FAILED` or `AMBIGUOUS` attempt without a task ARN, `_process_launch` proceeds to assume the role and call `RunTask` again, violating AC 8 and allowing a second logical launch. [runtime/process_manager/src/process_manager/handler.py:259-268]
- [x] [Review][Patch] Failure and ambiguity do not reduce the occurrence record — `finish_failed` and `mark_ambiguous` update only the task-attempt item, leaving the occurrence in `EXPECTED` instead of the durable `FAILED`/`AMBIGUOUS` state required by AC 6 and AC 8. [runtime/process_manager/src/process_manager/ledger.py:211-253]
- [x] [Review][Patch] Launch validation does not require `config_version` to equal the verified CONFIG hash — `ConfigSnapshot.config()` validates `config_hash` against the JSON bytes, but `prepare_launch` omitted the explicit `config_hash == config_version` invariant enforced by the expected-occurrence path, so a malformed snapshot could launch under an untrue CONFIG identity. [runtime/process_manager/src/process_manager/domain.py:409-425]
- [x] [Review][Patch] Reservation is not conditional on the eligible occurrence — `reserve_attempt` transactionally created the processed event and attempt but never condition-checked the occurrence’s `EXPECTED` state or immutable coordinates, leaving a read-then-write race where stale launch processing could reserve after the occurrence changed. [runtime/process_manager/src/process_manager/ledger.py:139-169]
- [x] [Review][Patch] Reconciliation only searched `RUNNING` tasks and did not verify the required Cell/identity tags — an accepted task still in `PENDING` or already `STOPPED` could be treated as absent, and any task sharing the cluster and `startedBy` value could be mapped without checking platform tags. [runtime/process_manager/src/process_manager/launch.py:86-111]
- [x] [Review][Patch] The task-attempt schema did not require the launch identity fields added by this story — launch records could be schema-valid without the immutable task, role, deployment, cell, or network fields required by AC 4 and AC 5. [contracts/v1/schemas/task-attempt-record.schema.json:146-160]
- [x] [Review][Patch] Reconciliation uncertainty was allowed to escape without a durable terminal state — multiple-task and parameter-mismatch results could leave the attempt `PENDING` and cause repeated launch retries. [runtime/process_manager/src/process_manager/handler.py:275-286]
- [x] [Review][Patch] Deployment Identity was not represented as a reconciliable ECS tag — it was supplied only as a container override, so ECS evidence could not prove the exact platform deployment identity. [runtime/process_manager/src/process_manager/launch.py:43-72]
- [x] [Review][Patch] Failure code was written to the ledger but undeclared by the task-attempt schema — terminal failure records could violate `additionalProperties: false` and lacked a contract field for the sanitized code. [runtime/process_manager/src/process_manager/ledger.py:221-247; contracts/v1/schemas/task-attempt-record.schema.json:5-160]
- [x] [Review][Patch] Launch evidence arriving before the expected occurrence was quarantined instead of retried — queue reordering could permanently lose a valid launch event. [runtime/process_manager/src/process_manager/handler.py:244-249]
- [x] [Review][Patch] A contradictory ECS response containing both `failures[]` and a task was treated as ordinary failure — the accepted task could be orphaned while the ledger recorded `FAILED`. [runtime/process_manager/src/process_manager/launch.py:74-83]
- [x] [Review][Patch] Reconciliation accepted malformed task ARN values from `ListTasks` — arbitrary strings could reach the authoritative task mapping path. [runtime/process_manager/src/process_manager/launch.py:95-110]
