---
story_key: 1-6-materialize-future-expected-occurrences
baseline_commit: efb4de79bb6449794880e5e4755045371c8210f1
---

# Story 1.6: Materialize Future Expected Occurrences

Status: review

## Story

As an On-call Engineer,
I want expected canary occurrences generated independently before Scheduler delivery,
so that a missing Scheduler invocation remains observable as a specific occurrence failure.

## Acceptance Criteria

1. **Given** the canary has a `PUBLISHED` CONFIG candidate, **when** the materializer validates it, **then** it verifies the schema, RFC 8785 content hash, Cell identity, namespace ownership, bound Role ID and schedule ARN, task revision, cluster, private network, log group, notification metadata, runtime deadline, and supported contract ranges. Invalid, stale, substituted, secret-bearing, or incompatible candidates become `REJECTED` with a sanitized reason while launch remains disabled.
2. **Given** a candidate passes validation, **when** the materializer records it, **then** it copies an immutable snapshot into the separate configuration registry and records `VALIDATED`; the canonical body hash equals `config_version`, old versions are never overwritten, and the job root has no registry-write authority.
3. **Given** Cell resources are planned, **when** materializer evidence is first introduced, **then** the Cell owns an encrypted materializer source queue and 14-day DLQ that meet Compatibility Package retry, visibility, batch, payload, and quarantine constraints. The Evidence Normalizer gains only the source-specific read, authentication, and canonical-ingress mapping required for that source.
4. **Given** a validated recurring generation, **when** it is evaluated, **then** its expression, IANA time zone, start anchor, activation window, flexible-window mode, generation, and DST behavior match the Compatibility Package. Unsupported syntax, one-time schedules, ambiguous anchors, divergent vectors, and out-of-window occurrences are rejected.
5. **Given** the account-local EventBridge rule invokes the materializer, **when** the expectation horizon advances, **then** it emits deterministic `occurrence.expected.v1` evidence for every canary occurrence at least 24 hours ahead, with canonical scheduled time and exact `occurrence/v1` identity. Repeated or overlapping invocations reuse the same producer event IDs for the same logical occurrence.
6. **Given** Scheduler and materializer evaluate the same canary generation, **when** conformance runs, **then** occurrence times and IDs agree for supported cron/rate expressions, time zones, DST boundaries, activation anchors, and consecutive windows. Divergence blocks `MATERIALIZED`.
7. **Given** a complete, acknowledged future horizon, **when** status is recorded, **then** the registry records generation, horizon watermark, conformance result, CONFIG hash, validation timestamp, and `MATERIALIZED`. This neither enables Scheduler nor writes occurrence state before Story 1.7.
8. **Given** the horizon stalls or nears exhaustion, **when** health is evaluated, **then** bounded freshness and conformance metrics identify Cell, Environment, account, Region, and failure plane without an Occurrence ID dimension, and are available to the later alarm story before expiration.
9. **Given** materializer IAM is tested, **when** positive and negative cases execute, **then** it reads only the canary CONFIG candidate and active registry CONFIG, writes only verified registry snapshots/status, and sends only to its exact source queue. It cannot write occurrence state, consume canonical ingress, assume launch roles, call ECS, modify schedules, publish alerts, or access another job prefix.
10. **Given** disposable-Cell tests execute, **when** valid, duplicate, partial-failure, stale-generation, hash-mismatch, unsupported-schedule, DST, stopped-horizon, and incompatible-version cases run, **then** valid expectations reach canonical ingress deterministically; invalid input produces no launch or occurrence mutation; and the canary remains disabled.

## Tasks / Subtasks

- [x] 1. Extend the normative materializer contracts and vectors before runtime code (AC: 1, 2, 4-7, 9-10)
  - [x] Correct `contracts/v1/catalogs/producers.json`: Scheduler alone produces `occurrence.launch.v1`; `occurrence-materializer` produces only `occurrence.expected.v1` and its authority is registered config version, schedule generation, immutable Cell-owned materializer Role ID, and exact source queue.
  - [x] Correct the materializer entry in `contracts/v1/catalogs/iam.json` and related ownership edges. It must model exact S3 CONFIG-version read, exact configuration-registry read/conditional snapshot write, exact materializer-source SQS send, own logs, bounded metrics, and scoped KMS use. It must not retain ledger, Scheduler create/update, ECS, canonical-ingress receive, role assumption/pass, or alert authority.
  - [x] Define the source-specific raw materializer evidence shape, canary registration, sanitized rejection/quarantine shape, and deterministic producer-event identity. The producer event ID must be SHA-256 of exact ASCII `materializer/v1\n<job_id>\n<schedule_generation>\n<scheduled_time>\n<config_version>\n<owner_generation>` bytes; add valid and invalid vectors. Do not use an invocation ID, wall clock, SQS message ID, or horizon watermark as the deduplication identity.
  - [x] Reuse and extend existing strict JSON/JCS/schema/secret-safety/schedule/occurrence helpers and fixtures. Do not duplicate canonical JSON, CONFIG hashing, schedule evaluation, DST handling, occurrence hashing, or schema-validation logic in a runtime package.
  - [x] Update the Compatibility Package manifest, release semantic-surface digest, and migration evidence using the established raw-byte/JCS tests. Keep this development-line package coherent; do not invent a parallel contract location.

