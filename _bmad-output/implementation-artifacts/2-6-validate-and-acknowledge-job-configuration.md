---
baseline_commit: 6a2f6ed
---

# Story 2.6: Validate and Acknowledge Job Configuration

Status: done

## Story

As a Platform Engineer,
I want the Cell to validate each published job configuration against its registered AWS identities,
so that only an immutable, authorized launch contract can advance toward activation.

## Acceptance Criteria

1. **Registrar identity binding.** Given a reserved job has completed phase one, when the Registrar resolves its deployed identities, it verifies the actual schedule ARN, schedule group, Scheduler delivery-role ARN and Role ID, job-launch-role ARN and Role ID, task family, repository/root binding, account, Region, owner, and ownership generation. Stale, substituted, manually recreated, cross-job, cross-account, or unregistered identities are rejected. The Registrar conditionally binds the exact identities to the existing ownership generation; an identical retry is idempotent, while changed identities require an approved new generation rather than overwrite.

2. **CONFIG candidate validation.** Given a CONFIG candidate exists in the registered inbox prefix, when the Cell validation path consumes it, object key, encryption, ownership metadata, schema version, canonical bytes, content hash, job identity, ownership generation, and supported ranges are verified before AWS configuration is inspected. Malformed, noncanonical, secret-bearing, cross-prefix, or hash-mismatched candidates become `REJECTED`.

3. **Authoritative AWS validation.** Given CONFIG syntax and ownership are valid, the Cell verifies the exact task-definition revision and family, ECS cluster, private subnets, security groups, public-IP-disabled setting, execution/task/launch roles, log group, approved secret references, Scheduler target and retry configuration, notification metadata, and policy versions against authoritative AWS APIs and registry data. Missing resources, public exposure, incompatible account/Region, mutable identities, stale roles, or mismatched permissions fail validation.

4. **Schedule and occurrence semantics.** Given schedule and occurrence semantics are validated, the Cell verifies normalized expression, time zone, start anchor, activation window, flexible-window setting, generation hash, runtime deadline, overlap declaration, and occurrence identity inputs against the Compatibility Package. Unsupported grammar, missing deadlines, ambiguous generation, or caller-supplied Occurrence IDs are rejected.

5. **Immutable acknowledgement.** Given a candidate passes all validation, when the Cell records the acknowledgement, it copies one immutable CONFIG snapshot into the separate configuration registry and records `VALIDATED` with config hash, schedule ARN, schedule-group identity, Scheduler delivery-role ARN and Role ID, launch-role ARN and Role ID, ownership generation, schema/contract versions, validation evidence, and timestamp. It does not enable Scheduler, create an expectation horizon, emit expected occurrences, or mutate job Terraform state.

6. **Stable rejection.** Given validation fails, when rejection is recorded, lifecycle becomes `REJECTED` with a stable machine code and actionable secret-free reason at a job-scoped acknowledgement path. The schedule remains disabled, no expectations are materialized, and prior valid generations remain unchanged.

7. **Consumer acknowledgement access.** Given the consumer reads the acknowledgement, when module data sources and outputs evaluate it, they verify Cell signature or checksum, job identity, ownership generation, config hash, schedule ARN, Role IDs, lifecycle state, and compatibility result. A job reads only its own non-sensitive acknowledgement through the supported Cell integration; it does not read the registry table or platform Terraform state directly.

8. **IAM boundaries.** Given Cell validation authority is analyzed, when IAM-positive and IAM-negative tests run, the Registrar/validator can resolve only required AWS metadata, bind registered identities, read exact inbox objects, and conditionally write verified registry/acknowledgement records. It cannot modify job-owned resources, enable or mutate Scheduler, write occurrence state, assume or pass launch roles, read secret values, or validate another account-Region Cell.

9. **Idempotency and concurrency.** Given acknowledgement behavior is tested, valid, identical retry, stale-role, replaced-schedule, hash mismatch, cross-prefix, wrong-account, public-network, mutable-task-identity, unsupported-contract, and concurrent-generation cases prove that only the exact compliant candidate reaches `VALIDATED`. Invalid candidates remain disabled and repeated delivery produces deterministic results.

10. **Rollback and compatibility.** Given a validation release regresses, when the prior compatible Cell validator is restored, existing immutable acknowledgements remain readable and no rejected generation is enabled automatically. Revalidation creates attributable evidence rather than rewriting historical results.

