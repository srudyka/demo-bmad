---
story_key: 1-5-authenticate-and-normalize-platform-evidence
baseline_commit: c564247c8e3dc1c92ab78a923ad905da9c1f0263
---

# Story 1.5: Authenticate and Normalize Platform Evidence

Status: ready-for-dev

## Story

As a Platform Security Engineer,
I want Scheduler evidence authenticated and normalized before it reaches occurrence processing,
so that an event body cannot forge producer, job, generation, or authorization identity.

## Acceptance Criteria

1. **Given** the canary Scheduler source queue from Story 1.4
   **When** the normalizer integration is deployed
   **Then** it creates an encrypted canonical ingress queue, ingress DLQ, and bounded quarantine path that satisfy the Compatibility Package retention, visibility, batch, retry, and payload constraints
   **And** materializer, ECS, completion-log, and command source queues are not created until their producer stories use them.

2. **Given** Scheduler sends launch evidence through its dedicated delivery role
   **When** the normalizer receives the SQS record
   **Then** producer authority is derived from queue ARN, SQS sender identity or IAM Role ID, registered schedule ARN, account, Region, job ownership generation, and permitted evidence type
   **And** job ID, producer ID, source ARN, generation, and authorization fields in the message body are treated only as assertions to compare.

3. **Given** source identity and payload assertions agree with the Cell-owned registration and schema
   **When** normalization succeeds
   **Then** the normalizer emits one versioned canonical envelope containing Cell-stamped producer identity, deterministic producer event ID, event type, job, CONFIG version, generation, scheduled time, recomputed occurrence ID, emitted time, payload hash, and trace context
   **And** the envelope is secret-free and conforms to the Compatibility Package schema before entering canonical ingress.

4. **Given** a message contains a forged job, producer, evidence type, schedule ARN, scheduled time, generation, occurrence ID, stale Role ID, or cross-account sender
   **When** the normalizer evaluates it
   **Then** it is rejected without writing platform state, invoking ECS, or forwarding canonical evidence
   **And** a sanitized rejection record and bounded security metric are retained without secret values or unbounded metric dimensions.

5. **Given** a batch contains valid, transiently failing, and invalid messages
   **When** processing completes
   **Then** Lambda partial-batch responses acknowledge successful and quarantined records, retry only transient failures, and route poison records through the configured redrive or quarantine path
   **And** one malformed record cannot block unrelated Scheduler evidence.

6. **Given** the normalizer role is analyzed
   **When** IAM-positive and IAM-negative tests run
   **Then** it can read only the registered Scheduler source queue and write only canonical ingress, its own logs, approved bounded metrics, and the exact quarantine path
   **And** it cannot write namespace, CONFIG, occurrence, or alert data; assume job launch roles; call ECS; pass roles; change queue policies; or read another source queue.

7. **Given** the shared normalizer runtime is deployed
   **When** networking and logging controls are inspected
   **Then** it remains outside consumer VPCs, has no inbound public interface, and writes structured secret-free logs with explicit retention
   **And** timeout, reserved concurrency, event-source batch settings, and queue visibility satisfy published constraints.

8. **Given** the normalizer code, schema, or integration changes
   **When** repository and disposable-Cell tests run
   **Then** they cover valid launch evidence, duplicate delivery, malformed schema, forged fields, stale registration, source-account/source-ARN mismatch, partial batches, poison records, and replay
   **And** identical valid source events normalize deterministically while unsupported schema majors fail before side effects.

## Tasks / Subtasks

- [ ] 1. Define the canary-only trusted Scheduler registration and contract additions (AC: 2, 3, 4, 6, 8)
  - [ ] Add an explicit `canary_normalizer_registration` Cell input. It is platform-controlled and contains the canary job ID, account, Region, owner generation, CONFIG version, schedule generation, source queue ARN, schedule group ARN, exact schedule ARN, and immutable scheduler delivery Role ID. Validate every field against the existing Cell, `canary_reservation`, canonical ARN/identifier grammar, and the exact `fixtures/canary` root.
  - [ ] The registration is the normalizer's read-only deployment configuration; do not introduce a general Registrar, a runtime ledger, or a normalizer DynamoDB permission. The fixture must expose `aws_iam_role.scheduler_delivery.unique_id` as evidence for this explicit Cell input, without `terraform_remote_state` or root-to-root mutation.
  - [ ] Extend the Compatibility Package for the normalized Scheduler launch envelope: define the deterministic Scheduler producer-event-ID byte serialization and vectors, a SHA-256 payload hash, and an optional secret-safe trace-context representation. Preserve schema compatibility by using an additive compatible schema/catalog change and update `contracts/manifest.json`, `contracts/releases/1.0.0.json`, and `contracts/migrations/v1.0.0.md` according to the existing manifest/release tests.
  - [ ] Use the existing RFC 8785 helpers, schema registry, secret-safety policy, `occurrence_id`, producer catalog, and raw AWS producer fixtures. Do not duplicate JSON canonicalization, schema validation, schedule evaluation, or occurrence hashing in the runtime package.
  - [ ] Correct `contracts/v1/catalogs/iam.json` so the normalizer catalog does not grant DynamoDB `PutItem` or any ledger write. Its required authority is only exact source-queue receive/delete/attribute access, exact canonical-ingress/quarantine send, own log delivery, and approved bounded metric publication.