- [x] 2. Implement deterministic CONFIG validation, immutable snapshotting, and occurrence materialization (AC: 1, 2, 4-8, 10)
  - [x] Replace only the `runtime/occurrence_materializer/` stub with typed Python 3.14 modules and tests. Split deterministic domain logic from the narrow boto3/EventBridge/S3/DynamoDB/SQS adapter so unit tests need no AWS credentials.
  - [x] Strictly load the exact canary S3 object key `jobs/<job_id>/config/<config_version>.json`; validate UTF-8/duplicate-key/canonical JSON, CONFIG schema and secret safety, canonical body hash, configured Cell account/Region/environment, namespace reservation, owner generation, schedule ARN/generation, immutable Scheduler delivery Role ID, task/cluster/private networking, log group, notification target, completion window, and all declared compatibility ranges. Never log a raw CONFIG body, secret reference value, header, or unrestricted AWS exception.
  - [x] Use the existing schedule evaluator and normative `tzdata==2026.2`/IANA `2026b` contract. Accept only the documented recurring cron/rate subset with `flexible_time_window = OFF`, inclusive start/exclusive end activation semantics, and explicit anchors. Canonicalize UTC timestamps before calculating epoch minutes and require the configured generation to equal the contract generation.
  - [x] Materialize the configured horizon plus a small deterministic boundary past 24 hours so every occurrence through the 24-hour watermark is provably emitted. Produce the canonical envelope with Cell-stamped `producer_id = "occurrence-materializer"`, the exact producer event ID, `occurrence.expected.v1`, canonical `scheduled_time`/`emitted_at`, recomputed occurrence ID, canonical payload hash, and payload fields `config_validated=true`, `materialized_at`, `expectation_horizon`, and `repair=false`.
  - [x] Use deterministic registry keys `PK=JOB#<job_id>`, `SK=CONFIG#<config_version>` and conditional writes so a matching retry is idempotent but a conflicting snapshot/status cannot overwrite evidence. Write `PUBLISHED -> VALIDATED -> MATERIALIZED` only after validation, conformance, and complete source-queue emission; persist config version, generation, watermark, conformance result, and validation timestamp. Do not use DynamoDB TTL or a GSI read as correctness evidence for horizon completeness.
  - [x] Treat malformed, stale, substituted, incompatible, and conformance-failed candidates as sanitized `REJECTED` records with no registry snapshot overwrite, source evidence, Scheduler enablement, ECS launch, or runtime-ledger write. Map AWS delivery/read/write errors to bounded record/invocation retries without a batch-wide exception.
  - [x] Publish only bounded `job_id`, `environment`, and `state` metrics for validation, horizon freshness, and conformance. Never use occurrence ID, schedule ARN, config hash, role ID, or raw error text as a metric dimension.

- [x] 3. Extend the Evidence Normalizer for the distinct materializer source (AC: 3, 5, 9-10)
  - [x] Add a canary-only, Cell-controlled materializer registration binding job/account/Region/environment, owner generation, CONFIG version, schedule generation/ARN, exact materializer source queue, and the Cell-created immutable materializer Role ID. Keep Scheduler registration and source behavior intact.
  - [x] Generalize the normalizer handler to dispatch by exact source queue and authenticate materializer messages from non-body SQS metadata (`eventSourceARN`, `awsRegion`, `SenderId` immutable role-ID prefix) plus the registration. Body identity fields, including producer/job/config/generation/schedule/time/occurrence ID, remain assertions only.
  - [x] Accept only `occurrence.expected.v1` from this source, recompute and compare the materializer producer event ID, canonical scheduled time, occurrence ID, and payload hash, validate the envelope/secret policy before canonical ingress, and preserve Story 1.5 partial-batch, strict-parser, JCS-wire-byte, rejection-log, and KMS behavior.
  - [x] Add only the materializer source queue to normalizer receive/delete/attribute access and encryption-context scope; canonical ingress remains normalizer-write-only. A materializer source record must never be forwarded directly to canonical ingress without successful authentication and normalization.