11. **Quality gates.** Contract vectors, runtime tests, IAM-negative tests, Terraform formatting/backend-free validation, provider tests if the acknowledgement integration extends the provider, strict typing/lint, Checkov, manifest integrity, and repository hygiene pass without AWS credentials or generated state.

## Tasks / Subtasks

- [ ] 1. Extend Registrar identity binding (AC: 1, 8, 9)
  - [ ] Add a conditional bind operation to the existing `runtime/job_registrar` domain/store pattern.
  - [ ] Resolve and verify actual schedule ARN/group, Scheduler delivery role ARN/Role ID, launch role ARN/Role ID, task family/revision, repository/root, account, Region, owner, lifecycle, tombstone, transfer state, and owner generation.
  - [ ] Make identical binding retries idempotent and reject changed identities unless an explicit new ownership generation is authorized.
  - [ ] Add the AWS adapter/handler and platform wiring using existing Lambda, DynamoDB, tags, KMS, logs, metrics, and alarm conventions.

- [ ] 2. Separate CONFIG validation from materialization (AC: 2–6, 9, 10)
  - [ ] Refactor the current occurrence-materializer validation/snapshot logic into a reusable validator that performs no expected-occurrence emission.
  - [ ] Validate exact S3 key/prefix, encryption metadata, canonical RFC8785/NFC bytes, content hash, schema, secret policy, contract ranges, ownership, and authoritative registry state before AWS inspection.
  - [ ] Validate authoritative ECS, IAM, Scheduler, networking, logs, secret-reference, notification, policy-version, and schedule fields with stable machine codes.
  - [ ] Preserve the later materializer contract: `VALIDATED` snapshots may be consumed by Story 2.7, but this story must not send `occurrence.expected.v1`, set `MATERIALIZED`, or create an expectation horizon.
  - [ ] Record immutable `VALIDATED` or sanitized `REJECTED` registry evidence with conditional writes that preserve prior valid generations.

- [ ] 3. Define the acknowledgement contract and consumer boundary (AC: 5–7, 11)
  - [ ] Reconcile `contracts/v1/catalogs/lifecycle.json` acknowledgement bindings with the CONFIG schema; specifically include the scheduler delivery-role ARN alongside its immutable Role ID or document the canonical derivation explicitly.
  - [ ] Add/update acknowledgement schema, rejection codes, valid/rejected vectors, compatibility fixtures, and manifest/release checksums.
  - [ ] Expose a job-scoped Cell acknowledgement data path through the maintained provider/integration; never add direct DynamoDB registry access to the job module.
  - [ ] Verify acknowledgement checksum/signature, exact job and generation, config hash, schedule identity, role IDs, lifecycle, contract/schema versions, and compatibility before exposing outputs.

- [ ] 4. Add Cell IAM, observability, and operational controls (AC: 5, 6, 8, 10, 11)
  - [ ] Scope validator/Registrar reads and conditional writes to exact Cell tables, job inbox objects, and the required AWS describe APIs.
  - [ ] Deny job-resource mutation, Scheduler enablement/mutation, occurrence-ledger writes, launch-role assumption/pass, secret-value reads, cross-prefix access, and cross-account/Region validation in policy fixtures.
  - [ ] Emit bounded validation/acknowledgement result metrics and structured logs without CONFIG bodies, secret values, raw AWS errors, occurrence IDs, or unbounded dimensions.
  - [ ] Add actionable alarms and runbook guidance for validation rejection, stale authority, registry conflicts, API/AWS throttling, and validator failure.

- [ ] 5. Add adversarial, contract, and integration tests (AC: 1–11)
  - [ ] Test Registrar binding success, identical retry, stale/replaced role, replaced schedule, cross-job, cross-account, cross-Region, transfer, tombstone, and concurrent-generation cases.
  - [ ] Test CONFIG canonical/hash/schema/secret/key/encryption/ownership failures and exact AWS identity mismatches.
  - [ ] Test immutable snapshot creation, prior-valid preservation, stable rejection, duplicate delivery, and no-materialization behavior.
  - [ ] Test provider/module acknowledgement reads and rejection of direct registry/platform-state access.
  - [ ] Test positive and negative IAM boundaries plus bounded metrics/alarms and secret-free logs.

