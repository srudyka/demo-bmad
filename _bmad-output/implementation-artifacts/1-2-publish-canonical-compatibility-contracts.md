---
baseline_commit: 970a8d8cc8add345024109d289eab8d17549b08c
---

# Story 1.2: Publish Canonical Compatibility Contracts

Status: done

## Story

As a Platform Engineering contributor,
I want a versioned Compatibility Package for every Cell integration boundary,
so that independently implemented Terraform and runtime components cannot disagree on identity, schemas, state, IAM, or compatibility.

## Acceptance Criteria

1. **Given** the repository seed from Story 1.1
   **When** the Compatibility Package is published
   **Then** `contracts/` contains versioned JSON Schemas for the Cell Contract, CONFIG, authenticated evidence envelope, occurrence and task-attempt records, completion signal, command, alert, and Deployment Identity
   **And** the package's strict parser, semantic checks, and schemas together reject missing required fields, unsupported majors, malformed identifiers, noncanonical timestamps, duplicate JSON keys, non-finite numbers, and fields or values capable of carrying plaintext secrets.

2. **Given** the `occurrence/v1` identity contract
   **When** identity vectors are evaluated
   **Then** fixtures define the exact UTF-8 bytes and lowercase SHA-256 result for canonical job ID, schedule generation, and Unix epoch minute
   **And** they cover valid adjacent occurrences, invalid job IDs, Unicode/byte-normalization differences, daylight-saving boundaries, and mismatched hashes.

3. **Given** evidence can arrive duplicated, delayed, or out of order
   **When** reducer fixtures execute
   **Then** every bounded permutation of the same immutable, deduplicated evidence converges on the documented `EXPECTED`, `STARTED`, `SUCCEEDED`, `FAILED`, `OVERDUE`, `MISSED`, or `AMBIGUOUS` result
   **And** no late, duplicate, wrong-occurrence, or conflicting signal silently overwrites a terminal result.

4. **Given** the materializer and EventBridge Scheduler must interpret one recurring schedule contract
   **When** schedule fixtures are evaluated
   **Then** they define the supported cron/rate grammar, IANA time zones, explicit start anchors, activation windows, disabled flexible windows, daylight-saving behavior, generation hashing, and consecutive-window expectations
   **And** one-time schedules, unsupported syntax, ambiguous anchors, invalid time zones, and divergent occurrence calculations fail deterministically.

5. **Given** Cell and job roots have separate owners and IAM boundaries
   **When** the integration and IAM catalogs are reviewed
   **Then** every cross-root ARN, resource-policy principal, evidence type, role assumption, `RunTask`, `PassRole`, queue, CONFIG, metric, alert, and lifecycle handoff has one owner and explicit allowed authority
   **And** named positive and negative fixtures cover source-account/source-ARN confused-deputy conditions, cross-producer forgery, cross-job access, stale roles, boundary removal, and unrelated role passing.

6. **Given** SQS and Lambda integrations must remain safe under retry
   **When** runtime constraint fixtures are evaluated
   **Then** they validate message size, batch size, function timeout, batch window, queue visibility, concurrency, `maxReceiveCount >= 5`, 14-day retention, partial-batch failure behavior, DLQ handling, and bounded retry rules
   **And** invalid or unbounded combinations fail before deployment.

7. **Given** Cell and consumer versions evolve independently
   **When** compatibility validation runs
   **Then** the package declares supported Cell, module, CONFIG, evidence, runtime, workflow, Terraform, AWS provider, and Python ranges for the current and previous major through the required replay and rollback horizon, with an explicit `previous_major = null` exception for the first major release
   **And** unsupported or unknown major combinations fail with an actionable migration reference.

8. **Given** a contract, catalog, or fixture changes
   **When** credential-free repository validation runs
   **Then** schema tests, canonicalization and identity vectors, schedule fixtures, reducer permutations, IAM cases, queue constraints, ownership checks, and compatibility matrices execute from the same checked-in package
   **And** breaking changes require a major-version classification and migration note without schema-network retrieval, AWS credentials, account-specific deployment values, or plaintext secrets.

9. **Given** this story publishes contracts rather than infrastructure
   **When** the implementation and documentation are reviewed
   **Then** both Terraform modules remain resource-free, all examples still validate independently, and no real or account-specific deployment ID, Region, ARN, Environment, credential, state, plan, or secret value is hardcoded or generated; unmistakably fake structural sentinels are permitted only in isolated fixtures
   **And** the package documents versioning, consumer use, validation, security assumptions, migration classification, and repository-only rollback.

## Tasks / Subtasks

**Development entry gate:** Before editing implementation files, identify a reviewed commit that contains the completed Story 1.1 implementation and record it as this story's review baseline. If the current dirty Story 1.1 work is not committed, stop and establish that baseline first; do not mix prerequisite and Story 1.2 changes into one unattributable review diff.

- [x] 1. Establish the versioned Compatibility Package layout and manifest (AC: 1, 7, 8, 9)
  - [x] Replace the placeholder `contracts/README.md` with the normative package contract, consumer workflow, versioning policy, validation command, security rules, migration rules, and rollback guidance.
  - [x] Create `contracts/manifest.json` for package version `1.0.0`, predecessor release (`null` for the initial release), schema dialect, canonicalization profile, current major, initial-release/previous-major state, supported tool/component ranges, minimum replay/rollback horizon, and relative paths to every schema, catalog, fixture suite, and migration note.
  - [x] Use immutable versioned paths under `contracts/v1/`; do not use mutable `latest` aliases or remote `$ref` targets.
  - [x] Add `contracts/migrations/v1.0.0.md` as the initial-release compatibility note and define the Patch/Minor/Major classification rules used by tests.
  - [x] Define artifact checksums as SHA-256 of exact checked-in UTF-8 bytes after enforcing LF line endings and exactly one final newline; reserve RFC 8785 for semantic hashed JSON bodies. Add a package inventory test that validates the manifest itself and fails for a missing, duplicate, unreferenced, path-escaping, or checksum-mismatched referenced artifact. Do not create a circular self-checksum for `manifest.json`.
  - [x] Seed an immutable release index/snapshot for `1.0.0` and a semantic-diff classifier with Patch/Minor/Major positive and negative fixtures. Initial release explicitly has no predecessor; later validation must compare with the checked-in predecessor snapshot and reject breaking change, version bump, or migration-note disagreement.