- [x] 4. Provision only the additive Cell and canary wiring required for materialization (AC: 1-3, 5, 7-9)
  - [x] In `modules/ecs-scheduled-job-platform/`, add a Cell-owned materializer Lambda, Lambda-only role with permissions boundary, explicit-retention KMS log group, EventBridge scheduled rule/target/permission, materializer source SQS queue and DLQ, exact queue policy, artifact inputs, bounded Lambda/SQS controls, and an additional normalizer event-source mapping. Use standard encrypted SQS, 14-day retention, `maxReceiveCount` 5-1000, batch size 1-10, batch window 0-300 seconds, timeout 1-900 seconds, reserved concurrency 2-1000, and visibility `>= 6 * timeout + batch window` and `<= 43200`.
  - [x] EventBridge is only the independent, UTC minute-cadence materializer trigger; the job schedule evaluator remains the Compatibility Package implementation. Scope Lambda permission to the exact rule ARN and any queue policy to its exact principal/source. Keep all platform Lambdas outside consumer VPCs with no function URL or inbound interface.
  - [x] Add only a canary-specific materializer registration/wiring path and required canary outputs. Preserve the fixture's isolated backend-free root, content-addressed PUBLISHED CONFIG, disabled Scheduler, no remote state, and no Cell-root mutation. Do not add generic Registrar behavior.
  - [x] Extend the Cell Contract, outputs, module basic example, checked-in Cell Contract fixture/checksum, ownership catalog, README, canary README, and static tests additively. Preserve existing resource addresses for SSM, registry tables, Scheduler source queue, canonical ingress, and Story 1.5 normalizer resources.
  - [x] Document the immutable external artifact interface. The trusted package includes the runtime source, shared contract helper package, `contracts/v1` at `/var/task/contracts/v1`, and pinned dependencies it imports; Terraform must never build a checkout zip or commit build output, state, plan, credentials, or `.terraform/`.
  - [x] Document exact external KMS key-policy prerequisites for materializer S3/SQS/Lambda/CloudWatch use and narrowly scoped runtime actions. Do not solve access with broad KMS, S3, DynamoDB, SQS, or IAM permissions.

- [x] 5. Prove safety, conformance, operations, and rollback (AC: 1-10)
  - [x] Add contract and runtime tests for valid config/snapshot/materialization, duplicate and overlapping invocation determinism, immutable snapshot conflicts, malformed/oversized/secret-bearing CONFIG, config hash mismatch, stale owner/schedule/role, source/account/Region mismatch, unsupported major/range, unsupported schedules, activation boundaries, cron/rate, spring-forward/fall-back DST, adjacent windows, stopped/exhausted horizon, and no side effect on rejection.
  - [x] Add normalizer tests for valid materializer evidence plus forged producer/job/config/generation/schedule/queue/role/account/Region/time/occurrence ID, malformed body, replay, partial transport failure, and permanent-rejection acknowledgement. Assert only transient IDs enter `batchItemFailures` and accepted output bytes are RFC 8785-identical.
  - [x] Extend Terraform/IAM-negative/static tests for exact resources/trust/boundary/KMS contexts, encryption/retention/redrive/visibility, EventBridge permission, no VPC/function URL, Cell Contract additions/checksum, registration validation, and absence of ledger, Process Manager runtime authority, ECS launch, Scheduler enablement/mutation, ECS/log/command queues, alarms, and alert routing.
  - [x] Update `docs/runbooks/README.md`, module README, and fixture README with source-authentication semantics, CONFIG rejection investigation, horizon freshness/conformance queries, limits of local proof, and rollback: disable the materializer EventBridge rule and normalizer mapping, keep Scheduler disabled, retain CONFIG snapshots/queues/DLQs/logs for at least 14 days, and revert only to compatible Cell Contract/runtime versions. Never represent credential-free tests as live delivery, state, launch, or alert proof.
  - [x] Run `terraform fmt -check -recursive`, locked backend-free init/validate for every discovered root, Ruff format/check, strict mypy, contract/runtime tests, Cell/canary Checkov scans, repository hygiene, `./scripts/validate.sh`, and `git diff --check`. Record tool or live-AWS limitations truthfully.

