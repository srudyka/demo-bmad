---
story_key: 1-9-correlate-ecs-state-and-completion-evidence
baseline_commit: 79a54c5
---

# Story 1.9: Correlate ECS State and Completion Evidence

Status: ready-for-dev

## Story

As an On-call Engineer,
I want ECS lifecycle events and structured completion records correlated to the authoritative canary occurrence,
so that successful, failed, delayed, duplicate, and conflicting outcomes are distinguished correctly.

## Acceptance Criteria

1. **Given** ECS task-state evidence is consumed for the first time, **when** Cell integrations are planned, **then** create encrypted ECS-event source queues/DLQs and an account-local EventBridge rule capturing only relevant task-state events for the registered Cell cluster; authority derives from AWS event metadata, source account, Region, cluster, and task ARN, never body-supplied job identity.
2. **Given** completion-log evidence is consumed for the first time, **when** the canary completion path is deployed, **then** create an encrypted completion source queue/DLQ, log ingestor, and exact canary log-subscription permission; identity derives from AWS-generated log-group and log-stream metadata mapped to the registered task/job.
3. **Given** an ECS event arrives after task mapping exists, **when** normalized, **then** resolve its task ARN through the Story 1.8 ledger index to one occurrence/attempt and compare, but never trust, asserted job, occurrence, CONFIG, attempt, or task values.
4. **Given** an ECS or completion event arrives before task mapping, **when** correlation cannot resolve the task ARN, **then** retain orphan evidence and retry/reconcile within a bounded window; do not discard, redirect, or declare success.
5. **Given** the mapped task reaches `RUNNING`, **when** task-state evidence is reduced, **then** record authoritative `started_at` and idempotently transition to `STARTED`; duplicates and reordering cannot change immutable coordinates.
6. **Given** the canary emits structured completion, **when** parsed, **then** validate job, occurrence, CONFIG, attempt, timestamp, status, exit code when available, and sanitized error reason against the completion schema; malformed, secret-bearing, wrong-job/task, and unsupported-version records cannot declare success.
7. **Given** attempt zero has exactly one accepted success record and essential-container exit code zero, **when** both evidence records reduce, **then** transition exactly once to `SUCCEEDED` with authoritative task/completion timing; a Scheduler delivery, marker, log count, or zero exit alone is insufficient.
8. **Given** the task fails to start, stops unexpectedly, or an essential container exits non-zero, **when** task-state evidence reduces, **then** transition to `FAILED` with stable sanitized stop/exit details; later success markers cannot overwrite it.
9. **Given** completion evidence is duplicated, delayed, conflicting, tied to another occurrence, or tied to multiple task ARNs, **when** reduced, **then** commutative fixtures determine the same result independent of arrival order; wrong-window evidence cannot satisfy the occurrence and conflicts become `AMBIGUOUS`.
10. **Given** ECS capture, log ingestion, and normalization IAM are analyzed, **when** positive/negative tests run, **then** each producer can publish only permitted event types to its exact source queue and read only required AWS metadata; forgery, cross-job delivery, direct ledger writes, ECS launch, role passing, and queue-policy mutation are denied.
11. **Given** correlation is tested in a disposable Cell, **when** success, start failure, non-zero exit, missing marker, marker without zero exit, wrong occurrence, delayed prior completion, duplicates, conflicts, early events, log failure, and consecutive windows are exercised, **then** every occurrence reaches the Compatibility Package state and successful runs produce no failure state or unbounded metric dimensions.

## Tasks / Subtasks

- [ ] 1. Extend normative correlation contracts and fixtures (AC: 3-9, 11)
  - [ ] Reuse the existing task-state, completion-observed, completion-signal, evidence-envelope, occurrence, and task-attempt schemas; add only required correlation fields/catalog entries.
  - [ ] Define bounded orphan-evidence storage, deduplication, retry coordinates, and expiry without a second identity algorithm or ledger writer.
  - [ ] Publish reducer vectors for RUNNING, start failure, STOPPED, zero/non-zero exits, marker/exit combinations, duplicates, delays, wrong windows, multiple task ARNs, and AMBIGUOUS.
  - [ ] Update producer/event/key/IAM/queue/metric/schema/manifest/release artifacts only when canonical bytes change.

- [ ] 2. Implement authoritative ECS-event normalization (AC: 1, 3-5, 9-10)
  - [ ] Extend `runtime/evidence_normalizer/` with typed pure-domain logic plus a narrow AWS adapter. Derive account, Region, cluster, task ARN, task definition, status, stop code/reason, containers, and event version from AWS-owned fields.
  - [ ] Resolve task ARN through the Story 1.8 GSI, then strongly read the base attempt/occurrence records. GSI absence is bounded orphan/retry work, never proof of absence or permission to redirect.
  - [ ] Compare body assertions with ledger/config authority, retain bounded conflicts, preserve source authentication, strict schema-major checks, quarantine, partial-batch behavior, and secret-free logs.