- [ ] 2. Add Cell-owned queues, Lambda integration, and least-privilege IAM (AC: 1, 5, 6, 7)
  - [ ] In `modules/ecs-scheduled-job-platform/`, add separate standard SQS resources for canonical ingress and its DLQ, plus a bounded sanitized-rejection quarantine queue and its DLQ. Do not rename or repurpose `aws_sqs_queue.scheduler_ingress`: it remains the Story 1.4 Scheduler **source** queue.
  - [ ] Use the supplied Cell KMS key, 14-day retention, no public policy, and redrive `maxReceiveCount` from 5 through 1000. Preserve source-queue policy ownership in the Cell root. Quarantine records contain stable rejection code, source message ID/hash, source queue ARN, and receipt timestamp only; never retain the raw untrusted body or a secret value.
  - [ ] Add a dedicated Evidence Normalizer Lambda role with the supplied permissions boundary and Lambda-only trust. Grant only `sqs:ReceiveMessage`, `sqs:DeleteMessage`, and `sqs:GetQueueAttributes` on the exact Scheduler source queue; `sqs:SendMessage` on exact canonical ingress and quarantine; own-log-group write actions; and `cloudwatch:PutMetricData` restricted to the configured namespace and the approved bounded dimensions. Do not grant DynamoDB, S3, ECS, STS AssumeRole, `iam:PassRole`, queue/policy mutation, other queue reads, or self-modification.
  - [ ] Add the Lambda function, explicit secret-free environment configuration for the Cell registration, encrypted explicit-retention log group, and SQS event-source mapping. The Lambda has no VPC configuration, public endpoint, function URL, or inbound interface.
  - [ ] Configure `ReportBatchItemFailures`, standard-queue batch size 1-10, batch window 0-300 seconds, timeout 1-900 seconds, and reserved concurrency 2-1000. Validate `scheduler_ingress.visibility_timeout_seconds >= 6 * normalizer_timeout_seconds + normalizer_batch_window_seconds` and `<= 43200`; validate all queue/Lambda controls against `contracts/v1/catalogs/queue-lambda-constraints.json` before apply.
  - [ ] Add all new Cell ARNs to the SSM Cell Contract, outputs, basic example, checked-in Cell Contract fixture, checksum, ownership catalog, manifest/release/migration evidence, and static tests. Keep the SSM path, contract identity, ASCII/JCS guard, and existing integration addresses stable.

- [ ] 3. Implement deterministic, isolated normalizer runtime behavior (AC: 2-5, 8)
  - [ ] Replace only the `runtime/evidence_normalizer/` package stub with typed, testable Python 3.14 code. Keep AWS transport calls behind a narrow adapter so parsing/authorization/normalization is deterministic and unit-testable without AWS credentials; do not add runtime account, Region, Environment, queue, or secret defaults.
  - [ ] Parse each SQS record strictly. Derive authority from record `eventSourceARN`, `awsRegion`, system `attributes.SenderId`, and the Cell registration; require the Scheduler role-ID prefix before `:` to match the registered immutable role ID. Treat all body identity coordinates as assertions, including job ID, producer ID, evidence type, source/schedule ARN, account, Region, owner generation, CONFIG version, schedule generation, scheduled time, and occurrence ID.
  - [ ] Accept only `occurrence.launch.v1` from this source. Verify the registered schedule ARN/group, account/Region, generation, CONFIG version, and canonical Scheduler time. Recompute `occurrence/v1` from the registered job ID, registered schedule generation, and scheduled-time epoch minute; reject a supplied occurrence ID unless it matches.
  - [ ] Define and use the contract-owned Scheduler producer event ID as SHA-256 of exact ASCII bytes `scheduler/v1\n<schedule_arn>\n<scheduled_time>\n<config_version>\n<owner_generation>`. Use Cell-stamped `producer_id = "scheduler"`; derive the payload hash from canonical JSON bytes; preserve an optional sanitized AWS trace header only in the approved trace-context field. Do not use a mutable SQS message ID as the deduplication identity.
  - [ ] Set canonical-envelope `emitted_at` to the canonical Scheduler scheduled time, not the Lambda wall clock, so a replay of identical valid source evidence produces the same bytes.
  - [ ] Validate the completed canonical envelope and secret safety before sending it to canonical ingress. Identical valid records must produce byte-identical canonical envelopes. Duplicate delivery is allowed to emit the same envelope because Story 1.7 owns processed-event deduplication and all occurrence-state mutation.
  - [ ] Classify malformed/unsupported/forged/stale records as permanent rejections: emit one sanitized quarantine record and bounded rejection metric, then acknowledge the source record. Return only transient transport failures in `batchItemFailures`; never raise a batch-wide exception for a record-specific permanent failure.
  - [ ] Use structured secret-free logs with stable machine codes. Do not log raw bodies, untrusted headers, SQS receipt handles, credentials, or unrestricted exception data.