- [x] 2. Publish the nine required JSON Schemas and strict parsing profile (AC: 1, 8)
  - [x] Create Draft 2020-12 schemas for `cell-contract`, `config`, `evidence-envelope`, `occurrence-record`, `task-attempt-record`, `completion-signal`, `command`, `alert`, and `deployment-identity` under `contracts/v1/schemas/`.
  - [x] Give every schema an exact `https://json-schema.org/draft/2020-12/schema` declaration, immutable package-local `$id`, explicit major-bearing `schema_version`, required fields, identifier patterns, numeric bounds, and defined additive-field behavior.
  - [x] Freeze version syntax: `package_version`, `contract_version`, and every `schema_version` are canonical SemVer strings such as `1.0.0`; `config_version` and `schedule_generation` are 64-character lowercase SHA-256 values; identity algorithms are literals such as `occurrence/v1`; and each canonical `event_type` ends in `.v<schema major>`. Reject leading `v` on SemVer fields and reject a schema/event-type major mismatch.
  - [x] Parse JSON before schema validation with duplicate-key rejection, UTF-8 enforcement, and rejection of `NaN`, infinities, and invalid Unicode; validate all `$ref` values from an explicit local registry with network retrieval disabled.
  - [x] Enforce canonical timestamps as uppercase UTC `Z` with exactly three fractional digits (`YYYY-MM-DDTHH:MM:SS.sssZ`). Upstream AWS timestamps are normalized to this form before canonical validation; offsets, lowercase `z`, missing milliseconds, and excess precision are invalid canonical wire values.
  - [x] Keep security-sensitive typed objects and payloads closed. Every event type maps in the manifest to a closed versioned payload schema under `contracts/v1/schemas/payloads/` (or a named `$defs` entry with an immutable `$id`). The evidence envelope may retain architecture-required additive compatibility only after recursive sensitive-name/secret-shape validation and projection of known fields; unknown fields never become authority or persisted canonical state.
  - [x] Publish a versioned secret-safety catalog that defines forbidden field names/value shapes and the explicit approved Secrets Manager/SSM/approved-platform reference union. Approved references contain identifiers only, never secret values, and are validated before general secret-shape rules.
  - [x] Add positive and negative instances for every required field, unsupported major, malformed job/occurrence/config/UUID identifier, timestamp form, duplicate key, non-finite number, plaintext secret field/value, allowed secret reference, and disallowed unknown payload field. Store lexically invalid or non-UTF-8 inputs as base64-encoded raw bytes plus exact expected parser error so the fixture wrapper remains valid JSON.

- [x] 3. Define canonical JSON, CONFIG hashing, and occurrence identity (AC: 1, 2, 8)
  - [x] Adopt RFC 8785 JSON Canonicalization Scheme (JCS) and lowercase SHA-256 for semantic JSON hashes such as CONFIG and schedule generation; artifact-integrity digests follow Task 1's raw-byte rule. Reject floats and integers outside the interoperable IEEE-754 safe-integer range in semantic hashed bodies; require NFC strings and publish cross-language-sensitive vectors.
  - [x] Define CONFIG as a versioned wrapper whose `config_version` is SHA-256 over the RFC 8785 bytes of the secret-free `config` body only, avoiding a circular self-hash. Include immutable schedule generation, full task-definition revision ARN, cluster/network/role/runtime/log/notification references, approved secret references, and Deployment Identity reference.
  - [x] Implement the exact occurrence bytes `occurrence/v1\n<job_id>\n<schedule_generation>\n<epoch_minute>` with no trailing newline and hash those UTF-8 bytes to 64 lowercase hex characters.
  - [x] Enforce job IDs as three lowercase slash-separated segments matching `[a-z0-9][a-z0-9-]{0,62}` and epoch minute as canonical base-10 with no sign, whitespace, decimal, or leading zero except `0`.
  - [x] Add exact byte and digest vectors for ASCII, adjacent minutes, Unicode normalization rejection, CRLF/trailing-newline differences, DST transitions, malformed components, and asserted-hash mismatch.
  - [x] Do not assume Terraform `jsonencode` is JCS-equivalent. Fixtures must expose characters and numeric cases that could diverge so future Terraform consumers must prove byte compatibility rather than reimplement a look-alike hash.

- [x] 4. Freeze the recurring schedule and generation contract (AC: 2, 4, 8)
  - [x] Define `schedule/v1` as one normalized expression, IANA time-zone name, explicit canonical start anchor, inclusive activation start, optional exclusive activation end, `flexible_time_window = "OFF"`, evaluator version, and pinned tzdb release.
  - [x] Set the MVP cron subset to daily `cron(M H * * ? *)`, weekly `cron(M H ? * DOW *)`, and monthly `cron(M H DOM * ? *)`, where `M=0..59`, `H=0..23`, `DOM=1..31`, `DOW=SUN..SAT`, month is `*`, and year is `*`. Reject lists, ranges, steps, `L`, `W`, `#`, wildcard minute/hour, explicit month/year, multiple weekdays/days, and alternate whitespace/case.
  - [x] Support canonical `rate(N minute[s]|hour[s]|day[s])` with a positive integer, no leading zero, singular only for `N=1`, plural otherwise, and an explicit start anchor. Rate days are fixed 24-hour intervals.
  - [x] Reject `at(...)`, aliases, empty/open-ended ambiguous anchors, activation end not after start, flexible windows other than `OFF`, and time zones unavailable in the pinned tzdb.
  - [x] Define `schedule_generation` as lowercase SHA-256 of `schedule/v1\n` followed by RFC 8785 bytes of the normalized generation body. Include evaluator and tzdb versions so a change that alters occurrence calculation creates a new generation.
  - [x] Pin `tzdata==2026.2`, record its bundled IANA release (2026b), and force conformance tests to use the wheel rather than the host TZPATH (for example, an empty/reset `zoneinfo` search path with package fallback). Assert the loaded package/release before evaluating ordinary dates, consecutive windows, spring-forward skipped cron time, fall-back repeated local time occurring once, month-end invalid dates, rate-across-DST, activation boundaries, and generation mismatches.
  - [x] Implement only a bounded offline conformance evaluator for fixtures. Do not add a generic cron library or production materializer behavior in this story.

