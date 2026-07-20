---
story_key: 1-7-record-deterministic-occurrence-state
baseline_commit: df49485
---

# Story 1.7: Record Deterministic Occurrence State

Status: ready-for-dev

## Story

As an On-call Engineer,
I want one authoritative processor to record expected occurrences deterministically,
so that retries and reordered evidence cannot corrupt or duplicate the Cell's operational truth.

## Acceptance Criteria

1. **Given** canonical ingress contains valid `EXPECTED` evidence, **when** the Process Manager consumes it, **then** it verifies the envelope schema and supported major, recomputes Occurrence ID, resolves the exact immutable CONFIG, and verifies its canonical hash; **and** unknown jobs, unsupported versions, inactive generations, mismatched CONFIG, or identity disagreement cause no ledger mutation.

2. **Given** occurrence state is written for the first time, **when** Cell resources are planned, **then** an encrypted occurrence ledger is created with production PITR, protected retention, canonical occurrence and processed-event keys, and only the access patterns required by this story; **and** task-ARN indexes, deadline indexes, alert-outbox items, and notification-ledger resources are not created until their first consuming stories.

3. **Given** one valid expected event is accepted, **when** the Process Manager commits it, **then** one conditional DynamoDB transaction records the immutable processed event and creates or reduces the canonical occurrence to `EXPECTED` with job, generation, CONFIG, scheduled time, deadline, and evidence provenance; **and** the same producer event ID cannot be accepted twice.

4. **Given** the same logical expectation arrives more than once or in a different delivery order, **when** the reducer evaluates all accepted evidence, **then** the occurrence remains one logical record with the same state and audit history; **and** no duplicate delivery creates another occurrence, changes its immutable coordinates, or extends its deadline.

5. **Given** evidence permitted by the Compatibility Package arrives before its live producer integration exists, **when** reducer unit tests execute, **then** all published state-permutation fixtures converge on their documented state without arrival-order dependence; **and** runtime wiring accepts only producer types registered by completed stories, so fixture coverage does not grant premature live authority.

6. **Given** malformed, unauthorized, poison, or transiently failing canonical records are processed in one batch, **when** the invocation completes, **then** partial-batch handling retries only transient failures, rejects deterministic contract failures, and redrives poison records without blocking valid expectations; **and** unsupported or quarantined evidence is retained with a stable machine code and secret-free operator message.

7. **Given** the Process Manager role shell from Story 1.4 is activated, **when** its effective authority is analyzed, **then** it can consume canonical ingress, read verified CONFIG, conditionally write only occurrence and processed-event records, publish bounded metrics, and write its own retained logs; **and** it still cannot call ECS, assume job launch roles, create task attempts, change CONFIG or schedules, write alert records, pass roles, or alter its authorization path.

8. **Given** an operator queries a canary occurrence, **when** supported operational output or diagnostic tooling is used, **then** the operator can retrieve state, scheduled time, completion deadline, CONFIG version, evidence provenance, and last reduction time without direct Terraform-state access; **and** secret values, raw CONFIG bodies, and unrestricted evidence payloads are excluded.

9. **Given** ledger or Process Manager changes are validated, **when** contract, unit, IAM-negative, retry, and disposable-Cell tests run, **then** they cover first expectation, duplicates, reordered delivery, wrong identity, stale CONFIG, unsupported schema, conditional conflicts, partial batches, and restart after transaction commit; **and** the canary's materialized expectations become queryable while Scheduler remains disabled and no ECS task launches.

## Tasks / Subtasks

- [ ] 1. Extend the normative ledger and reducer contract before runtime code (AC: 1-5, 9)
  - [ ] Verify or add only the additive occurrence-ledger and processed-event schema/catalog vectors needed by this story. Preserve `occurrence/v1`, canonical envelope, `occurrence-record.schema.json`, `processed-event.schema.json`, `keys-and-correlation.json`, and `reducer.json` as the sources of truth.
  - [ ] Define exact DynamoDB keys: occurrence `PK=JOB#<job_id>`, `SK=OCCURRENCE#<occurrence_id>`; processed event `PK=EVENT#<producer_id>`, `SK=<producer_event_id>`. Include immutable coordinates, deadline, state, evidence IDs/provenance, and last reduction timestamp without storing raw payloads or CONFIG bodies.
  - [ ] Add/extend IAM ownership and producer catalogs for the Process Manager's expected-evidence authority only. Do not grant live runtime processing for Scheduler launch, ECS, completion, deadline, command, or alert producers before their stories activate those integrations.
  - [ ] Keep reducer fixtures bounded and commutative. The published `contracts/v1/fixtures/reducer/cases.json` must remain the executable source for state-permutation behavior, including duplicates, digest conflicts, deadline facts, and `AMBIGUOUS` outcomes.
  - [ ] Update manifest/release/migration checksums only when contract bytes change; do not create a parallel contract location or silently change a major/schema version.

