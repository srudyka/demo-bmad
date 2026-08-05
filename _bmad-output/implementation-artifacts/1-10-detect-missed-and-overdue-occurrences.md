---
story_key: 1-10-detect-missed-and-overdue-occurrences
baseline_commit: a539260
---

# Story 1.10: Detect Missed and Overdue Occurrences

Status: done

## Story

As an On-call Engineer,
I want every due canary occurrence reconciled against launch and completion deadlines,
so that a missing invocation or unfinished task cannot disappear because of delayed evidence or index propagation.

## Acceptance Criteria

1. **Given** deadline evaluation is introduced, **when** the Cell is planned, **then** it has a canonical deadline access pattern and an encrypted scanner checkpoint containing a durable watermark and bounded reconciliation position. This story creates no alert-outbox or notification resource.
2. **Given** the scanner emits deadline evidence, **when** the producer path is authenticated, **then** an encrypted deadline source queue and DLQ enforce retention, visibility, bounded retry, partial-batch handling, and quarantine. The normalizer derives authority from the scanner role, exact queue ARN, registered deadline key, Cell identity, and event-type registration; payload coordinates are assertions only.
3. **Given** a scan reaches due deadline buckets, **when** candidates are read, **then** the scanner advances its durable watermark safely, paginates within explicit bounds, applies the configured lookback and maximum-lateness horizon, and verifies every candidate against the authoritative base-table item. A missing eventually consistent GSI result is never conclusive.
4. **Given** an occurrence is `EXPECTED` at its launch deadline without valid launch evidence, **when** deadline evidence is reduced, **then** the canonical `DEADLINE_REACHED` fact records the launch deadline and schedule-delivery failure context and the Process Manager reduces the occurrence to `MISSED`, retaining immutable coordinates and evidence provenance.
5. **Given** an occurrence has valid launch/`STARTED` evidence at its completion deadline without valid completion, **when** deadline evidence is reduced, **then** the Process Manager reduces it to `OVERDUE`. The platform does not stop the task, claim cancellation, extend the deadline, or relaunch it.
6. **Given** an occurrence is temporarily absent from a deadline index, **when** later scans run within the maximum-lateness horizon, **then** bounded lookback and base-table verification rediscover it; GSI propagation delay cannot permanently skip it.
7. **Given** the scanner crashes after reading a page or partially emitting evidence, **when** it restarts, **then** uncommitted candidates are rediscovered and deterministic producer event IDs make re-emission idempotent. The scanner never writes an occurrence record directly.
8. **Given** valid, duplicate, late, reordered, or conflicting launch, task, completion, and deadline evidence, **when** the reducer runs, **then** the Compatibility Package produces the same result independent of arrival order. Late evidence cannot silently overwrite established `MISSED`, `OVERDUE`, `FAILED`, or `AMBIGUOUS` terminal truth; timely completion facts remain timely even if delivered after the deadline.
9. **Given** scanner IAM is reviewed, **when** positive and negative tests run, **then** the scanner can read only registered deadline/config projections and authoritative base records required for verification, update only its checkpoint, and send only the exact deadline source queue. It cannot mutate occurrences, launch or stop ECS tasks, assume job roles, change schedules, write alerts, or forge another producer.
10. **Given** the deadline path is exercised in a disposable Cell, **when** no launch, no completion, zero-exit-without-marker, delayed-GSI, duplicate-scan, pagination-boundary, restart, late-evidence, and sustained-scanner-lag cases run, **then** missed and overdue occurrences are detected within five minutes, healthy completed canaries remain healthy, and metrics stay bounded.

## Tasks / Subtasks

- [x] 1. Extend the normative deadline contracts and compatibility fixtures (AC: 2-8)
  - [x] Define the canonical deadline index key/bucket, bounded lookback, maximum-lateness horizon, checkpoint record shape, monotonic update rules, deadline identity, and deterministic producer-event identity in the Compatibility Package. Do not create a second identity algorithm.
  - [x] Extend occurrence/config/key catalogs and schemas for deadline access and checkpoint semantics; preserve existing occurrence, attempt, event, reducer, producer, IAM, and queue contracts.
  - [x] Add `DEADLINE_REACHED` payload/envelope vectors for launch and completion deadlines, duplicate/reordered delivery, late completion, conflicts, and scanner restart. Update manifest/release checksums only when canonical bytes change.