- [x] 5. Publish deterministic reducer and correlation fixtures (AC: 1, 3, 8)
  - [x] Define canonical event types, payload schemas, deduplication key `(producer_id, producer_event_id)`, occurrence/attempt/processed-event ledger keys, and task tag/environment/correlation assertions in versioned catalogs.
  - [x] Define occurrence and attempt record fields for job/config/schedule identity, state, expected/started/completed timestamps, exit code, optional operator-safe error reason, attempt zero, deterministic client token, launch-pending state, first-request time, safe-retry deadline, task ARN, correlation/conflict data, and immutable accepted evidence.
  - [x] Add an auxiliary processed-event ledger schema for registered producer plus producer-event deduplication identity, canonical event checksum, acceptance/rejection result, occurrence binding, and immutable processing metadata. This supplements the nine required boundary schemas; it does not add a runtime writer.
  - [x] Define completion as one structured marker tied to job, occurrence, config, attempt, and task assertions. `SUCCEEDED` requires exactly one accepted marker and zero essential-container exit; either signal alone is insufficient.
  - [x] Create bounded evidence sets for every canonical state and execute every ordering of each set after immutable deduplication. Cap individual fixture sets explicitly so exhaustive permutations remain fast and deterministic.
  - [x] Cover identical duplicates, same dedup key with conflicting body, delayed evidence, orphan ECS/log evidence, missing expectation repair, wrong occurrence/config/task assertions, non-zero exit, start/RunTask failure, deadline before/after start, conflicting task ARNs, duplicate completion, late consistent evidence, and late conflicting terminal evidence.
  - [x] Prove that accepted immutable evidence commutes, terminal truth is not silently replaced, conflicts resolve to `AMBIGUOUS`, and rejected unauthenticated/wrong-occurrence evidence never enters reduction.

- [x] 6. Publish ownership, producer, IAM, metric, and alert catalogs (AC: 1, 5, 8)
  - [x] Catalog every Cell-root and job-root resource/integration edge with exactly one Terraform owner, lifecycle owner, producer, consumer, evidence type, ARN shape, and compatibility version.
  - [x] Catalog the distinct Scheduler delivery, materializer, normalizer, Process Manager, log ingestor, deadline scanner, alert router, command handler, lifecycle/garbage-collection, operator, break-glass, job launch, execution, task, plan, and apply roles with allowed trust, action, resource, and condition boundaries. No catalog entry may use an unexplained `Action="*"` or `Resource="*"`.
  - [x] Require Scheduler confused-deputy conditions for exact `aws:SourceAccount` and schedule-group `aws:SourceArn`; require job-scoped `iam:PassRole` plus `iam:PassedToService=ecs-tasks.amazonaws.com`; require the Process Manager to assume only approved boundary-constrained launch roles.
  - [x] Define producer authority from non-body metadata, including Scheduler queue `SenderId` immutable IAM `RoleId` prefix, ECS source/resource/task ARN, CloudWatch log group/stream, registry CONFIG, deadline key, and authorized command record. Payload coordinates are assertions only.
  - [x] Define raw AWS producer-shape fixtures separately from canonical evidence. ECS fixtures require the authoritative EventBridge/ECS task-state subset while allowing additive AWS-managed fields; Scheduler fixtures derive occurrence time from `<aws.scheduler.scheduled-time>`. Conditional stop fields and new AWS system attributes must not be mistaken for identity.
  - [x] Publish exact GitHub OIDC `aud` and custom `sub` template/rendering fixtures for immutable repository identity, deployment Environment, and pinned `job_workflow_ref`. Include wrong repository, Environment, workflow ref, audience, branch-only subject, and mutable workflow negative cases without adding OIDC privileges to Story 1.1 CI.
  - [x] Define bounded metric dimensions (`job_id`, `environment`, `state`; never occurrence ID), alarm names/dimensions/missing-data/threshold/ownership semantics, and alert/outbox fields including Environment, detection time, failure plane, Deployment Identity, account/Region, notification target reference, and Runbook context.
  - [x] Publish the registration and enablement lifecycle contract for `RESERVED`, `PUBLISHED`, `VALIDATED`, `MATERIALIZED`, `ENABLED`, and `REJECTED`, including acknowledgement bindings to role/schedule identity, owner generation, CONFIG hash, contract versions, horizon watermark, legal transitions, rejection reasons, timeout behavior, and the two-phase enablement guard. Add transition and stale/mismatched acknowledgement fixtures without implementing the Registrar or job resources.
  - [x] Add named positive and negative fixtures for exact and stale principals, wrong source account/group ARN, producer/event-type forgery, cross-job access, stale ownership generation, boundary omission/removal, unrelated role passing, arbitrary log/task assertions, and unauthorized lifecycle handoff.

- [x] 7. Freeze queue/Lambda and ECS retry constraints (AC: 5, 6, 8)
  - [x] Publish AWS service maxima separately from stricter MVP platform limits. Record SQS message maximum 1 MiB but cap the MVP canonical message body at 256 KiB and SQS event-source batch size at 10 so the 6 MiB Lambda synchronous payload ceiling retains metadata headroom.
  - [x] Validate Lambda timeout `1..900` seconds, batch window `0..300` seconds, standard-queue batch size `1..10`, queue visibility `>= 6 * function_timeout + batch_window` and `<= 43200` seconds, and maximum concurrency `2..1000` that does not exceed declared reserved concurrency across mappings.
  - [x] Require encrypted standard queues, 14-day source/DLQ retention, redrive with `maxReceiveCount` in `5..1000`, a configured DLQ, `ReportBatchItemFailures`, failed `messageId` responses, and a finite application retry/redrive horizon. Reject provisioned poller mode in MVP.
  - [x] Define ECS `RunTask` client tokens as at most 64 printable ASCII characters, identical-parameter reuse within one cluster, HTTP-success `failures[]` handling, attempt zero reuse, and a conservative safe-retry deadline no later than one hour after the first request. No later retry is allowed unless the original task is authoritatively recovered.
  - [x] Add boundary-value and invalid-combination fixtures, including whole-batch exception behavior, partial failures, poison message redrive, visibility overflow, concurrency oversubscription, missing DLQ, retention drift, and retry after the safe deadline.