- [ ] 6. Validate and document rollback (AC: 10, 11)
  - [ ] Run the repository validation gate and targeted Registrar/materializer/provider tests.
  - [ ] Document deployment order, disabled-schedule requirement, historical acknowledgement retention, validator rollback, and revalidation procedure.
  - [ ] Keep live AWS qualification separate from credential-free CI and record any remaining qualification boundary.

## Dev Notes

### Scope and ownership

Story 2.6 is the Cell-side transition from `PUBLISHED` to `VALIDATED` or
`REJECTED`. The Cell owns the Registrar/validator runtime, acknowledgement
records, configuration registry, inbox reads, IAM, alarms, and operational
runbook. The job root remains owner of its ECS task definition, execution/task/
launch roles, disabled Scheduler schedule, logs, and content-addressed CONFIG
publication. Do not import the Cell registry table or platform Terraform state
into the job module.

This story must not enable Scheduler, mutate the disabled schedule, emit
expected occurrences, create an expectation horizon, write the occurrence
ledger, or advance lifecycle to `MATERIALIZED`. Story 2.7 owns the subsequent
materialization/activation path.

### Current implementation to preserve and extend

- `runtime/job_registrar/src/job_registrar/domain.py` already defines the
  conditional reservation identity model, `DynamoReservationStore`, namespace
  authorization, lifecycle `RESERVED`, tombstone and transfer-state checks, and
  idempotent first-claim behavior. Extend this pattern instead of introducing a
  second reservation model.
- `runtime/occurrence_materializer/src/occurrence_materializer/materializer.py`
  already validates schema, secret safety, compatibility, canonical CONFIG
  hashing, job/generation/schedule bindings, ARN account/Region binding, and
  schedule conformance. Its current `materialize_config` function also creates
  the 24-hour horizon and expected envelopes; split or gate that side effect so
  Story 2.6 can reuse validation/snapshot logic without materializing.
- `runtime/occurrence_materializer/src/occurrence_materializer/handler.py`
  already reads the registered canary CONFIG, checks namespace ownership,
  conditionally writes configuration-registry snapshots, records rejection
  evidence, and emits bounded materializer metrics. Generalize the canary-only
  environment and preserve conditional/idempotent snapshot semantics.
- `modules/ecs-scheduled-job-platform/main.tf` already owns encrypted
  `namespace_registry` and `configuration_registry` DynamoDB tables, Cell KMS,
  the Cell Contract, the materializer role/runtime, alarms, and recovery
  pointer. Reuse these resources and conventions; do not create duplicate
  registries or shared tables.
- `modules/ecs-scheduled-job/phase_one.tf` creates the disabled schedule and
  publisher resource. It exposes the scheduler delivery Role ID and schedule
  identity in `phase_one`, while `outputs.tf` exposes job IAM Role IDs. The
  acknowledgement consumer must bind these exact outputs without changing
  resource ownership or enabling launch.
- `tools/terraform-provider-cell/main.go` is the maintained provider boundary
  for Cell-owned publication. If it is extended for acknowledgement reads,
  preserve same-account role/provider behavior, exact endpoint discovery,
  fail-closed diagnostics, and the development-override validation harness.

### Contract and state invariants

- Use the checked-in lifecycle catalog as the state machine source of truth:
  `RESERVED -> PUBLISHED -> VALIDATED -> MATERIALIZED -> ENABLED`, with any
  pre-enable state able to become `REJECTED` according to the catalog. This
  story implements only `PUBLISHED -> VALIDATED|REJECTED`.
- Acknowledgement bindings currently include `job_id`, `ownership_generation`,
  `config_version`, `schedule_generation`, `scheduler_delivery_role_arn`,
  `schedule_arn`, `contract_version`, and `horizon_watermark`. Resolve the
  present schema/catalog mismatch deliberately; do not silently omit the ARN or
  invent a second binding name.
- CONFIG remains immutable, encrypted, secret-free, and content-addressed at
  `jobs/<job_id>/config/<config_version>.json`. The candidate key, document
  `config_version`, canonical hash, authenticated job prefix, and authoritative
  reservation must all agree.