- [ ] 3. Implement structured completion log ingestion (AC: 2, 4, 6, 9-10)
  - [ ] Extend `runtime/log_ingestor/` to decode the AWS CloudWatch Logs subscription envelope and retain authoritative `logGroup`/`logStream` metadata.
  - [ ] Map registered canary log group/stream and task ARN to the ledger before accepting completion evidence; application identity is assertion-only.
  - [ ] Reject unsupported versions, malformed JSON, secrets/credentials, wrong job/task/config/attempt, out-of-window timestamps, duplicate/conflicting records, and unbounded error text using stable sanitized codes.
  - [ ] Emit canonical completion evidence through the authenticated normalizer path; never write the ledger directly.

- [ ] 4. Reduce task and completion evidence in Process Manager (AC: 5-9, 11)
  - [ ] Extend `runtime/process_manager/` without weakening Story 1.8 task-ARN authority, attempt-zero immutability, terminal guards, and transactional single-writer behavior.
  - [ ] Require authoritative RUNNING plus one accepted completion and essential-container exit zero for SUCCEEDED; never accept a marker, zero exit, Scheduler delivery, or log count alone.
  - [ ] Reduce start failure, stopped/non-zero exit, missing marker, late, duplicate, reordered, and conflicting evidence to durable documented states without terminal overwrite.
  - [ ] Store only bounded timestamps, stop/exit codes, sanitized reasons, evidence IDs, and Deployment Identity; keep immutable coordinates and bounded metrics.

- [ ] 5. Add Cell and canary infrastructure (AC: 1, 2, 10, 11)
  - [ ] In `modules/ecs-scheduled-job-platform/`, add encrypted ECS-event/completion source queues and DLQs, redrive/visibility bounds, policies, EventBridge rule/target, log-ingestor Lambda artifact/configuration, and KMS contexts while preserving stable addresses.
  - [ ] Match only `aws.ecs` task-state events for the exact Cell cluster; do not capture broad account events or grant producer ledger writes.
  - [ ] In the job/canary owner boundary, add the exact CloudWatch Logs subscription filter and Lambda permission for the canary log group; do not move job-owned log resources into the Cell module.
  - [ ] Grant only required queue publish, log invocation, task-ARN lookup/base reads, and metadata reads. No direct ledger writes, ECS launch, `iam:PassRole`, Scheduler mutation, trust/boundary mutation, or queue-policy mutation.
  - [ ] Update Cell Contract, README, and rollback/runbook guidance. Rollback disables capture/intake and preserves evidence; it does not stop or relaunch tasks automatically.

- [ ] 6. Prove correctness, security, and operations (AC: 1-11)
  - [ ] Add runtime tests for AWS event authority, index/base lookup, delayed mapping, orphan retry/expiry, log decoding, strict completion validation, state reduction, duplicate/reorder/conflict convergence, and bounded observability.
  - [ ] Add contract/IAM-negative tests for exact EventBridge cluster patterns, source principals, log permission, no direct ledger writes, no ECS/PassRole, secret rejection, wrong-task isolation, and task-ARN authority.
  - [ ] Add credential-free disposable-Cell tests for EventBridge-to-SQS, CloudWatch Logs-to-Lambda, ECS payloads, delivery failures, and consecutive windows; state that live AWS timing/IAM is unproven.
  - [ ] Run Terraform format/backend-free validation for every discovered root, Ruff, strict mypy, contract/runtime tests, Checkov, hygiene, and `git diff --check`.

## Dev Notes

### Architecture and Scope Boundaries

- Process Manager remains the only writer of `OCCURRENCE`, `TASK_ATTEMPT`, and processed `EVENT` records. ECS capture, log ingestor, and normalizer emit authenticated evidence only.
- Reuse the Story 1.8 task-ARN GSI as an accelerator, then strongly read the base table for correctness. EventBridge resource/detail and CloudWatch subscription metadata are authoritative; application text is assertion-only.
- Do not implement deadline scanning, alert outbox/router, commands, recovery, automatic task stopping, synthetic reruns, or production activation.
- ECS/log delivery is at-least-once and may precede task mapping. Orphan evidence must be retained/retried within a bounded horizon and never acknowledged as processed when unresolved.

### Existing Components to Reuse

- `runtime/evidence_normalizer/`, `runtime/log_ingestor/`, and `runtime/process_manager/` package boundaries, handler conventions, strict contract utilities, and focused tests.
- `contracts/v1/schemas/payloads/task-state.schema.json`, `completion-observed.schema.json`, `completion-signal.schema.json`, occurrence/task-attempt schemas, reducer fixtures, producer catalog, and keys/correlation catalog.
- `modules/ecs-scheduled-job-platform/main.tf` encrypted queue/Lambda/KMS/IAM/Cell Contract patterns and `fixtures/canary/main.tf` existing task definition, log group, roles, private network, and disabled schedule.