- [x] 8. Publish compatibility, migration, and command contracts (AC: 1, 7, 8)
  - [x] Use SemVer 2.0.0 and `semantic-version` SimpleSpec range semantics. Reject prerelease/build versions unless a fixture explicitly opts into them; do not substitute PEP 440 ranges.
  - [x] Make `1.0.0` an honest initial release with `current_major=1`, `previous_major=null`, and `initial_release=true`; encode the future invariant that releases support N and N-1 through at least 14 days and longer while referenced by CONFIG, occurrences, queues, DLQs, investigation, or rollback.
  - [x] Declare current component ranges for Cell, both modules, CONFIG, evidence, each runtime producer/consumer, workflow, Terraform `>=1.10.0,<2.0.0`, AWS provider `>=6.0.0,<7.0.0`, and Python `>=3.14.0,<3.15.0`.
  - [x] Add valid, unsupported-major, unknown-component, range-boundary, prerelease, rollback, replay, and missing-migration fixtures. Every rejection returns a stable machine code and relative migration reference.
  - [x] Separate the operator request from the Cell-stamped canonical command. The request identifies a job and scheduled time/approved lookup selector but rejects caller-supplied occurrence ID, command ID, producer identity, or evidence; the trusted handler resolves the original occurrence and creates the canonical record.
  - [x] Define handler-generated lowercase canonical UUIDv7 command IDs and exact manual bytes `occurrence/manual/v1\n<job_id>\n<original_occurrence_id>\n<config_version>\n<command_id>` with no trailing newline. The canonical command requires actor, approval, reason, resolved original occurrence, config version, Deployment Identity, verification, and compensation.

- [x] 9. Integrate exact, credential-free validation and documentation (AC: 1-9)
  - [x] Promote contract-critical packages to exact direct development dependencies: `jsonschema==4.26.0`, `referencing==0.37.0`, `rfc8785==0.1.4`, `semantic-version==2.10.0`, and `tzdata==2026.2`; regenerate and review `uv.lock` with no unrelated dependency churn.
  - [x] Put reusable conformance helpers under `tests/contract/support/` or another explicitly linted and typed test-tooling boundary. Extend the existing Ruff/mypy/pytest paths rather than creating an unvalidated script island.
  - [x] Extend `tests/contract/` so the existing `./scripts/validate.sh` runs every package check from checked-in artifacts, never downloads schemas, opens sockets, reads AWS credentials, or depends on deployment-specific environment values.
  - [x] Preserve `scripts/validate.py` credential scrubbing, dynamic Terraform-root discovery, precise stage labels, temporary data directories, lock-readonly behavior, artifact cleanliness, and the single local/CI entry point.
  - [x] Update the root `README.md` layout/toolchain/validation/rollback sections without removing the BMad customization or bootstrap security boundary. Do not modify Terraform resources, runtime production packages, GitHub workflow privileges, architecture/PRD artifacts, or protected-state behavior.
  - [x] Run the full documented validation with AWS credential/profile/web-identity variables unset; prove both modules and both examples remain resource-free and valid, all contract suites pass, locks remain stable after validation, and no generated artifact remains.

## Dev Notes

### Developer Context

Story 1.2 turns the Story 1.1 `contracts/` placeholder into the normative, language-neutral Compatibility Package required before any Cell resource or runtime behavior is implemented. Later stories must consume these artifacts rather than inventing schemas, hashes, IAM edges, schedule semantics, or reducer transitions independently.

This story is deliberately contract-only. It may add offline conformance tooling and fixtures, but it must not create AWS resources, implement production Lambda handlers, implement the production materializer/reducer, deploy schedules/queues/tables, add privileged CI, or register the pilot canary. Story 1.3 begins AWS foundations; Stories 1.5 through 1.11 implement evidence, materialization, state, launch, completion, deadlines, and alerts.

The binding architecture uses brokered Scheduler-to-queue evidence and Process Manager `RunTask`; it supersedes older PRD language that suggested direct Scheduler-to-ECS. DLQs are required by the adopted architecture even though the early product notes called them optional. Treat the architecture spine as source of truth.

Traceability: FR17, FR24, FR25, and FR26; NFR9, NFR10, NFR12, and NFR13; AR4, AR5, AR15, AR17, AR22, AR23, and AR42.

### Contract Decisions

- JSON Schema dialect is Draft 2020-12. `$ref` resolution is package-local and offline.
- Package release is `1.0.0`; schema and identity major is `v1`. Initial release has no fictional previous major.
- Canonical hashed JSON uses RFC 8785 JCS plus the restricted interoperable data profile in Task 3.
- Canonical wire timestamps use UTC `Z` and exactly milliseconds. Occurrence identity still uses integer Unix epoch minute exactly as AD-4 defines.
- Schedule fixtures use pinned IANA data, a deliberately small EventBridge Scheduler grammar, and no generic cron evaluator.
- The platform limit is stricter than the current AWS SQS 1 MiB limit: canonical evidence remains at most 256 KiB and MVP event-source batches remain at most 10.
- SemVer ranges use `semantic-version` SimpleSpec, not PEP 440.
- Unknown envelope additions are never authority. Typed payloads are closed; additive metadata is screened for secret-bearing names/shapes and ignored or projected before canonical persistence.

### Required Schema Content