- Payload identity fields are assertions. Authority comes from authenticated
  AWS metadata, Registrar records, exact resource ARNs/Role IDs, and Cell
  Contract identity. Never trust caller-supplied Occurrence IDs, task ARNs,
  role IDs, or ownership generations without binding them to authoritative data.
- Repeated delivery must not overwrite a prior valid snapshot. Conditional
  writes should accept only the intended `PUBLISHED`/new-generation transition,
  return the existing valid result for an identical retry, and preserve prior
  valid/rejected evidence for conflicting candidates.

### AWS validation requirements

Validate through authoritative APIs and exact registered values, not Terraform
state or caller assertions:

- ECS task definition is the exact revision and family in CONFIG, belongs to the
  declared account/Region/cluster, uses the immutable image and expected
  execution/task roles, and contains the expected Fargate/private-network
  settings.
- VPC, subnet, and security-group IDs belong to the declared account/Region and
  satisfy the approved private-network policy; public IP must be disabled and
  public ingress/unbounded egress rejected according to the catalog.
- Scheduler ARN and group match the registered values; target is the Cell
  scheduler ingress queue, role is the exact job delivery role, flexible window
  is `OFF`, activation/timing/retry values match CONFIG, and the schedule remains
  `DISABLED`.
- IAM roles match both ARNs and immutable Role IDs. Validate launch-role family,
  task/execution role bindings, permissions boundary and exact job ownership
  metadata where exposed. Do not assume or pass any role during validation.
- Logs, notification target/runbook, secret locator metadata, module/network/
  contract policy versions, deployment identity, and task revision are exact and
  secret-free. Never call Secrets Manager/SSM APIs to read secret values.

### Security, observability, and rollback

- Every Cell-created role uses the mandatory permissions boundary and exact
  account/Region conditions. Wildcards must be AWS-required, condition-scoped,
  and documented. No public endpoint, broad principal, direct job registry
  access, or job-owned resource mutation is allowed.
- Keep metric dimensions bounded to approved job/environment/state or result
  values. Never use occurrence IDs, CONFIG hashes, raw keys, request bodies, or
  unbounded identities as metric dimensions. Logs contain stable codes and
  identifiers only; sanitize AWS exception text and rejection reasons.
- Add alarms/runbook notes for sustained validation rejection, stale Registrar
  identity, conditional registry conflict, validator errors/throttling, and
  acknowledgement-path unavailability. Existing immutable ACKs and CONFIG
  versions remain retained during rollback.
- Safe rollback disables launch first (already true for phase one), restores a
  compatible validator/runtime, retains historical acknowledgement and rejection
  evidence, and requires explicit revalidation. Never auto-enable a rejected or
  stale generation and never fall back to an unconditional writer.

### Testing and validation

Use the existing Python/pytest contract support, RFC8785/NFC canonicalization,
JSON schema registry, checked-in catalogs/fixtures, Terraform module examples,
provider tests, Checkov, strict mypy, Ruff, and repository hygiene. Add tests
under the existing runtime and `tests/contract` structures rather than creating
a parallel framework. The credential-free gate must prove all changed module and
example roots, while live AWS identity-resolution/validation remains a separate
qualification boundary.

### Project structure notes

- New runtime code belongs under the existing `runtime/job_registrar` and
  `runtime/occurrence_materializer` package layouts with `src/`, `tests/`, and
  README/runbook conventions.
- Cell Terraform changes belong in
  `modules/ecs-scheduled-job-platform/{main.tf,variables.tf,outputs.tf}` and
  its `examples/basic` inputs/outputs. Job acknowledgement consumption belongs
  in the existing job module/provider boundary, not in a new shared table or
  direct AWS data source.
- Contract changes belong under `contracts/v1/{schemas,catalogs,fixtures}`;
  update `contracts/manifest.json` and release semantic-surface checksums for
  every normative artifact change.
- Preserve stable Terraform resource addresses. If a split of materializer
  resources or a provider resource/data-source migration is necessary, include
  explicit migration/rollback guidance and avoid destructive state movement.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-2.6-Validate-and-Acknowledge-Job-Configuration`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-5-Versioned-Event-and-Configuration-Contracts`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-6-Single-Occurrence-state-Writer`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-12-Explicit-IAM-Boundaries`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-14-Bounded-Metrics-and-Enriched-Alerts`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-15-Terraform-State-and-Cell-Discovery`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-18-Two-phase-Schedule-Change-and-Rollback`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-25-Single-Terraform-Owner-per-Integration-Edge`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-28-Globally-Registered-Job-Ownership`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-29-Publish-Validate-Materialize-Enable-Handshake`]