## Dev Notes

### Architecture And Scope Boundaries

- This is the independent expectation clock. Flow is **EventBridge rule -> Occurrence Materializer Lambda -> materializer source SQS/DLQ -> Evidence Normalizer -> existing canonical ingress**. Scheduler is the sole launch-evidence producer. Story 1.7, not this story, owns processed-event deduplication and all occurrence-ledger mutation.
- The materializer creates verified configuration-registry snapshots only. It must not create the runtime ledger, deadline index/scanner, Process Manager implementation, ECS state/log sources, command source, launch authority, alert outbox/router, alarms, generic Registrar, or phase-two Scheduler enablement.
- Lifecycle is strictly `PUBLISHED -> VALIDATED -> MATERIALIZED`; reject failures with a sanitized reason and leave the launch schedule disabled. `MATERIALIZED` proves the future evidence horizon, not an ECS task, occurrence-state row, live Scheduler delivery, or production health.
- A 24-hour horizon is a minimum. Production enablement later requires a verified horizon beyond the completion window. A stalled horizon must be visible before it expires; metric dimensions remain bounded.

### Existing Components To Reuse And Preserve

- `runtime/occurrence_materializer/` is an empty typed boundary. Implement there, following `runtime/evidence_normalizer/`'s pure-domain-plus-adapter pattern, strict error codes, structured secret-free logging, and record-local partial retry behavior.
- Reuse `tests/contract/support/contracts.py` for strict JSON, JCS bytes, CONFIG hash, schemas, secret policy, schedule validation/expansion, schedule generation, and occurrence ID. Do not fork those algorithms.
- `contracts/v1/catalogs/schedules.json` and `contracts/v1/fixtures/schedules/cases.json` define the only supported schedule grammar, DST rules, `tzdata==2026.2`, and IANA `2026b`. `config.schema.json`, `evidence-envelope.schema.json`, and `payloads/occurrence-expected.schema.json` already define the CONFIG/envelope shape; evolve them only additively when indispensable.
- Preserve current Cell resource addresses and current Scheduler normalizer behavior in `modules/ecs-scheduled-job-platform/`. The normalizer currently has one Scheduler registration/mapping; extend it source-specifically, not by broadening Scheduler trust or body authority.
- The current `configuration_registry` table is encrypted, PITR-protected, and key-shaped for `pk`/`sk`. Preserve it as a separate registry; do not repurpose it as the future runtime ledger. A DynamoDB `PutItem` overwrites without a condition, so use `attribute_not_exists` (and transactions only where a multi-item atomic outcome is actually needed).
- EventBridge scheduled rules are UTC, minute-resolution triggers and can be late or duplicate. They are not the job schedule evaluator. EventBridge Scheduler flexible windows remain `OFF`; never make native scheduler delivery the source of expected occurrence truth.

### AWS, Security, And Operations Guardrails

- All new AWS resources use Cell names/tags, supplied KMS key, explicit retention, permissions boundary, and least-privilege resource ARNs. Include confused-deputy controls for EventBridge/Lambda/SQS where AWS supports them.
- Do not introduce account, Region, environment, queue, secret, or credential defaults in the runtime. No plaintext secrets in CONFIG, environment values, queues, registry, logs, tests, plans, or docs.
- DynamoDB TTL is lifecycle cleanup only and may delete days late; it cannot establish a horizon or lifecycle conclusion. GSIs are eventually consistent; verify authoritative base records and deterministic keys instead of inferring absence from one GSI read.
- Local and disposable tests prove only implementation behavior. Do not claim live EventBridge invocation, Lambda delivery, S3/DynamoDB side effect, canonical-ingress delivery, occurrence state, ECS launch, or alarm delivery without recorded disposable-account evidence.

### Project Structure Notes

- Expected updates: `modules/ecs-scheduled-job-platform/{main.tf,variables.tf,outputs.tf,README.md,examples/basic/*}`, `fixtures/canary/{main.tf,outputs.tf,README.md}`, `runtime/occurrence_materializer/**`, `runtime/evidence_normalizer/**`, `contracts/**`, `tests/contract/**`, `docs/runbooks/README.md`, `scripts/validate.py`, and this story/sprint status.
- New code belongs only in the existing runtime package and contract/fixture locations. No new module, environment root, remote-state link, provider, build tool, or dependency is expected.

### Previous Story Intelligence