- **Cell Contract:** semantic version; Cell/account/Region/Environment identity; exact integration ARNs; metric namespace; KMS reference; supported schema/CONFIG/component ranges; checksum; discovery path metadata.
- **CONFIG:** job identity; ownership generation; schedule contract/generation; completion window; full task-definition revision ARN; cluster, subnet, security-group, role, runtime, log, notification, approved secret-reference, and Deployment Identity fields; canonical body/config hash.
- **Evidence envelope:** `producer_id`, `producer_event_id`, `event_type`, `schema_version`, `job_id`, `config_version`, `schedule_generation`, `scheduled_time`, `occurrence_id`, `emitted_at`, and typed `payload`.
- **Occurrence record:** job/config/generation/occurrence identity, canonical expected/started/completed/deadline timestamps, state, exit code, optional operator-safe error reason, immutable evidence references, and package-owned ledger keys.
- **Task attempt:** `attempt_no=0`, deterministic client token, config version, launch pending, first request, retry deadline, task ARN, correlation, conflict, and recovery fields.
- **Completion:** structured marker and asserted job/occurrence/config/attempt/task coordinates, completion time, status, exit code, and optional operator-safe error reason.
- **Command:** separate caller-request and Cell-stamped forms; handler-generated canonical UUIDv7 command ID, actor/approval/reason, resolved original occurrence, config, Deployment Identity, verification, compensation, and architecture-owned manual identity.
- **Alert:** job/occurrence/state/failure plane, Environment, detection time, account/Region, Deployment Identity, notification target reference, Runbook context, and outbox/deduplication identity.
- **Deployment Identity:** target account/Region/Environment, immutable source commit, image digest, full ECS task-definition revision, module/workflow/contract/tool versions, workflow run identity, resolved managed-runtime/platform versions, and checksums.

### Architecture Compliance

- `contracts/` is normative and versioned with the Cell. Every later module, runtime package, workflow, and operational projection consumes the same package and rejects disagreement before side effects.
- Job ID, occurrence bytes, event names, registry keys, ledger keys, time form, structured logging fields, bounded metric dimensions, CONFIG publication path, stable error form, and secret-reference-only configuration follow the spine's consistency conventions.
- Producer identity and job authority come from registered non-body AWS metadata. Payload IDs are assertions only. Catalog fixtures must make forgery and stale authority fail closed.
- The Process Manager is the only future occurrence-state writer. Offline reducer tooling demonstrates the transition contract but is not a second runtime implementation.
- Completion is occurrence-aware. A success string alone is never sufficient; success binds one marker and zero essential-container exit to attempt zero and the authoritative task mapping.
- Metrics never use occurrence ID as a dimension. Alerts do include occurrence and Deployment Identity context.
- Configuration and fixtures must be secret-free. Only approved secret references may appear; neither secret values nor fake realistic credentials belong in schemas/examples.

### Existing Files To Update And Preserve

- `contracts/README.md`: currently a four-line placeholder naming this story as owner. Replace it with package consumer and maintainer documentation.
- `pyproject.toml`: currently pins Checkov, mypy, pytest, and Ruff under Python 3.14. Add the five direct contract dependencies exactly and keep the current runtime/test discovery settings unless deliberately extended.
- `uv.lock`: currently contains some required libraries only transitively through Checkov. Regenerate after direct promotion; review the entire diff and retain exact reproducibility.
- `scripts/validate.py`: currently scrubs AWS and tool override variables, discovers all Terraform roots dynamically, validates with temporary data directories, runs one shared test stage, and checks checkout cleanliness. Preserve those behaviors; extend only validation paths/stages needed for typed contract tooling.
- `README.md`: preserve the BMad customization section, Story 1.1 bootstrap contract, credential-free security boundary, and single validation command. Update layout, tested dependencies, contract use, and rollback wording.
- `tests/contract/test_repository_structure.py`: currently asserts the placeholder boundary. Extend it for the versioned package inventory without weakening resource-free Terraform assertions.
- `tests/contract/test_documentation.py`: currently protects root/module/Runbook documentation. Extend it for Compatibility Package documentation without removing existing assertions.

### File Structure Requirements

```text
contracts/
  README.md
  manifest.json
  releases/
    1.0.0.json               # immutable release checksum/classification snapshot
  migrations/
    v1.0.0.md
  v1/
    schemas/                  # nine required boundary schemas plus auxiliary records/payloads
      payloads/
    catalogs/
      producers.json
      event-types.json
      keys-and-correlation.json
      ownership.json
      iam.json
      lifecycle.json
      oidc.json
      metrics-alerts.json
      secret-safety.json
      queue-lambda-constraints.json
      compatibility.json
    fixtures/
      schemas/
      canonical-json/
      identity/
      schedules/
      reducer/
      iam/
      lifecycle/
      oidc/
      queue-lambda/
      compatibility/
tests/contract/
  support/                    # offline typed conformance helpers
  test_contract_manifest.py
  test_contract_schemas.py
  test_contract_identity.py
  test_contract_schedules.py
  test_contract_reducer.py
  test_contract_iam.py
  test_contract_lifecycle.py
  test_contract_oidc.py
  test_contract_queue_lambda.py
  test_contract_compatibility.py
```

Names may be split into smaller files, but the versioned ownership boundary and coverage must remain obvious. Do not place executable production code under `contracts/`, duplicate normative constants in tests, or hide fixture data in Python literals when consumers need language-neutral JSON.

### Testing Requirements

- Validate each schema document with `Draft202012Validator.check_schema()` and validate instances using an explicit local `referencing.Registry`; remote retrieval is a test failure.
- Do not rely on JSON Schema `format` alone. Use exact regex and semantic round-trip checks for canonical timestamps, UUIDv7, time-zone names, hashes, ARNs, and schedule fields.
- Load JSON with strict hooks so duplicate keys and non-finite values fail before schema validation.
- Read expected bytes/digests/results from fixtures. Tests must not calculate both the input and expected answer with the same helper and then call that independent proof.
- Execute all permutations declared by each bounded reducer fixture and verify deduplication, convergence, terminal conflict, and rejection behavior.
- Freeze schedule results to the pinned tzdb. A tzdb update requires reviewed fixture diffs and a schedule-generation compatibility decision.
- Add positive and negative tests for every IAM authority edge and numeric queue boundary, including one-below/at/one-above values.
- Prove no fixture contains credential-shaped or plaintext-secret data. Use unmistakably fake non-secret sentinel references where a reference shape is required.
- Run `./scripts/validate.sh` and `terraform fmt -check -recursive`. Both module and example `terraform validate` checks remain mandatory even though this story changes no Terraform configuration.