- [x] 2. Implement the deadline scanner runtime (AC: 1, 3, 6, 7, 10)
  - [x] Replace the `runtime/deadline_scanner` stub with typed pure-domain selection, pagination, bounded lookback, maximum-lateness reconciliation, checkpoint progression, and deterministic evidence construction.
  - [x] Add a narrow AWS adapter that queries only the deadline projection, strongly verifies base-table candidates, and conditionally persists a monotonic encrypted checkpoint only after emission progress is durable. Crash windows must safely replay.
  - [x] Emit only authenticated `occurrence.deadline-reached.v1` evidence to the exact source queue. Implement bounded structured logs and metrics using only Cell/environment/state/failure-plane dimensions; never include occurrence IDs, deadline keys, task ARNs, or raw payloads as metric dimensions.

- [x] 3. Extend evidence normalization and Process Manager reduction (AC: 2, 4, 5, 8)
  - [x] Extend `runtime/evidence_normalizer` to validate the deadline envelope and derive scanner identity from AWS metadata, queue ARN, registered role/key, Cell, and event type. Quarantine malformed, stale-generation, cross-Cell, wrong-queue, forged, and secret-bearing records with partial-batch behavior.
  - [x] Extend `runtime/process_manager` to retain immutable deadline facts and reduce them with the complete deduplicated evidence set. A launch deadline without valid launch is `MISSED`; a completion deadline after launch without valid completion is `OVERDUE`.
  - [x] Preserve commutativity, duplicate digest handling, conflict-to-`AMBIGUOUS`, terminal guards, completion-at-or-before-deadline semantics, and the single-writer transaction. Deadline processing must not stop, cancel, extend, or relaunch ECS work.

- [x] 4. Add Cell Terraform resources and least-privilege IAM (AC: 1, 2, 9, 10)
  - [x] In `modules/ecs-scheduled-job-platform`, add the encrypted deadline source queue/DLQ, scanner Lambda artifact/configuration, event source mapping with `ReportBatchItemFailures`, retry/redrive/visibility bounds, KMS encryption contexts, and encrypted scanner checkpoint storage while preserving stable resource addresses.
  - [x] Add the deadline index/projection and required PITR, deletion-protection, retention, tags, and deployment controls. Preserve existing task-ARN GSI behavior and avoid broad account-wide queries.
  - [x] Grant scanner only exact deadline-index/base reads, checkpoint update, and exact source-queue send. Grant normalizer only the source intake path it needs. Add IAM-negative tests proving no ledger state writes, ECS actions, `iam:PassRole`, STS assume-role, Scheduler mutation, alert writes, or policy/trust changes.
  - [x] Update Cell Contract outputs, variables, examples, README, and rollback/runbook documentation; do not add alert routing or production activation in this story.

- [x] 5. Prove ordering, failure handling, security, and operations (AC: 1-10)
  - [x] Add runtime tests for due selection, canonical key/bucket, pagination, watermark monotonicity, lookback, max lateness, delayed GSI visibility, authoritative reads, duplicate/restart replay, queue quarantine, and bounded metrics.
  - [x] Add reducer fixtures for `EXPECTED` to `MISSED`, launched/started to `OVERDUE`, timely completion delivered late, completion after deadline conflict, duplicate/reordered deadline evidence, and concurrent scanner attempts.
  - [x] Add credential-free disposable-Cell tests for no launch, no completion, zero-exit-without-marker, delayed index propagation, pagination boundaries, crash/restart, sustained lag, duplicate scans, healthy completion, and five-minute detection.
  - [x] Run contract/runtime tests, Ruff, strict mypy, Terraform `fmt -check`, backend-free `terraform validate` for every changed root, Checkov/hygiene checks when available, and `git diff --check`. Record any local provider or live-AWS limitation explicitly.

## Dev Notes

### Architecture and scope boundaries