### Failure and Ordering Guardrails

- A stopped task without valid completion is failed only from authoritative stop/essential-container evidence. A marker without essential exit zero is not success.
- Later success cannot overwrite terminal failure. Conflicting terminal facts, duplicate task ARNs, wrong windows, and mismatched coordinates become `AMBIGUOUS` per commutative fixtures.
- Never log raw CloudWatch payloads, credentials, raw exception text, or unbounded application errors; use stable codes and bounded operator-safe reasons.

### AWS/Terraform Standard

- Use encrypted standard SQS queues with DLQs, `ReportBatchItemFailures`, `maxReceiveCount >= 5`, 14-day redrive retention, and visibility at least six times Lambda timeout plus batch window.
- Scope the EventBridge pattern to `source = aws.ecs`, `detail-type = ECS Task State Change`, and the exact cluster ARN. Scope CloudWatch Logs invoke permission to the exact canary log group/function.
- Preserve tags, KMS contexts, PITR/deletion protection, stable addresses, explicit retention, least privilege, runbook notes, alarms/metrics, and rollback. No public access, mutable images, provisioners, state, plans, credentials, or remote-state links.

### Previous Story Intelligence

- Story 1.8 review established terminal launch guards, conditional immutable reservation, full platform-tag reconciliation, schema-conformant failure records, and live/stopped visibility. Preserve all of them.
- Story 1.7 established dedicated routing, strict canonical contracts, source authentication, record-local quarantine/retry, bounded metrics, UTC timestamps, and no silent discard.
- Existing schemas and runtime stubs are intentional extension points; do not create parallel identity or normalization implementations.

### Current AWS Notes

- ECS task-state events are delivered to EventBridge for lifecycle changes such as PENDING→RUNNING and RUNNING→STOPPED; parsers must tolerate unknown additive properties. See [ECS task state change events](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_task_events.html) and [ECS events](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_cwe_events.html).
- EventBridge patterns should constrain both source and detail type, then the exact cluster. See [EventBridge ECS events](https://docs.aws.amazon.com/eventbridge/latest/ref/events-ref-ecs.html).
- CloudWatch Logs subscription delivery uses an AWS-owned encoded envelope and requires an exact Lambda permission/filter. See [CloudWatch Logs subscription filters](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/SubscriptionFilters.html).

### Expected File Areas

- `contracts/**`, `tests/contract/**`, `runtime/evidence_normalizer/**`, `runtime/log_ingestor/**`, `runtime/process_manager/**`
- `modules/ecs-scheduled-job-platform/{main.tf,variables.tf,outputs.tf,README.md,examples/basic/*}`
- `fixtures/canary/{main.tf,variables.tf,README.md}`, and `modules/ecs-scheduled-job/**` only for the reviewed job-owned log subscription interface
- `docs/runbooks/README.md`

Do not add generated state, plans, credentials, secrets, broad IAM wildcards, a new identity algorithm, direct producer ledger writes, automatic task stopping, alert/deadline resources, or unrelated queues.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-1.9-Correlate-ECS-State-and-Completion-Evidence`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-5-to-AD-14`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-23-to-AD-29`]
- [Source: `_bmad-output/implementation-artifacts/1-8-launch-exactly-one-canary-task-per-occurrence.md`]
- [Source: `_bmad-output/implementation-artifacts/1-7-record-deterministic-occurrence-state.md`]
- [Source: `contracts/v1/schemas/payloads/task-state.schema.json`]
- [Source: `contracts/v1/schemas/payloads/completion-observed.schema.json`]
- [Source: `contracts/v1/catalogs/producers.json`]
- [Source: `contracts/v1/catalogs/keys-and-correlation.json`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Ultimate context analysis completed from Story 1.9 criteria, Epic 1 architecture, AWS/Terraform standards, Story 1.8 review fixes, Story 1.7 patterns, existing schemas/stubs, Cell Terraform interfaces, and recent commits.

### Completion Notes List

- Created from the first backlog story after committed Story 1.8.
- Preserves task-ARN authority, orphan-evidence safety, bounded observability, the single-writer boundary, and no automatic rerun/stop behavior.
- Includes current AWS EventBridge ECS task-state and CloudWatch Logs subscription constraints; local tests must not claim live AWS or IAM proof.

### File List

- `_bmad-output/implementation-artifacts/1-9-correlate-ecs-state-and-completion-evidence.md`

### Change Log

- 2026-07-20: Created implementation-ready Story 1.9 with contract, runtime, Terraform, IAM, testing, and operational guardrails.