- [ ] 2. Implement deterministic Process Manager domain logic and adapter (AC: 1, 3-6, 8-9)
  - [ ] Replace only the `runtime/process_manager/` stub with typed Python 3.14 code following the evidence normalizer/materializer pure-domain-plus-narrow-AWS-adapter pattern.
  - [ ] Parse strict RFC 8785 canonical ingress bytes, validate the supported envelope major and secret policy, require `occurrence.expected.v1` from the authenticated materializer source, recompute Occurrence ID and payload hash, and reject all mismatches before AWS writes.
  - [ ] Read the exact `JOB#<job_id>/CONFIG#<config_version>` registry record with a strongly consistent base-table read. Require an immutable validated/materialized snapshot, exact `config_hash == config_version`, active owner/schedule generation, and canonical CONFIG bytes; derive `deadline_at` from the verified scheduled time plus the configured completion window.
  - [ ] Build deterministic occurrence and processed-event records. Preserve immutable job/config/generation/scheduled-time coordinates, never extend a deadline on duplicate delivery, and store only bounded evidence IDs/provenance and sanitized machine codes.
  - [ ] Commit the first accepted expected event with one DynamoDB `TransactWriteItems` operation that conditionally creates the processed-event record and occurrence record. Use an immutable processed-event digest and conditional conflict handling so a retry after a transaction commit becomes a duplicate/no-op, while a changed body for the same producer event ID becomes a retained conflict without overwriting state.
  - [ ] For an existing occurrence, reduce accepted facts using the Compatibility Package reducer semantics and conditionally update the single canonical occurrence record. Do not implement arrival-order transitions, last-write-wins terminal updates, TTL/GSI correctness, or raw evidence storage.
  - [ ] Keep deterministic contract failures record-local and acknowledged after sanitized quarantine/rejection delivery. Return only transient transport/storage failures in `batchItemFailures`; never throw after a valid record has already been committed in a way that causes an unsafe second mutation.
  - [ ] Emit only bounded metrics using the established `job_id`, `environment`, and `state` dimensions; never use Occurrence ID, producer event ID, raw error text, CONFIG body/hash, or task ARN as a metric dimension.
  - [ ] Add an operator-safe query/diagnostic boundary only if an existing output path supports it. It must return state, schedule time, deadline, CONFIG version, provenance IDs, and last reduction time, never raw CONFIG or unrestricted evidence.

- [ ] 3. Add only the Cell resources and wiring required for occurrence state (AC: 2, 7, 9)
  - [ ] Add an encrypted Cell-owned occurrence ledger table with explicit billing/retention controls, production PITR and deletion protection inputs consistent with the existing module, required tags, and stable resource addresses.
  - [ ] Do not add GSIs for task ARN or deadline, alert outbox/notification ledger items, task-attempt records, ECS integrations, alarms, or operator command resources; those belong to their first consuming stories.
  - [ ] Add a Cell-owned Process Manager Lambda artifact input, explicit log group retention/KMS configuration, bounded timeout/concurrency, canonical-ingress event-source mapping with partial-batch responses, and only the exact role/policy permissions required by this story.
  - [ ] Scope IAM to the canonical ingress queue, exact configuration-registry read path, occurrence-ledger table, bounded CloudWatch namespace, own logs, and required KMS encryption contexts. Preserve the existing Process Manager role shell address and permissions boundary; do not grant `ecs:*`, `sts:AssumeRole`, `iam:PassRole`, Scheduler mutation, CONFIG writes, alert writes, or self-policy/trust changes.
  - [ ] Extend Cell Contract outputs and static fixtures additively with ledger, Process Manager, and mapping identifiers. Preserve all existing SSM, registry, Scheduler, normalizer, and materializer addresses/checksums.