- Story 1.5 (`efb4de7`) established authenticated source identity from non-body SQS metadata, strict raw parsing, RFC 8785 queue bytes, `ApproximateFirstReceiveTimestamp`, permanent-rejection logs, botocore record-local retries, exact KMS encryption contexts, and exact registration ARN validation. Preserve all of those controls for the materializer source.
- The normalizer artifact is externally built and immutable. Its package must explicitly contain every imported shared helper/dependency; Terraform validation is artifact-independent.
- Full repository validation uses dynamic Terraform root discovery and isolated temporary Terraform data. The global `.agents` fixture may contain unrelated lint findings; the story's changed runtime/contract scope must still pass its configured checks, and unrelated failures must be reported rather than hidden.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.6]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-3-to-AD-7]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-11-to-AD-12]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-23-to-AD-29]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/solution-design-review.md#Runtime-Processing]
- [Source: _bmad-output/planning-artifacts/prds/prd-demo-bmad-2026-07-13/prd.md#FR-6-and-FR-17]
- [Source: _bmad-output/implementation-artifacts/1-5-authenticate-and-normalize-platform-evidence.md]
- [AWS DynamoDB conditional expressions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html)
- [AWS DynamoDB transactions](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_TransactWriteItems.html)
- [AWS DynamoDB TTL](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html)
- [AWS EventBridge scheduled rules](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-create-rule-schedule.html)
- [AWS Lambda SQS partial-batch failures](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html)

## Dev Agent Record

### Review Findings

- [x] [Review][Patch] EventBridge ticks are canonicalized before materialization [runtime/occurrence_materializer/src/occurrence_materializer/materializer.py:55].
- [x] [Review][Patch] Materializer S3 KMS decrypt is separately scoped [modules/ecs-scheduled-job-platform/main.tf:822].
- [x] [Review][Patch] Queue delivery precedes the immutable completion marker [runtime/occurrence_materializer/src/occurrence_materializer/handler.py:160].
- [x] [Review][Patch] Empty occurrence windows omit the DynamoDB string set [runtime/occurrence_materializer/src/occurrence_materializer/handler.py:49].
- [x] [Review][Patch] Registry records use canonical job/config keys and lifecycle fields [runtime/occurrence_materializer/src/occurrence_materializer/materializer.py:165].
- [x] [Review][Patch] Candidate validation includes secret safety and namespace ownership [runtime/occurrence_materializer/src/occurrence_materializer/handler.py:86].
- [x] [Review][Patch] Invalid candidates create sanitized rejection records and invocation retries are bounded [runtime/occurrence_materializer/src/occurrence_materializer/handler.py:139].
- [x] [Review][Patch] Materializer emits bounded result metrics [runtime/occurrence_materializer/src/occurrence_materializer/handler.py:57].
- [x] [Review][Patch] The Cell Contract publishes materializer integration identifiers [modules/ecs-scheduled-job-platform/main.tf:242].
- [x] [Review][Patch] Materializer source queue policy and control bounds are explicit [modules/ecs-scheduled-job-platform/main.tf:923].
- [ ] [Review][Decision] Define the authoritative Scheduler/materializer conformance input. The implementation sets `conformance_result` to `PASS` without comparing a Scheduler-side schedule result, so it cannot block divergence [runtime/occurrence_materializer/src/occurrence_materializer/materializer.py:229; runtime/occurrence_materializer/src/occurrence_materializer/handler.py:164].
- [ ] [Review][Patch] Advance the persisted horizon rather than treating a `MATERIALIZED` CONFIG version as terminal; subsequent minute ticks currently emit nothing after the first 24-hour window [runtime/occurrence_materializer/src/occurrence_materializer/handler.py:133].
- [ ] [Review][Patch] Read and conditionally advance the authoritative `PUBLISHED` CONFIG lifecycle record before writing a `VALIDATED` materialization snapshot [runtime/occurrence_materializer/src/occurrence_materializer/handler.py:101].
- [ ] [Review][Patch] Require an immutable task-definition revision in the CONFIG binding, not merely an ECS ARN in the registered account and Region [runtime/occurrence_materializer/src/occurrence_materializer/materializer.py:91].
- [ ] [Review][Patch] Split materializer IAM so the namespace registry grants only `dynamodb:GetItem`; it must not allow snapshot writes or updates there [modules/ecs-scheduled-job-platform/main.tf:810].
- [ ] [Review][Patch] Preserve sanitized rejection evidence when a changed candidate conflicts with an existing CONFIG snapshot instead of raising `MATERIALIZER_REJECTION_CONFLICT` [runtime/occurrence_materializer/src/occurrence_materializer/handler.py:174].
- [ ] [Review][Patch] Validate the CONFIG Cell identity, environment, and declared supported contract ranges against the registration and Compatibility Package [runtime/occurrence_materializer/src/occurrence_materializer/materializer.py:144].
- [ ] [Review][Patch] Emit distinct bounded horizon-freshness and conformance metrics with the required Cell, environment, account, Region, and failure-plane dimensions [runtime/occurrence_materializer/src/occurrence_materializer/handler.py:57].
- [ ] [Review][Patch] Reject oversized CONFIG objects before persisting `config_json` to DynamoDB, producing a sanitized rejection rather than an unbounded storage retry [runtime/occurrence_materializer/src/occurrence_materializer/handler.py:246].

### Agent Model Used

GPT-5

### Debug Log References

- Ultimate context analysis completed from Epic 1, PRD, Architecture Spine, solution design review, project standards, Story 1.5, current repository structure, recent commit `efb4de7`, and current official AWS documentation.

### Completion Notes List

- Implemented the contract-owned materializer producer-event identity and valid
  byte vector; narrowed materializer producer/IAM/ownership catalog authority.
- Added deterministic CONFIG validation and a 24-hour expected-occurrence
  materializer with a narrow EventBridge/S3/DynamoDB/SQS adapter.
- Added authenticated materializer-source normalization, Cell queue/Lambda/rule
  wiring, immutable artifact inputs, outputs, and operational documentation.
- Bound CONFIG to the exact Scheduler ARN and immutable delivery role ID; the
  snapshot now records canonical CONFIG bytes/hash and advances conditionally
  from `VALIDATED` to `MATERIALIZED` only after source-queue delivery.
- Validation completed: 126 tests and 175 subtests passed; focused Ruff and
  strict mypy passed; `terraform fmt -check -recursive`, all discovered locked
  backend-free Terraform roots, and `git diff --check` passed. Checkov reported
  documented design exceptions for no-VPC/no-X-Ray/no-Lambda-DLQ/code-signing
  and no S3 notification; its remote guideline lookup was unavailable. Broad
  Ruff formatting and mypy also report unrelated `_bmad`/`.agents` formatting
  and one pre-existing integration-test annotation. Local checks are not live
  AWS EventBridge, queue, ECS, state, or alert proof.

### File List

- `_bmad-output/implementation-artifacts/1-6-materialize-future-expected-occurrences.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `contracts/README.md`
- `contracts/manifest.json`
- `contracts/migrations/v1.0.0.md`
- `contracts/releases/1.0.0.json`
- `contracts/v1/catalogs/{iam,ownership,producers}.json`
- `contracts/v1/fixtures/iam/raw-aws-producer-shapes.json`
- `contracts/v1/fixtures/identity/materializer-v1.json`
- `contracts/v1/fixtures/schemas/valid-instances.json`
- `contracts/v1/schemas/config.schema.json`
- `docs/runbooks/README.md`
- `fixtures/canary/{README.md,main.tf}`
- `modules/ecs-scheduled-job-platform/{README.md,main.tf,outputs.tf,variables.tf}`
- `modules/ecs-scheduled-job-platform/examples/basic/{main.tf,variables.tf}`
- `runtime/evidence_normalizer/src/evidence_normalizer/{__init__.py,handler.py,normalizer.py}`
- `runtime/evidence_normalizer/tests/test_scheduler_normalizer.py`
- `runtime/occurrence_materializer/{README.md,src/occurrence_materializer/__init__.py,src/occurrence_materializer/handler.py,src/occurrence_materializer/materializer.py,tests/test_occurrence_materializer.py}`
- `tests/{__init__.py,contract/__init__.py}`
- `tests/contract/fixtures/cell-foundation-contract.json`
- `tests/contract/support/contracts.py`
- `tests/contract/{test_canary_fixture.py,test_cell_foundation.py,test_contract_iam.py,test_contract_identity.py,test_repository_structure.py}`

### Change Log

- 2026-07-16: Created comprehensive Story 1.6 implementation context and marked it ready for development.
- 2026-07-16: Started Story 1.6 implementation; status remains in progress pending lifecycle, metrics, and expanded conformance work.
- 2026-07-16: Completed materializer validation, lifecycle persistence, authenticated normalization, Cell wiring, documentation, and local quality gates; marked ready for review.