- [ ] 4. Keep Terraform packaging reproducible without committing build output (AC: 1, 7, 8)
  - [ ] Define an explicit trusted normalizer artifact input/interface for `aws_lambda_function` and `source_code_hash`; the caller/CI supplies the immutable package artifact outside the checkout. Terraform validation must not depend on a locally generated zip, and no zip, Terraform state, plan, credentials, or `.terraform/` directory may be committed.
  - [ ] Do not use provisioners, `null_resource`, a checkout-writing archive step, or an unpinned external packaging tool. If a provider/dependency is added for artifact metadata, pin it, update provider locks for required platforms, and document the reproducible build/verification path.
  - [ ] Document external KMS key-policy prerequisites for Lambda/SQS/log use instead of adding broad KMS IAM permissions. Keep code distribution and runtime execution account/Region-local.

- [ ] 5. Add deterministic contract, runtime, Terraform, and IAM-negative proof (AC: 1-8)
  - [ ] Extend contract fixtures/tests for Scheduler raw SQS source shape, exact role-ID prefix, schedule registration, deterministic producer event ID, schema/secret validation, payload hash, trace-context handling, unsupported major, and every assertion mismatch.
  - [ ] Add runtime tests for accepted evidence, duplicate/replay determinism, malformed JSON/schema, oversized body, forged job/producer/type/schedule/group/account/Region/generation/CONFIG/time/occurrence ID, stale role ID, source queue mismatch, cross-account input, and no side effect on every rejection.
  - [ ] Add partial-batch tests containing accepted, permanent-rejection, and transient-failure records. Assert accepted/quarantined records are omitted from `batchItemFailures`, only transient record IDs are returned, and one poison record does not block an unrelated accepted record.
  - [ ] Extend Cell/fixture static tests for encryption, 14-day retention, all redrive policies, visibility formula, event-source mapping response type, Lambda timeout/concurrency/batch bounds, no VPC/function URL, exact IAM resources/trust/boundary, log retention, Cell Contract additions, and absence of materializer/ECS/log/command queues, ledger, Process Manager runtime authority, ECS launch, alarms, and alert routing.
  - [ ] Update module, fixture, and runbook documentation with source authentication, body-assertion semantics, quarantine investigation/replay limits, metrics/log queries, safe rollback, and retained-evidence cleanup boundaries.

- [ ] 6. Run full credential-free validation and record limitations (AC: 1-8)
  - [ ] Run `terraform fmt -check -recursive`, backend-free locked init/validate for every discovered root, Ruff format/check, strict mypy, all contract/runtime tests, Checkov for the Cell and fixture, repository hygiene, `./scripts/validate.sh`, and `git diff --check`.
  - [ ] Do not claim a live Scheduler delivery, Lambda invocation, ECS task, occurrence state, or production alert without recorded disposable-account evidence. Local tests must prove behavior without AWS credentials, plan, apply, state, or saved artifacts.
  - [ ] Rollback disables the normalizer event-source mapping while leaving the canary schedule disabled, retains source/ingress/quarantine queues, DLQs, mappings, and logs through their 14-day investigation window, and reverts only to a compatible Cell Contract/runtime version. It does not delete shared Cell or canary evidence as routine cleanup.

## Dev Notes

### Scope and Ownership

Story 1.5 is the first runtime component. The Cell root owns the normalizer,
its queues and policies, normalizer IAM/logs/mapping, Cell Contract additions,
and the canary-only registration. The canary fixture remains a separate,
backend-free root; it only exposes the scheduler delivery role ID and retains
its disabled schedule. It must not create or mutate Cell queues, policies,
Lambda, registry, or ledger resources.

The existing `scheduler_ingress` name is historical and must be preserved as
the Scheduler **source** queue. Canonical ingress is a new resource with a
different stable address. This story does not create any later producer source
queue, materializer, Process Manager implementation, occurrence ledger,
ECS-event integration, log subscription, deadline scanner, alert path, generic
job module behavior, or ECS launch permission.