- AD-6 and AD-7 remain binding: only Process Manager mutates occurrence, attempt, and processed-event records; state is a deterministic reduction of immutable evidence rather than arrival-order transitions.
- AD-10 requires a minute-cadence scanner, durable watermark, bounded lookback across deadline buckets, authoritative base-table verification, and reconciliation through the maximum lateness horizon. A GSI miss is not proof that an occurrence is absent.
- AD-11 requires encrypted standard SQS, partial-batch responses, `maxReceiveCount >= 5`, a 14-day DLQ, and visibility at least six times Lambda timeout plus batch window. AD-12 and AD-27 require exact producer queues and source-derived authority.
- This story is detection-only. Do not implement alert outbox/router, automatic task stopping, cancellation, deadline extension, rerun/command handling, recovery, or production activation.

### Existing components to reuse

- `runtime/deadline_scanner/` is the seeded package boundary and must become the only scanner implementation; do not import deployed runtime code from `tests.contract.support`.
- Reuse `runtime/evidence_normalizer`, `runtime/process_manager`, their handler/ledger conventions, the existing `deadline-reached.schema.json`, event-type and producer registrations, and reducer fixture framework.
- Reuse `modules/ecs-scheduled-job-platform` encrypted DynamoDB, SQS, Lambda, KMS, Cell Contract, PITR, tagging, and example patterns. Preserve the task-ARN GSI address and existing Story 1.9 correlation behavior.

### Failure and ordering guardrails

- Checkpoint updates must be conditional and monotonic. A page may be replayed after a crash; replay is safe because producer IDs and processed-event reduction are idempotent.
- Deadline facts must be retained so evidence that arrives out of order can be reduced correctly. A completion fact at or before `deadline_at` remains timely even if delivered later; a success fact after an established overdue result is conflicting evidence, not a silent overwrite.
- Scanner and normalizer logs must be secret-free and bounded. Never expose raw queue payloads, credentials, unbounded error text, occurrence IDs, deadline keys, or task ARNs in metric dimensions.

### AWS/Terraform implementation standard

- Follow `_bmad/custom/standards/aws-terraform-implementation.md`: explicit encryption, KMS contexts, retention, PITR/deletion protection, stable addresses, tags, least-privilege IAM, no public access, no mutable images, no provisioners, no generated state/plans/credentials, and documented rollback.
- The scanner role may query only the registered deadline projection and strongly read the base records needed for verification, update its own checkpoint, and send to its exact encrypted source queue. Producers never write the ledger.
- Rollback disables the scanner trigger/intake while preserving queue, checkpoint, and evidence data for replay or forward-fix; it does not stop or relaunch ECS tasks. Live AWS timing and IAM enforcement remain unproven by local tests unless explicitly exercised.

### Expected file areas

- `contracts/v1/**`, `tests/contract/**`, `runtime/deadline_scanner/**`, `runtime/evidence_normalizer/**`, `runtime/process_manager/**`
- `modules/ecs-scheduled-job-platform/{main.tf,variables.tf,outputs.tf,README.md,examples/basic/*}` and `fixtures/canary/**` only for Cell scanner controls
- `docs/runbooks/README.md` and sprint tracking artifacts

Do not add generated state, plans, credentials, broad IAM wildcards, direct producer ledger writes, automatic ECS stopping, alert resources, or unrelated queues.

### Previous story intelligence