- [ ] 4. Prove reducer, transaction, security, and operational behavior (AC: 1-9)
  - [ ] Add runtime tests for valid expected evidence, exact CONFIG lookup/hash, invalid schema/major, forged occurrence identity, unknown job, stale generation, missing/incomplete snapshot, duplicate same digest, same producer-event conflict, reordered evidence, immutable-coordinate conflict, deadline calculation, transaction-commit retry, and no-side-effect rejection.
  - [ ] Add reducer tests that execute every published permutation fixture and prove duplicate/reordered inputs converge to one state and one deadline. Include `AMBIGUOUS` for digest/task/completion/terminal conflicts even though later producers are not live-wired.
  - [ ] Add adapter tests for transient DynamoDB/SQS/CloudWatch failures, partial-batch output, poison-message redrive, quarantine delivery failure, restart after committed transaction, and no batch-wide blocking.
  - [ ] Add Terraform/IAM-negative/static tests for PITR, retention, encryption, tags, no GSI/no alert resources, exact queue/table/KMS scope, boundary/trust, no ECS/STS/PassRole/Scheduler/CONFIG mutation, no public interface, and Cell Contract checksum stability.
  - [ ] Update Process Manager README, Cell module README, runbook, and canary README with query fields, duplicate semantics, state/reducer limitations, retry behavior, rollback order, retention, and the explicit boundary that local tests do not prove live AWS delivery or state.
  - [ ] Run `terraform fmt -check -recursive`, locked backend-free init/validate for every discovered root, Ruff format/check, strict mypy, contract/runtime/integration tests, Checkov, repository hygiene, `./scripts/validate.sh`, and `git diff --check`. Record live-AWS and network limitations honestly.

## Dev Notes

### Architecture and Scope Boundaries

- The Process Manager is the only runtime-ledger writer. The materializer and normalizer emit evidence; they do not write occurrence state. This story activates expected-evidence processing only; ECS launch, task attempts, completion correlation, deadline scanning, alerts, commands, and recovery remain later stories.
- The canonical state is a deterministic reduction of immutable, deduplicated facts: `EXPECTED`, `STARTED`, `SUCCEEDED`, `FAILED`, `OVERDUE`, `MISSED`, and `AMBIGUOUS`. Do not encode a one-way arrival-order state machine.
- A valid expected event must not enable Scheduler, launch ECS, or claim live delivery. The canary schedule remains disabled.
- A failed or uncertain transaction must fail closed. A retry after a committed transaction must be identified as duplicate/no-op from the immutable processed-event record, not replayed as a second state mutation.

### Existing Components to Reuse

- Reuse `tests/contract/support/contracts.py` for strict JSON/JCS, schema validation, CONFIG hashing, Occurrence ID, and reducer fixture semantics; do not fork identity or reducer algorithms.
- Reuse `contracts/v1/catalogs/reducer.json`, `keys-and-correlation.json`, `iam.json`, `ownership.json`, `producers.json`, `metrics-alerts.json`, and existing occurrence/processed-event schemas and fixtures.
- Reuse the existing canonical ingress queue, normalizer mapping, Cell Contract, configuration registry, KMS key, tags, permissions boundary, and Process Manager role shell. Preserve all Terraform addresses.
- The current Process Manager runtime is only a package boundary and test. New implementation belongs under `runtime/process_manager/src/process_manager/` with focused tests under `runtime/process_manager/tests/`.

### DynamoDB Transaction Guardrails

- Use `TransactWriteItems` for the coupled processed-event/occurrence first-accept operation. Conditions must protect immutable keys and reject conflicting existing records.
- Do not use DynamoDB TTL, an eventually consistent GSI, or absence from one query as correctness evidence. The base table and strongly consistent `GetItem` are authoritative.
- Keep stored data secret-free and bounded. `config_json`, raw message bodies, raw AWS exceptions, headers, and unbounded evidence payloads must never enter the ledger or logs.
- Preserve the exact deadline derived from the verified CONFIG and scheduled time. Duplicate or reordered evidence cannot extend it or mutate immutable coordinates.

### Retry and Partial-Batch Guardrails