### Authorization Boundary

SQS bodies are untrusted. `SenderId` is the non-body Scheduler authority and
has the shape `<immutable-role-id>:<session>`. The Cell registration binds the
immutable role ID plus exact schedule/source identifiers to the canary. The
normalizer compares payload claims to that registration and never selects a
job, producer, generation, CONFIG, or authorization target from the body.

The role must not write DynamoDB in this story. In particular, remove the
stale normalizer ledger write from the IAM catalog rather than carrying it
forward. Story 1.7 introduces processed-event deduplication and occurrence
state; this story may emit duplicate, byte-identical canonical evidence.

### Existing Implementation Intelligence

- Baseline commit is `c564247` (`feat: add platform-owned canary fixture`).
- `modules/ecs-scheduled-job-platform/main.tf` already owns `scheduler_ingress`,
  `scheduler_dlq`, the scheduler group, Process Manager shell, Cell KMS key
  wiring, SSM contract JCS guard, and 14-day scheduler queue retention. Extend
  it additively; preserve all existing resource addresses and the documented
  best-effort canary reservation/CONFIG-publication caveats.
- `fixtures/canary/main.tf` creates the delivery role and disabled Scheduler
  schedule. Its target body currently includes job ID, ownership generation,
  schedule generation, Scheduler scheduled-time context, and schema version.
  Any new body claims remain assertions; add fixture outputs rather than remote
  state coupling.
- `runtime/evidence_normalizer` is a typed source/test skeleton only. The
  repository has no runtime AWS SDK dependency; keep imports deploy-safe and
  isolate transport adapters so local tests do not require AWS clients.
- `tests/contract/support/contracts.py` already provides strict JSON parsing,
  schema validation, RFC 8785 canonical bytes, secret screening,
  `occurrence_id`, and canonical schedule/timestamp handling. Reuse it.

### AWS and Runtime Guardrails

- Standard SQS with a Lambda mapping is at-least-once. Configure
  `ReportBatchItemFailures`; return record `messageId` values only for transient
  failures. AWS documents that a Lambda exception retries the whole SQS batch,
  so record-local permanent failures must be handled inside the batch.
- The source queue visibility timeout must be at least six times the function
  timeout plus batching window, and Lambda validates that function timeout does
  not exceed visibility. Keep the 6 MiB Lambda invocation ceiling and the
  platform's stricter 262,144-byte message limit distinct.
- Platform Lambdas remain outside consumer VPCs and use regional AWS APIs.
  Required tags are `Environment`, `Application`, `Service`, `Owner`, and
  `ManagedBy=Terraform`, with applicable `CostCenter` and `Repository`.
- Metrics may use bounded `job_id`, `environment`, and `state` dimensions only.
  Never put `occurrence_id`, message ID, sender ID, schedule ARN, or raw error
  text in a metric dimension.

### Validation and Documentation

Follow the repository validator's dynamic root discovery, locked backend-free
Terraform initialization, temporary `TF_DATA_DIR`, credential scrubbing, and
Cell-only Checkov exceptions. Update the module README, canary README, and
`docs/runbooks/README.md`; documentation must state that disabling the mapping
is the immediate rollback and that retained evidence is not routine cleanup.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.5]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-4]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-5]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-11-to-AD-13]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-23-to-AD-29]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/solution-design-review.md#Runtime-Processing]
- [Source: _bmad-output/planning-artifacts/prds/prd-demo-bmad-2026-07-13/prd.md#FR-15-to-FR-17]
- [Source: _bmad-output/implementation-artifacts/1-4-register-a-platform-owned-canary-job.md]
- [Source: contracts/v1/catalogs/producers.json]
- [Source: contracts/v1/catalogs/iam.json]
- [Source: contracts/v1/catalogs/queue-lambda-constraints.json]
- [Source: contracts/v1/schemas/evidence-envelope.schema.json]
- [AWS Lambda SQS error handling](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html)
- [AWS Lambda SQS event-source configuration](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-configure.html)

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Created from Epic 1 Story 1.5, the Architecture Spine, solution-design
  review, PRD, Compatibility Package, committed Story 1.4 implementation, AWS
  Terraform implementation standard, and current AWS Lambda/SQS documentation.
- The Story 1.4 baseline is commit `c564247`; its canary schedule stays
  disabled throughout this story.
- AWS documentation verified that SQS Lambda mappings support
  `ReportBatchItemFailures`, require record-level handling to avoid whole-batch
  retry, and recommend visibility of at least six times function timeout plus
  batch window.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.

### File List

- _bmad-output/implementation-artifacts/1-5-authenticate-and-normalize-platform-evidence.md

### Change Log

- 2026-07-16: Created Story 1.5 implementation context and marked it ready for development.