### Library And API Notes (Verified 2026-07-15)

- JSON Schema Draft 2020-12 is the current published dialect. Python `jsonschema` does not retrieve referenced schemas automatically in the desired secure way; construct an explicit local registry.
- `format` is annotation-only unless explicitly checked, and optional dependencies can make a checker silently accept a format. Canonical timestamps and UUIDv7 therefore need contract-specific validation.
- RFC 8785 defines deterministic canonical JSON but does not normalize Unicode. The package must reject non-NFC strings before JCS and publish exact UTF-8 vectors.
- EventBridge Scheduler has 60-second precision. For cron schedules, a nonexistent DST local time is skipped and a repeated fall-back local time runs once; rate days are fixed 24-hour intervals.
- Current AWS SQS maximum message size is 1 MiB, retention is at most 14 days, and visibility is at most 12 hours. Lambda SQS event-source payloads remain limited to 6 MiB.
- Lambda SQS mappings support `ReportBatchItemFailures`; an uncaught handler exception fails the whole batch. Maximum-concurrency configuration is `2..1000` and must remain within reserved concurrency.
- Scheduler confused-deputy protection uses both source account and the schedule-group ARN. `iam:PassRole` is same-account/resource-scoped and should constrain `iam:PassedToService` to ECS tasks.
- ECS `RunTask` may return `failures[]` in a successful HTTP response. Its client token is at most 64 printable ASCII characters and is idempotent only for identical parameters in the same cluster.
- RFC 9562 defines UUIDv7, and Python 3.14 supplies `uuid.uuid7()`. Validate version, RFC variant, lowercase canonical representation, and timestamp plausibility.

### Previous Story And Git Intelligence

- Story 1.1 established the resource-free module skeletons, seven typed runtime boundaries, one credential-free `./scripts/validate.sh`, dynamic Terraform-root discovery, exact Python/tool pins, local provider locks, security scanning, hygiene checks, and read-only pull-request CI. Extend these conventions; do not replace or privilege them.
- Story 1.1 review fixed ambient tool-variable injection, hard-coded Terraform roots, unsafe scanner fixture exemptions, incomplete mutable-reference scanning, and weak checkout-artifact detection. New contract validation must preserve those corrections and must not add broad fixture exemptions.
- At story creation time, Story 1.1 implementation changes are present in the working tree but not represented by the current `HEAD` commit. Before developing Story 1.2, create or identify a reviewed Story 1.1 baseline commit. Otherwise Story 1.2 review cannot distinguish prerequisite files from new contract work.
- `uv.lock` was excluded from the prior code-review chunk even though locked validation passed. Treat the Story 1.2 regenerated lock as a separately reviewable dependency artifact and inspect both direct and transitive changes.

### Review Findings

- [x] [Review][Patch] Enforce secret-safety screening before accepting additive evidence-envelope extensions; `x-*` fields currently bypass the required recursive checks. [tests/contract/support/contracts.py:141]
- [x] [Review][Patch] Bind CONFIG identity to its RFC 8785 body and use the one normalized `schedule/v1` contract, including verified schedule generation and real timestamp semantics. [tests/contract/support/contracts.py:141]
- [x] [Review][Patch] Validate registered producer authority values, not merely producer/event names or the presence of ECS metadata keys. [tests/contract/support/contracts.py:610]
- [x] [Review][Patch] Drive IAM authority conformance from the IAM catalog and test all trust, action, resource, and condition boundaries rather than hard-coded fixture values. [tests/contract/support/contracts.py:576]
- [x] [Review][Patch] Recompute and verify the canonical command's `synthetic_occurrence_id` from the required `occurrence/manual/v1` bytes. [contracts/v1/schemas/command.schema.json:100]
- [x] [Review][Patch] Enforce release-to-predecessor semantic comparison, semver classification, and migration agreement; the current classifier and snapshot cannot detect future breaking releases. [tests/contract/support/contracts.py:263]
- [x] [Review][Patch] Reject overflowing JSON numeric exponents that Python parses as non-finite floats. [tests/contract/support/contracts.py:95]
- [x] [Review][Patch] Apply canonical timestamp semantic validation to every timestamp field, including CONFIG schedule anchors and activation windows. [tests/contract/support/contracts.py:155]
- [x] [Review][Patch] Validate all operator-request field semantics in the public request validator or compose schema validation into that boundary. [tests/contract/support/contracts.py:744]
- [x] [Review][Patch] Bound ECS safe-retry deadlines and elapsed time at zero as well as the one-hour maximum. [tests/contract/support/contracts.py:707]
- [x] [Review][Patch] Extend manifest coverage so a future versioned contract tree cannot bypass the unreferenced-artifact checksum guard. [tests/contract/support/contracts.py:224]
- [x] [Review][Patch] Honor explicit fixture opt-in for SemVer build metadata or remove that unsupported opt-in contract. [tests/contract/support/contracts.py:716]

### Scope Boundaries

Do not implement or deploy:

- AWS resources or Terraform resource/data/backend blocks
- Production schedule evaluation, occurrence materialization, reducer, normalizer, deadline scanner, alert router, or command handler
- DynamoDB tables/items, S3 CONFIG publication, queues/DLQs, EventBridge schedules/rules, Lambda mappings/functions, ECS tasks, alarms, or IAM roles/policies
- GitHub OIDC/IAM deployment or privileged use, protected deployment Environments, plan/apply workflows, AWS credentials, remote state, or production approvals; OIDC claim templates and fixtures required by the Compatibility Package remain in scope
- A UI, dashboard, migration of existing jobs, enforced task cancellation, Step Functions, cross-Region failover, or automatic remediation