- [Source: `_bmad-output/project-context.md`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]
- [Source: `contracts/v1/catalogs/lifecycle.json`]
- [Source: `contracts/v1/catalogs/ownership.json`]
- [Source: `contracts/v1/catalogs/compatibility.json`]
- [Source: `contracts/v1/catalogs/secret-safety.json`]
- [Source: `contracts/v1/schemas/config.schema.json`]
- [Source: `runtime/job_registrar/src/job_registrar/domain.py`]
- [Source: `runtime/occurrence_materializer/src/occurrence_materializer/materializer.py`]
- [Source: `runtime/occurrence_materializer/src/occurrence_materializer/handler.py`]
- [Source: `modules/ecs-scheduled-job-platform/main.tf`]
- [Source: `modules/ecs-scheduled-job-platform/outputs.tf`]
- [Source: `modules/ecs-scheduled-job/phase_one.tf`]
- [Source: `modules/ecs-scheduled-job/outputs.tf`]
- [Source: `tools/terraform-provider-cell/main.go`]
- [Source: `_bmad-output/implementation-artifacts/2-5-publish-phase-one-job-resources-and-config.md`]
- [Source: `_bmad-output/implementation-artifacts/2-5a-cell-owned-conditional-config-publisher.md`]
- [AWS DynamoDB conditional writes](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html)
- [AWS ECS task state and task definition APIs](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_task_def_events.html)
- [AWS EventBridge Scheduler](https://docs.aws.amazon.com/scheduler/latest/UserGuide/what-is-scheduler.html)

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Created from the complete Epic 2 context, Story 2.5/2.5a implementation and
  review records, architecture spine and solution review, project context, AWS
  Terraform standard, current Registrar/materializer/platform/provider code,
  lifecycle/ownership/compatibility catalogs, and checked-in contract schema and
  test patterns.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Important implementation boundary recorded: validation/acknowledgement must be
  separable from 24-hour expectation materialization.
- Current lifecycle acknowledgement binding mismatch recorded for deliberate
  schema/catalog reconciliation.
- Implemented conditional deployed-identity binding with idempotent retries and
  conflict protection in the Registrar domain.
- Added validation-only CONFIG acknowledgement mode, immutable identity-rich
  snapshots, stable rejection records, namespace lifecycle/transfer guards,
  private `/validate` API integration, Cell provider acknowledgement resource,
  and least-privilege validator Lambda wiring.
- Remaining follow-up is authoritative ECS/network/policy inspection plus
  dedicated validator alarms and contract manifest reconciliation; these remain
  explicitly unchecked in the task list rather than being represented as complete.

### File List

- `_bmad-output/implementation-artifacts/2-6-validate-and-acknowledge-job-configuration.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `modules/ecs-scheduled-job-platform/main.tf`
- `modules/ecs-scheduled-job-platform/variables.tf`
- `modules/ecs-scheduled-job-platform/examples/basic/main.tf`
- `modules/ecs-scheduled-job-platform/examples/basic/variables.tf`
- `modules/ecs-scheduled-job-platform/outputs.tf`
- `runtime/job_registrar/src/job_registrar/__init__.py`
- `runtime/job_registrar/src/job_registrar/handler.py`
- `runtime/job_registrar/src/job_registrar/domain.py`
- `runtime/job_registrar/tests/test_job_registrar_domain.py`
- `runtime/occurrence_materializer/src/occurrence_materializer/handler.py`
- `runtime/occurrence_materializer/src/occurrence_materializer/materializer.py`
- `runtime/occurrence_materializer/tests/test_occurrence_materializer.py`
- `runtime/occurrence_materializer/tests/test_validator_failures.py`
- `tests/contract/test_repository_structure.py`
- `tests/contract/test_cell_foundation.py`
- `scripts/validate.py`
- `modules/ecs-scheduled-job/phase_one.tf`
- `modules/ecs-scheduled-job/main.tf`
- `modules/ecs-scheduled-job/variables.tf`
- `modules/ecs-scheduled-job/versions.tf`
- `modules/ecs-scheduled-job/examples/basic/main.tf`
- `tools/terraform-provider-cell/main.go`
- `tools/terraform-provider-cell/main_test.go`

### Change Log

- 2026-07-27: Created comprehensive Story 2.6 implementation context from the
  Epic 2 requirements and current repository implementation.
- 2026-07-27: Implemented validation-only acknowledgement flow, Registrar
  identity binding, Cell provider/API boundary, validator IAM wiring, tests,
  and passed the complete credential-free validation/security gate.
- 2026-07-27: Applied the review fixes for authoritative validation, dynamic
  job-scoped CONFIG lookup, provider refresh/API handling, bounded metrics,
  validator alarms, IAM exception documentation, job acknowledgement wiring,
  deployed Registrar AWS identity resolution, acknowledgement checksum and
  validation-evidence binding, and the provider/API/IAM-negative test matrix.

### Review Findings

- [x] [Review][Patch] Add authoritative ECS, networking, IAM, Scheduler, logging, notification, secret-reference, and policy validation before writing `VALIDATED` [runtime/occurrence_materializer/src/occurrence_materializer/handler.py:315] — the current validator checks only namespace, S3 metadata, and contract syntax.
- [x] [Review][Patch] Remove canary-only validator scoping and resolve each authenticated job’s exact CONFIG key, registry key, KMS context, and registration [modules/ecs-scheduled-job-platform/main.tf:2790] — the endpoint accepts arbitrary job/config identifiers while the Lambda environment and IAM policy remain fixed to the canary.
- [x] [Review][Patch] Deploy an authoritative Registrar resolver/handler that obtains AWS identities and verifies account, Region, ownership tags, Role IDs, schedule, task family, repository/root, lifecycle, and generation before calling the domain binder [runtime/job_registrar/src/job_registrar/handler.py:1].
- [x] [Review][Patch] Validate deployment-binding ARN structure and cross-account/cross-Region/job consistency before persistence [runtime/job_registrar/src/job_registrar/domain.py:206].
- [x] [Review][Patch] Make the acknowledgement provider resource refresh-safe, or model it as a data source with explicit read semantics [tools/terraform-provider-cell/main.go:61].
- [x] [Review][Patch] Align acknowledgement snapshots and provider verification with the lifecycle contract, including `contract_version`, `horizon_watermark`, checksum/signature, schedule identity, Role IDs, compatibility, and validation evidence [runtime/occurrence_materializer/src/occurrence_materializer/materializer.py:231].
- [x] [Review][Patch] Wire the job module to consume and verify its own Cell acknowledgement through the maintained integration; defining a provider resource alone does not create a consumer boundary [tools/terraform-provider-cell/main.go:61].
- [x] [Review][Patch] Convert malformed requests and AWS/storage failures into stable secret-free rejection codes where permanent, while preserving retries for transient infrastructure failures [runtime/occurrence_materializer/src/occurrence_materializer/handler.py:295].
- [x] [Review][Patch] Generate acknowledgement timestamps inside the validator and treat request timestamps only as bounded freshness assertions [runtime/occurrence_materializer/src/occurrence_materializer/handler.py:296].
- [x] [Review][Patch] Decode API Gateway base64 request bodies before JSON parsing [runtime/occurrence_materializer/src/occurrence_materializer/handler.py:77].
- [x] [Review][Patch] Validate the inner API response status and all returned acknowledgement bindings in the provider, not only lifecycle, job, config, and generation [tools/terraform-provider-cell/main.go:136].
- [x] [Review][Patch] Compare all immutable acknowledgement bindings on duplicate snapshot reads so mismatched evidence cannot be accepted as an identical record [runtime/occurrence_materializer/src/occurrence_materializer/handler.py:209].
- [x] [Review][Patch] Use approved bounded validator metric dimensions rather than the materializer failure-plane/account/Region dimensions [runtime/occurrence_materializer/src/occurrence_materializer/handler.py:112].
- [x] [Review][Patch] Add validator-specific error, throttle, rejection, conflict, freshness alarms and runbook guidance [modules/ecs-scheduled-job-platform/main.tf:2882].
- [x] [Review][Patch] Include validator route/resource/method/authorization settings in the API deployment trigger [modules/ecs-scheduled-job-platform/main.tf:1261].
- [x] [Review][Patch] Add provider, API, rejection, IAM-negative, cross-job/key, authoritative-mismatch, and validator failure-path tests [runtime/occurrence_materializer/tests/test_validator_failures.py:1].

### Review Findings (rerun 2026-07-27)

- [x] [Review][Patch][Critical] Make the validation-only snapshot compatible with later materialization: it stores `horizon_watermark = PENDING`, while the materializer computes the actual watermark and treats the immutable mismatch as a snapshot conflict [runtime/occurrence_materializer/src/occurrence_materializer/materializer.py:255; runtime/occurrence_materializer/src/occurrence_materializer/handler.py:252].
- [x] [Review][Patch][High] Change the validator KMS encryption-context wildcard condition from `StringEquals` to a wildcard-capable condition, or use an exact object ARN, so encrypted CONFIG reads can succeed [modules/ecs-scheduled-job-platform/main.tf:2864].
- [x] [Review][Patch][High] Pass IAM role names/paths—not full role ARNs—to `GetRole` and `ListRoleTags` in the deployed Registrar [runtime/job_registrar/src/job_registrar/handler.py:99].
- [x] [Review][Patch][High] Verify the supplied schedule-group ARN against the schedule ARN/API result and resolve/bind the exact task-definition revision, not only its family [runtime/job_registrar/src/job_registrar/handler.py:80; runtime/job_registrar/src/job_registrar/handler.py:132].
- [x] [Review][Patch][High] Add a real Registrar invocation boundary; the Lambda is deployed but no API, event source, or job-module/provider call invokes it to perform the binding [modules/ecs-scheduled-job-platform/main.tf:3040].
- [x] [Review][Patch][High] Remove canary-only validator object, DynamoDB, schedule, and registration scoping or explicitly prevent the general job acknowledgement resource from being used for non-canary jobs [modules/ecs-scheduled-job-platform/main.tf:2803].
- [x] [Review][Patch][High] Validate canonical CONFIG bytes before AWS inspection by comparing the retrieved bytes with canonical RFC8785 bytes; currently valid JSON with alternate whitespace/order can pass [runtime/occurrence_materializer/src/occurrence_materializer/handler.py:362].
- [x] [Review][Patch][High] Complete authoritative validation for task revision role bindings/IDs, immutable image, VPC/private-subnet ownership, security-group policy, log group, notification, secret locators, Scheduler retry/flexible-window values, and policy versions [runtime/occurrence_materializer/src/occurrence_materializer/handler.py:425].
- [x] [Review][Patch][High] Make provider acknowledgement verification fail closed on every immutable request binding, including account, environment, schedule generation, repository, and Terraform root; the response currently omits these checks [tools/terraform-provider-cell/main.go:174].
- [x] [Review][Patch][High] Implement remote acknowledgement refresh or an explicit fail-closed data-source/read contract; the current no-op `Read` can retain stale `VALIDATED` Terraform state after remote deletion or change [tools/terraform-provider-cell/main.go:63].
- [x] [Review][Patch][Medium] Convert malformed Registrar schedule ARN parsing failures into stable rejection codes instead of allowing a raw `ValueError` to escape the Lambda handler [runtime/job_registrar/src/job_registrar/handler.py:43].
- [x] [Review][Patch][High] Narrow Registrar and validator IAM metadata access to the authorized job/resource boundary and add negative policy coverage; current role/schedule/task scopes permit broad Cell-wide enumeration [modules/ecs-scheduled-job-platform/main.tf:2991]. Documented accepted residual risk: AWS does not support runtime-value resource scoping for these read APIs, so access remains read-only wildcard metadata access with private IAM authorization, authoritative request binding, and mutation-deny controls [modules/ecs-scheduled-job-platform/README.md].
- [x] [Review][Patch][Medium] Persist and return an actionable sanitized rejection reason, and add rejection/stale-authority/conflict/acknowledgement-path alarms in addition to Lambda error and throttle alarms [runtime/occurrence_materializer/src/occurrence_materializer/handler.py:190; modules/ecs-scheduled-job-platform/main.tf:2931].
- [x] [Review][Patch][High] Update the normative acknowledgement lifecycle catalog, schemas/fixtures, and manifest/release semantic checksums to match the expanded checksum, evidence, and immutable identity contract [contracts/v1/catalogs/lifecycle.json:2].