- Standard SQS delivery is at-least-once. The event-source mapping must use `ReportBatchItemFailures`; deterministic rejection/quarantine succeeds for that record, while transient delivery/storage failures return that record's message ID only.
- If a Process Manager invocation throws, AWS treats the complete batch as failed; catch record-local failures at the adapter boundary and return valid item identifiers.
- A transaction commit followed by process loss is expected. The next delivery must reconcile from the processed-event record and avoid a second occurrence mutation.

### IAM and Terraform Guardrails

- Follow `_bmad/custom/standards/aws-terraform-implementation.md`: least privilege, separate role responsibilities, explicit retention/PITR/tags, stable addresses, no provisioners/null resources, no broad wildcard authority, and documented rollback.
- The Process Manager may read only verified configuration and write only the occurrence/processed-event ledger records for this Cell/job scope. It must not read or write the S3 CONFIG inbox, configuration registry writes, Scheduler, ECS, task roles, alert records, or commands.
- Production ledger changes require PITR/deletion protection and rollback that preserves occurrence/processed-event evidence. Routine rollback restores a compatible Cell Contract/runtime artifact; it does not destroy or edit ledger records.

### Previous Story Intelligence

- Story 1.6 completed the materializer and authenticated materializer-source normalization. Its explicit unresolved deferral is authoritative Scheduler/materializer conformance; do not silently claim this story closes that deferred comparison.
- Story 1.6 review exposed real risks around conditional monotonicity, exact KMS contexts, compatibility checks, canonical UTC timestamps, and focused tests. Preserve those review lessons for all new DynamoDB/IAM/runtime work.
- Full validation is credential-free and discovers Terraform roots dynamically. It validates configuration, not live AWS EventBridge, Lambda, SQS, DynamoDB, ECS, alarms, or notification delivery.

### Web-verified AWS Notes

- DynamoDB transactions and condition expressions must be used for the atomic processed-event/occurrence write and immutable-key conflict behavior. See [DynamoDB TransactWriteItems](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_TransactWriteItems.html) and [DynamoDB condition expressions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html).
- Lambda SQS partial-batch behavior requires `ReportBatchItemFailures`; an unhandled invocation exception makes the whole batch fail, while valid `itemIdentifier` values retry only selected records. See [Handling errors for an SQS event source in Lambda](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html).

### Project Structure Notes

- Expected updates: `runtime/process_manager/**`, `modules/ecs-scheduled-job-platform/{main.tf,variables.tf,outputs.tf,README.md,examples/basic/*}`, `contracts/**`, `tests/contract/**`, `docs/runbooks/README.md`, `fixtures/canary/README.md`, this story, and sprint status.
- Do not add a new Terraform module, environment root, remote-state link, queue family, GSI, alert ledger, or dependency unless a reviewed contract change proves it is required for this story.
- External Process Manager artifacts are immutable inputs. Terraform must consume the published artifact and never build a checkout ZIP or retain state, plans, credentials, or generated output.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-1.7-Record-Deterministic-Occurrence-State`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-5-to-AD-7`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-11-to-AD-14`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/solution-design-review.md#Runtime-Processing`]
- [Source: `_bmad-output/implementation-artifacts/1-6-materialize-future-expected-occurrences.md`]
- [Source: `contracts/v1/catalogs/reducer.json`]
- [Source: `contracts/v1/catalogs/keys-and-correlation.json`]
- [Source: `contracts/v1/schemas/occurrence-record.schema.json`]
- [Source: `contracts/v1/schemas/processed-event.schema.json`]
- [Source: `tests/contract/support/contracts.py#reduce_occurrence_state`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Ultimate context analysis completed from Epic 1, Story 1.7, PRD, Architecture Spine, solution design review, project context, AWS Terraform standard, completed Story 1.6, reducer contracts/fixtures, current Cell module, current Process Manager stub, recent commits, and current AWS DynamoDB/Lambda documentation.

### Completion Notes List

- Story context created from the first backlog item after Story 1.6.
- Story 1.6's explicit Scheduler/materializer conformance deferral is preserved as a cross-story constraint.

### File List

- `_bmad-output/implementation-artifacts/1-7-record-deterministic-occurrence-state.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `runtime/process_manager/**`
- `modules/ecs-scheduled-job-platform/{main.tf,variables.tf,outputs.tf,README.md,examples/basic/*}`
- `contracts/**`
- `tests/contract/**`
- `docs/runbooks/README.md`
- `fixtures/canary/README.md`