### Project Structure Notes

- No UX artifact applies. The developer experience is a versioned package with clear paths, exact fixtures, actionable failures, and one documented validation command.
- Keep contract data in JSON/Markdown so Terraform, Python, workflows, and reviewers can consume it. Python code is conformance tooling, not the source of truth.
- Do not edit `_bmad/`, `.agents/`, PRD, architecture, epic, or readiness artifacts during implementation. Only this story file and sprint status are planning-tracking changes.
- If an implementation choice conflicts with the architecture spine, stop and document an architecture deviation rather than silently changing the contract.

### Rollback Notes

This story creates no AWS resources, state, plan, deployment artifact, or credential. Rollback is a repository revert of the Story 1.2 schemas, catalogs, fixtures, conformance tests, direct dependency declarations/lock changes, and documentation updates, followed by `./scripts/validate.sh`. Do not run `terraform destroy`, mutate a backend, remove a previous compatible contract still referenced by a queue/DLQ/CONFIG/occurrence, or perform any AWS action.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-12-Publish-Canonical-Compatibility-Contracts`]
- [Source: `_bmad-output/planning-artifacts/epics.md#Story-Traceability-Matrix`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-3-Independent-Expectation-and-Launch-Clocks`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-4-Stable-Occurrence-Identity`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-5-Versioned-Event-and-Configuration-Contracts`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-7-Occurrence-State-Machine`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-11-At-least-once-Ingress-and-Replay`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-12-Explicit-IAM-Boundaries`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-14-Bounded-Metrics-and-Enriched-Alerts`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-23-Checked-in-Compatibility-Package`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-25-Single-Terraform-Owner-per-Integration-Edge`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-27-Authenticated-Evidence-and-Command-Ingress`]
- [Source: `_bmad-output/project-context.md#Terraform-Rules`]
- [Source: `_bmad-output/project-context.md#Security-and-IAM-Rules`]
- [Source: `_bmad-output/project-context.md#Observability-Rules`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md#Security-And-Identity`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md#Testing-And-Validation`]
- [JSON Schema: Draft 2020-12](https://json-schema.org/draft/2020-12)
- [Python jsonschema 4.26](https://python-jsonschema.readthedocs.io/en/v4.26.0/)
- [RFC 8785: JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785.html)
- [RFC 9562: UUIDs](https://www.rfc-editor.org/rfc/rfc9562.html)
- [AWS: EventBridge Scheduler schedule types](https://docs.aws.amazon.com/scheduler/latest/UserGuide/schedule-types.html)
- [AWS: Scheduler context attributes](https://docs.aws.amazon.com/scheduler/latest/UserGuide/managing-schedule-context-attributes.html)
- [AWS: SQS quotas](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/quotas-messages.html)
- [AWS: Lambda SQS configuration](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-configure.html)
- [AWS: Lambda partial batch responses](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html)
- [AWS: Scheduler confused-deputy prevention](https://docs.aws.amazon.com/scheduler/latest/UserGuide/cross-service-confused-deputy-prevention.html)
- [AWS: IAM PassRole](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_passrole.html)
- [AWS: ECS RunTask idempotency](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_Idempotency.html)
- [Python: zoneinfo](https://docs.python.org/3.14/library/zoneinfo.html)
- [Semantic Versioning 2.0.0](https://semver.org/)

## Dev Agent Record

### Agent Model Used

OpenAI Codex (GPT-5)

### Debug Log References

- RED Task 1: `test_contract_manifest.py` failed because the package support boundary did not exist.
- GREEN Task 1: manifest, release, migration, checksum inventory, and semantic-classification tests passed (6 tests); full regression passed (36 tests, 136 subtests).
- RED Task 2: schema tests failed on missing local-registry and strict-parser APIs.
- GREEN Task 2: 18 schemas and strict parser/semantic/secret fixtures passed (13 focused tests); full regression passed (43 tests, 136 subtests).
- RED Task 3: identity tests failed on missing RFC 8785 and occurrence helper APIs.
- GREEN Task 3: canonical JSON/CONFIG and exact occurrence vectors passed (12 focused tests); full regression passed (48 tests, 137 subtests).
- RED Task 4: schedule tests failed on missing bounded evaluator and generation APIs.
- GREEN Task 4: schedule grammar, generation, activation, tzdb, DST, rate, and invalid-date vectors passed (12 focused tests); full regression passed (53 tests, 138 subtests).
- RED Task 5: reducer tests failed on the missing reducer API and bounded evidence fixture.
- GREEN Task 5: every ordering of bounded immutable evidence converged across all seven states, duplicate/conflict/late/orphan/repair cases, and rejected wrong occurrence/config/task assertions.
- GREEN Task 6: ownership, producer authority, 16-role IAM, OIDC, metrics/alerts, and lifecycle fixtures passed 10 focused tests.
- GREEN Task 7: queue/Lambda and ECS retry boundary fixtures passed 3 focused tests, including service/platform limits, redrive, partial-batch, concurrency, visibility, and one-hour retry behavior.
- GREEN Task 8: SimpleSpec compatibility and exact command/manual identity fixtures passed 4 focused tests.
- GREEN Task 9: final `./scripts/validate.sh` passed four Terraform roots, Ruff, strict mypy, 78 tests plus 154 subtests, Checkov, repository hygiene, lock stability, and generated-artifact cleanliness.

### Implementation Plan

- Build each normative contract domain as checked-in JSON/Markdown plus pure typed offline conformance helpers.
- Add failing domain tests before each task, then implement the minimum catalogs, schemas, fixtures, and validation needed for green.
- Keep Terraform modules resource-free, preserve credential isolation, and finish with the single repository validation command.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Task 1 completed: published the initial package manifest, migration/release records, exact-byte inventory validation, semantic classification fixtures, and normative consumer/security/rollback documentation.
- Task 2 completed: published nine boundary schemas, auxiliary payload/processed-event schemas, an offline registry, strict JSON parsing, version/timestamp semantics, and secret-safety policy fixtures.
- Task 3 completed: implemented the restricted RFC 8785 profile, CONFIG hashing, exact occurrence bytes/digests, and literal cross-language-sensitive vectors.
- Task 4 completed: froze the recurring schedule catalog and wheel-backed evaluator with deterministic DST, activation-window, rate, generation, and rejection fixtures.
- Task 5 completed: published canonical event/key/correlation catalogs, complete occurrence/attempt/processed-event records, and a deterministic occurrence-aware reducer conformance suite.
- Task 6 completed: published single-owner integration edges, explicit least-privilege role boundaries, non-body producer authority, immutable GitHub OIDC claims, bounded observability, and two-phase lifecycle contracts.
- Task 7 completed: froze stricter platform queue/Lambda constraints and ECS `RunTask` idempotency/recovery limits with boundary-value fixtures.
- Task 8 completed: published current component ranges, stable migration failures, initial-release retention semantics, and separate operator/canonical command identities.
- Task 9 completed: promoted all five exact contract dependencies, typed and linted conformance tooling, offline/credential-free proof, manifest/release inventory, and consumer/rollback documentation.
- Scope preserved: no Terraform resource/data/backend blocks, runtime production behavior, OIDC workflow privileges, AWS state, plans, credentials, or deployment artifacts were added.

### File List

- M `README.md`
- M `_bmad-output/implementation-artifacts/1-2-publish-canonical-compatibility-contracts.md`
- M `_bmad-output/implementation-artifacts/sprint-status.yaml`
- M `contracts/README.md`
- A `contracts/manifest.json`
- A `contracts/migrations/v1.0.0.md`
- A `contracts/releases/1.0.0.json`
- A `contracts/v1/catalogs/commands.json`
- A `contracts/v1/catalogs/compatibility.json`
- A `contracts/v1/catalogs/event-types.json`
- A `contracts/v1/catalogs/iam.json`
- A `contracts/v1/catalogs/keys-and-correlation.json`
- A `contracts/v1/catalogs/lifecycle.json`
- A `contracts/v1/catalogs/metrics-alerts.json`
- A `contracts/v1/catalogs/oidc.json`
- A `contracts/v1/catalogs/ownership.json`
- A `contracts/v1/catalogs/producers.json`
- A `contracts/v1/catalogs/queue-lambda-constraints.json`
- A `contracts/v1/catalogs/reducer.json`
- A `contracts/v1/catalogs/schedules.json`
- A `contracts/v1/catalogs/secret-safety.json`
- A `contracts/v1/fixtures/canonical-json/invalid.json`
- A `contracts/v1/fixtures/canonical-json/vectors.json`
- A `contracts/v1/fixtures/compatibility/cases.json`
- A `contracts/v1/fixtures/compatibility/commands.json`
- A `contracts/v1/fixtures/compatibility/semantic-change-classification.json`
- A `contracts/v1/fixtures/iam/cases.json`
- A `contracts/v1/fixtures/iam/producer-authority.json`
- A `contracts/v1/fixtures/iam/raw-aws-producer-shapes.json`
- A `contracts/v1/fixtures/identity/occurrence-v1.json`
- A `contracts/v1/fixtures/lifecycle/cases.json`
- A `contracts/v1/fixtures/oidc/cases.json`
- A `contracts/v1/fixtures/queue-lambda/cases.json`
- A `contracts/v1/fixtures/reducer/cases.json`
- A `contracts/v1/fixtures/schedules/cases.json`
- A `contracts/v1/fixtures/schemas/invalid-instances.json`
- A `contracts/v1/fixtures/schemas/raw-parser-cases.json`
- A `contracts/v1/fixtures/schemas/secret-safety-cases.json`
- A `contracts/v1/fixtures/schemas/valid-instances.json`
- A `contracts/v1/schemas/alert.schema.json`
- A `contracts/v1/schemas/cell-contract.schema.json`
- A `contracts/v1/schemas/command.schema.json`
- A `contracts/v1/schemas/common.schema.json`
- A `contracts/v1/schemas/completion-signal.schema.json`
- A `contracts/v1/schemas/config.schema.json`
- A `contracts/v1/schemas/deployment-identity.schema.json`
- A `contracts/v1/schemas/evidence-envelope.schema.json`
- A `contracts/v1/schemas/occurrence-record.schema.json`
- A `contracts/v1/schemas/payloads/command-authorized.schema.json`
- A `contracts/v1/schemas/payloads/completion-observed.schema.json`
- A `contracts/v1/schemas/payloads/deadline-reached.schema.json`
- A `contracts/v1/schemas/payloads/occurrence-expected.schema.json`
- A `contracts/v1/schemas/payloads/occurrence-launch.schema.json`
- A `contracts/v1/schemas/payloads/task-launch-result.schema.json`
- A `contracts/v1/schemas/payloads/task-state.schema.json`
- A `contracts/v1/schemas/processed-event.schema.json`
- A `contracts/v1/schemas/task-attempt-record.schema.json`
- M `pyproject.toml`
- M `scripts/validate.py`
- A `tests/contract/support/__init__.py`
- A `tests/contract/support/contracts.py`
- A `tests/contract/test_contract_commands.py`
- A `tests/contract/test_contract_compatibility.py`
- A `tests/contract/test_contract_iam.py`
- A `tests/contract/test_contract_identity.py`
- A `tests/contract/test_contract_lifecycle.py`
- A `tests/contract/test_contract_manifest.py`
- A `tests/contract/test_contract_offline.py`
- A `tests/contract/test_contract_oidc.py`
- A `tests/contract/test_contract_queue_lambda.py`
- A `tests/contract/test_contract_reducer.py`
- A `tests/contract/test_contract_schedules.py`
- A `tests/contract/test_contract_schemas.py`
- M `tests/contract/test_documentation.py`
- M `tests/contract/test_repository_structure.py`
- M `uv.lock`

### Change Log

- 2026-07-15: Published Compatibility Package `1.0.0`, offline conformance tooling, exact dependency pins, and repository validation/documentation integration; moved Story 1.2 to review.