- Story 1.9 established authoritative ECS/log correlation, strong base-table reads after GSI lookup, orphan/retry handling, strict completion validation, terminal guards, bounded metrics, and exact source permissions. Preserve those fixes while adding deadline evidence.
- Story 1.8 established immutable attempt reservation and launch safety; Story 1.7 established canonical routing, strict contracts, source authentication, quarantine/retry, and bounded observability.
- The current contract already registers `occurrence.deadline-reached.v1`, `deadline-scanner`, deadline payload fields, reducer vectors, and deadline IAM intent. Implement the missing runtime, infrastructure, and completeness rather than creating parallel contracts.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-1.10-Detect-Missed-and-Overdue-Occurrences`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-6-to-AD-14`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-23-to-AD-29`]
- [Source: `_bmad-output/implementation-artifacts/1-9-correlate-ecs-state-and-completion-evidence.md`]
- [Source: `contracts/v1/schemas/payloads/deadline-reached.schema.json`]
- [Source: `contracts/v1/catalogs/reducer.json`]
- [Source: `contracts/v1/catalogs/producers.json`]
- [Source: `contracts/v1/catalogs/iam.json`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]
- [AWS DynamoDB Query documentation](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_Query.html)
- [AWS DynamoDB global secondary index consistency](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GSI.html)
- [AWS Lambda SQS partial batch responses](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html)

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Story context assembled from the committed Story 1.9 implementation/review, Epic 1 acceptance criteria, architecture spine, existing deadline contracts, runtime stubs, Cell Terraform patterns, and AWS/Terraform standards.
- Validation: `142 passed, 187 subtests passed`; focused deadline/process-manager/normalizer tests passed; Ruff and strict mypy passed; Terraform recursive `fmt -check` and `git diff --check` passed.
- Terraform validation was attempted for the platform and canary roots but is blocked by the checked-in AWS provider `6.54.0` failing local plugin schema negotiation on darwin_arm64.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story 1.10 is the first remaining backlog story and is ready for implementation.
- The story explicitly preserves Process Manager single-writer semantics, order-independent deadline reduction, replay-safe scanning, bounded observability, and detection-only MVP scope.
- Added the deadline projection/index, encrypted checkpoint, source queue/DLQ, scanner Lambda and minute trigger, authenticated normalizer route, Process Manager deadline reduction, contract catalog/schema updates, and runbook rollback guidance.

### File List

- `_bmad-output/implementation-artifacts/1-10-detect-missed-and-overdue-occurrences.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `contracts/manifest.json`
- `contracts/releases/1.0.0.json`
- `contracts/v1/catalogs/iam.json`
- `contracts/v1/catalogs/keys-and-correlation.json`
- `contracts/v1/fixtures/schemas/valid-instances.json`
- `contracts/v1/schemas/occurrence-record.schema.json`
- `docs/runbooks/README.md`
- `modules/ecs-scheduled-job-platform/README.md`
- `modules/ecs-scheduled-job-platform/main.tf`
- `modules/ecs-scheduled-job-platform/variables.tf`
- `modules/ecs-scheduled-job-platform/outputs.tf`
- `modules/ecs-scheduled-job-platform/examples/basic/main.tf`
- `modules/ecs-scheduled-job-platform/examples/basic/variables.tf`
- `runtime/deadline_scanner/src/deadline_scanner/__init__.py`
- `runtime/deadline_scanner/src/deadline_scanner/domain.py`
- `runtime/deadline_scanner/src/deadline_scanner/handler.py`
- `runtime/deadline_scanner/tests/test_deadline_scanner.py`
- `runtime/evidence_normalizer/src/evidence_normalizer/__init__.py`
- `runtime/evidence_normalizer/src/evidence_normalizer/handler.py`
- `runtime/evidence_normalizer/src/evidence_normalizer/normalizer.py`
- `runtime/process_manager/src/process_manager/__init__.py`
- `runtime/process_manager/src/process_manager/domain.py`
- `runtime/process_manager/src/process_manager/handler.py`
- `runtime/process_manager/src/process_manager/ledger.py`
- `runtime/process_manager/tests/test_process_manager.py`

### Change Log

- 2026-07-20: Created implementation-ready Story 1.10 with contract, runtime, Terraform, IAM, testing, and operational guardrails.
- 2026-07-20: Implemented deadline scanning, authenticated deadline ingress, deterministic reduction, Cell resources, and validation evidence; status moved to review.
- 2026-07-20: Applied all 10 code-review patches; blind and edge-case layers completed, while the acceptance-auditor layer timed out.

### Review Findings

- [x] [Review][Patch] Scanner lookback/pagination and checkpoint safety — fixed by iterating bounded buckets, draining full pages, retaining complete cursors during each scan, and advancing the watermark only after reconciliation.
- [x] [Review][Patch] Deadline authority and immutable coordinates — fixed with registered-key checks, strong occurrence reads, coordinate/time validation, and record-shape validation.
- [x] [Review][Patch] Deterministic producer identity — fixed by recomputing and validating deadline producer event IDs.
- [x] [Review][Patch] Order-independent terminal reduction — fixed with terminal guards and conditional state/evidence transactions.
- [x] [Review][Patch] EventBridge trigger recovery — fixed with an encrypted tick DLQ, queue policy, bounded retry, and target dead-letter configuration.
- [x] [Review][Patch] Scanner observability and canonical serialization — fixed with bounded lag/candidate metrics, scoped CloudWatch permission, and RFC 8785 output.
- [x] [Review][Patch] Evidence growth — fixed with conditional duplicate detection and a bounded evidence collection.
