---
epic: 3
story: 3.8
title: Migrate Compatible Platform Versions
status: done
baseline_commit: 36389c2182560e0e0f3c16312f0aa87366303fe4
---

# Story 3.8: Migrate Compatible Platform Versions

Status: done

## Story

As a Platform Owner,
I want major platform changes migrated through expand-migrate-contract,
so that active jobs, queued evidence, and rollback paths remain compatible during upgrade.

## Acceptance Criteria

1. **Migration inventory fails closed.** Given a release changes Cell, module, CONFIG, schema, runtime, workflow, index, or state contracts, migration planning inventories affected consumers, active/retired generations, CONFIG versions, occurrences, task attempts, queues/DLQs, replay and rollback horizons, state addresses, policies, and operator procedures. Unknown consumers, references, or horizon values block migration.
2. **Expand is additive.** Additive schemas, indexes, IAM permissions, runtime readers/writers, contract ranges, and workflow support are deployed before old behavior is removed. The stable Process Manager principal remains unchanged within the existing Cell major.
3. **Current and previous majors coexist.** Both interoperate through the longest queue, replay, maximum-runtime, retention, investigation, recovery, and rollback horizon. Queued/delayed events resolve their original schema, CONFIG, runtime, and task-definition identities.
4. **Terraform/state changes are explicit.** Preserve stable addresses where possible. Otherwise document exact `moved` blocks, import/state procedures, ordering, expected plan impact, and rollback limitations. Destructive replacement cannot be hidden inside compatibility work.
5. **Data/index migration is safe.** It is idempotent, resumable, bounded, observable, attributable, and validated against source/target counts, checksums, schemas, access patterns, and reducer invariants. Launch remains disabled for incomplete or inconsistent generations.
6. **Consumer readiness is attributable.** Each job records current identity, target version, validation result, required configuration/code change, owner, due point, and rollback identity. Terraform-plan success alone never marks a consumer ready.
7. **Cutover uses protected fresh plans.** Versioned Lambda aliases, Cell Contract ranges/pointers, workflow manifests, and policy catalogs switch through fresh reviewed plans and protected approvals. No mixed unsupported contract or generation lacking acknowledgement/expectations may be enabled.
8. **Rollback preserves compatibility.** On failed cutover verification, aliases and contract pointers return to the prior compatible version; launch remains/becomes disabled; retained evidence is replayed only through supported paths; no old schema, CONFIG, runtime, module, or task revision is removed.
9. **Qualification covers mixed operation.** Test current-to-new, previous-to-new, delayed events, DLQ replay, active tasks, schedule-generation changes, state moves, partial migration, rollback, and mixed-version failures. Supported combinations preserve occurrence state, exactly-one launch, completion correlation, alerting, and recovery; unsupported combinations fail before side effects.
10. **Completion evidence is retained.** Record source/target versions, consumer inventory, plans, approvals, data checks, cutover timing, verification, rollback result, remaining horizon, and known limitations. Completion does not authorize deprecation/removal; Story 3.9 owns that boundary.

## Tasks / Subtasks

- [x] Define migration, readiness, horizon, cutover, rollback, and completion-evidence contracts (AC: 1, 3, 6, 8, 10)
  - [x] Reuse the immutable release manifest, Compatibility Package, Cell Contract, lifecycle acknowledgement, Deployment Identity, and existing checksum/evidence formats.
  - [x] Add strict schemas and stable `TargetViolation` codes for incomplete inventory, unknown references/horizons, unsupported combinations, stale readiness, mixed contracts, unsafe state moves, and rollback incompatibility.
  - [x] Bind records to source/target releases, checksums, owner, actor, timestamps, and freshness/expiry; distinguish dated observations from permanent constraints/runtime exceptions.
- [x] Build the complete consumer and horizon inventory (AC: 1, 3, 5, 6)
  - [x] Inventory consumers, repositories/roots, jobs, ownership generations, CONFIG, occurrences, task attempts, queues/DLQs, state addresses, policies, procedures, active/retired versions, and rollback identities.
  - [x] Fail closed on unknown consumers, references, owners, generations, horizons, or wildcard selections; independently verify inventory checksums.
  - [x] Calculate the maximum horizon from queue/DLQ, replay, runtime, investigation, recovery, retention, and rollback obligations.
- [x] Implement additive expand and cross-major compatibility checks (AC: 2, 3, 7)
  - [x] Require additive schemas/ranges, indexes, permissions, readers/writers, runtime/workflow/policy support before cutover.
  - [x] Preserve the stable Process Manager principal and resolve queued evidence using original schema, CONFIG, runtime, task-definition, producer, and ownership identity.
  - [x] Reject unsupported schema/config/component combinations before side effects with migration guidance.
- [x] Implement idempotent, resumable, bounded data/index migration (AC: 5)
  - [x] Define checkpoint/resume identity, bounded batches/age, retry behavior, operator authority, and partial/failure states.
  - [x] Compare source/target counts, checksums, schemas, access patterns, and reducer invariants; keep launch disabled until complete.
  - [x] Keep Cell-owned mutations behind Process Manager and preserve Cell-root/job-root ownership.
- [x] Govern Terraform/state migration and protected cutover (AC: 4, 7)
  - [x] Preserve addresses or add exact moved/import/state procedures, ordering, plan impact, and rollback limitations.
  - [x] Require immutable inputs, fresh reviewed plans, policy checks, protected approvals, exact target binding, and exact current acknowledgement.
  - [x] Switch aliases, Contract pointers, workflow manifests, and policy catalogs without mixed unsupported states.
- [x] Implement protected rollback and preserve old identities (AC: 3, 8, 10)
  - [x] Disable launch first; retain old schemas/CONFIG/runtimes/modules/task revisions/evidence; restore compatible aliases and pointers.
  - [x] Replay only supported evidence through canonical ingress/reducer; verify scheduling, occurrence state, exactly-one launch, completion, logs, deadlines, alarms, notifications, and recovery.
  - [x] Record rollback result, application compensation responsibility, remaining horizon, and limitations; do not perform Story 3.9 cleanup.
- [x] Add deterministic migration and workflow fixtures (AC: 1-10)
  - [x] Cover unknown inventory, stale checksums, unsupported ranges, missing acknowledgement, mixed versions, untrusted inventory, partial/resumed migration, and rollback.
  - [x] Cover delayed events, DLQ replay, active tasks, schedule changes, state moves, address changes, destructive replacement, exact-plan drift, duplicate evidence, and launch-disabled behavior.
  - [x] Run without live AWS credentials/state, production Environments, committed plans, raw CONFIG, or secrets.
- [x] Document migration operations and rollback (AC: 1, 4, 6, 8, 10)
  - [x] Document inventory inputs, horizon calculation, readiness, two-phase cutover, evidence retention, operator authority, escalation, rollback, and application compensation.
  - [x] State that migration completion does not deprecate, remove, or garbage-collect versions; Story 3.9 owns that boundary.

## Dev Notes

### Required reuse and invariants

- `contracts/` is normative. Extend its schemas, compatibility/lifecycle catalogs, migration metadata, fixtures, release metadata, and raw-byte checksums together.
- Consume Story 3.7's `release_manifest.py` and release identity; do not create a second version, checksum, canonicalization, or immutable-reference format. Use RFC8785/JCS and `TargetViolation` codes.
- Reuse `scripts/trusted_plan.py`, `production_apply.py`, `production_bundle.py`, `deployment_evidence.py`, `production_policy.py`, `deployment_targets.py`, and `validate.py` for target, plan, policy, identity, evidence, migration-diff, and checksum boundaries.
- Only Process Manager mutates occurrence, task-attempt, processed-event, and alert-outbox state. CONFIG/task definitions remain append-only while referenced by occurrences, queues, DLQs, investigations, or rollback windows. Physical cleanup is Story 3.9/lifecycle principal work.

### Architecture guardrails

- AD-18: two-phase schedule changes disable/drain old generation, then publish/materialize/verify/enable future-anchored new generation; rollback reverses this and retains evidence until recovery and Job Owner compensation.
- AD-20/22: credential-free validation, trusted plans, protected approvals, short-lived OIDC/operator authority, immutable identity, secret-safe config, logs/retention, alarms, impact/cost notes, and runbook rollback/forward-fix are required.
- AD-23/24: every component consumes the same Compatibility Package; breaking changes are additive, Process Manager principal stays stable, current/previous majors remain supported through maximum horizon, then schemas/indexes migrate and pointers cut over before removal.
- AD-25/26/28/29: preserve Cell/job ownership, disable launch during recovery, require registered immutable ownership, and use `RESERVED → PUBLISHED → VALIDATED → MATERIALIZED → ENABLED`; only an exact current acknowledgement enables launch.

### Terraform, AWS, queue, and runtime rules

- Terraform roots/modules require `>= 1.10, < 2.0`; validate with pinned Terraform 1.15.8/AWS provider 6.54.0. Preserve addresses; document moved/import/state order and expected plan effects for unavoidable changes.
- Keep encrypted/versioned path-isolated state and native S3 locks. No cross-repository remote state, provisioners, `null_resource`, committed state/plans, secrets, mutable Actions/workflows/modules/images, broad IAM, or public exposure.
- Preserve deterministic occurrence/reducer semantics, exactly-one task attempt, conservative ECS retry deadline, canonical replay ingress, encrypted standard queues, partial-batch handling, bounded redrive, and compatibility with both supported majors.
- Fargate/Lambda patching is an explicit managed-runtime exception: record observed versions in Deployment Identity/evidence and qualify after runtime changes.

### Expected files and integration map

- Contracts/fixtures: `contracts/v1/schemas/`, `contracts/v1/fixtures/`, `contracts/v1/catalogs/compatibility.json`, `contracts/v1/catalogs/lifecycle.json`, `contracts/manifest.json`, `contracts/releases/`, `contracts/migrations/`.
- Logic: `scripts/` beside release, deployment, policy, trusted-plan, lifecycle, target, and evidence helpers.
- Orchestration: existing production plan/apply/recovery workflows; add a dedicated protected migration workflow only if existing boundaries cannot express phases.
- Documentation: `docs/runbooks/`; tests: `tests/contract/` and runtime suites with local schema registry and stable rejection codes.

### Previous story intelligence

- Story 3.7 provides migration class, component/schema ranges, tested matrix, qualification observations, runtime exceptions, provenance, provider-lock binding, and consumer compatibility. Consume these fields and add migration-specific readiness/horizon semantics.
- Stories 3.5/3.6 found stale-plan reuse, self-asserted provenance, incomplete artifact handoffs, weak terminal evidence, and missing negative tests. Bind every migration input independently and test workflow boundaries.
- `scripts/validate.py::migration_check` detects Terraform address churn but does not prove consumer/state migration; extend without weakening it. Existing lifecycle checks remain authoritative for unknown/active references and horizons.

### Scope boundary

This story owns compatibility migration, inventory, horizons, expand/migrate/cutover/rollback, readiness, qualification, and evidence. It does not publish releases (3.7), deprecate/remove versions (3.9), perform lifecycle deletion (1.15), or independently authorize Epic 4 production activation.

### Testing and validation

Use uv 0.11.29, Python 3.14.6, Terraform 1.15.8, AWS provider 6.54.0, Ruff, mypy, pytest, JSON Schema, and Checkov.

```bash
PATH=/private/tmp/demo-bmad-uv-01129:$PATH UV_CACHE_DIR=/private/tmp/demo-bmad-uv-cache uv run --locked pytest tests runtime -q -p no:cacheprovider
PATH=/private/tmp/demo-bmad-uv-01129:$PATH UV_CACHE_DIR=/private/tmp/demo-bmad-uv-cache ./scripts/validate.sh
git diff --check
```

If Terraform Registry or PyPI DNS is required, use nameserver `192.168.1.1` and distinguish network/toolchain failures from code failures. Do not use live AWS credentials, state, production Environments, binary plans, raw CONFIG, or secrets.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-3.8-Migrate-Compatible-Platform-Versions`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-18`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-23`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-24`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-29`]
- [Source: `contracts/v1/catalogs/compatibility.json`]
- [Source: `contracts/v1/catalogs/lifecycle.json`]
- [Source: `contracts/migrations/v1.0.0.md`]
- [Source: `_bmad-output/implementation-artifacts/3-7-publish-immutable-platform-releases.md`]
- [Source: `_bmad-output/implementation-artifacts/3-6-record-deployment-and-rollback-evidence.md`]
- [Source: `_bmad-output/project-context.md`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story derived from Epic 3.8, architecture AD-18/20/22/23/24/25/26/28/29, Compatibility Package, Stories 3.5-3.7, project standards, and migration/recovery boundaries.
- Implemented RFC8785-bound migration manifests, explicit consumer/inventory scope, horizon calculation, component compatibility, readiness/cutover/rollback gates, strict schemas, deterministic fixtures, a protected migration workflow, and the migration runbook.
- Validation passed: 307 tests, 269 subtests, Terraform validation, Ruff, mypy, Checkov (1,012 checks), and repository hygiene.
- Code-review patches applied: phase execution evidence, immutable release bindings, authoritative inventory, protected sequencing/plan/rollback gates, complete retained evidence, locked workflow dependencies, Terraform ownership controls, and executable migration fixtures.
- Post-review validation passed: 310 tests, 270 subtests, Ruff, mypy, workflow YAML parsing, workflow policy, Terraform formatting, Checkov (1,012 checks), repository hygiene, and `git diff --check`. Full repository validation completed without AWS credentials, plans, state, or deployment artifacts.
- Second code-review patch set applied: bounded snapshot executor, durable phase-state and predecessor bindings, target-bound plan and release compatibility checks, catalog-backed ownership, schema-routed acknowledgements, rollback evidence derivation, executable snapshot tests, and reconciled release metadata.

### File List

- `_bmad-output/implementation-artifacts/3-8-migrate-compatible-platform-versions.md`
- `.github/workflows/migrate-platform-release.yml`
- `contracts/manifest.json`
- `contracts/releases/1.0.0.json`
- `contracts/v1/fixtures/migration/cases.json`
- `contracts/v1/schemas/migration-acknowledgement.schema.json`
- `contracts/v1/schemas/migration-manifest.schema.json`
- `docs/runbooks/platform-version-migration.md`
- `scripts/migration_contract.py`
- `scripts/validate.py`
- `tests/contract/test_contract_schemas.py`
- `tests/contract/test_migration_contract.py`

### Change Log

- 2026-07-30: Created comprehensive Story 3.8 context and marked it ready for development.
- 2026-07-30: Implemented migration contracts, protected workflow gates, fixtures, tests, and runbook; moved story to review.

### Review Findings

- [x] [Review][Patch] Implement the expand/migrate/cutover/rollback operations and their verified handoffs; the workflow now requires verified phase evidence and predecessor evidence [.github/workflows/migrate-platform-release.yml:37-91].
- [x] [Review][Patch] Bind migration source and target identities to immutable release manifests and raw-byte checksums; workflow inputs are independently validated [.github/workflows/migrate-platform-release.yml:48-54].
- [x] [Review][Patch] Make inventory validation fail closed and cross-check inventory consumers against readiness rows [scripts/migration_contract.py:118-126,183-199].
- [x] [Review][Patch] Enforce schema, release-order, phase/owner/type, and launch-disabled validation for every phase [scripts/migration_contract.py:229-279].
- [x] [Review][Patch] Add predecessor-phase sequencing and fresh trusted-plan/approval bindings [scripts/migration_contract.py:282-319].
- [x] [Review][Patch] Require verified rollback evidence and known-good release identity before rollback [scripts/migration_contract.py:312-319].
- [x] [Review][Patch] Require attributable fresh cutover acknowledgement and unexpired plan evidence [scripts/migration_contract.py:282-309].
- [x] [Review][Patch] Emit complete retained evidence with a 90-day retention ceiling [.github/workflows/migrate-platform-release.yml:67-91].
- [x] [Review][Patch] Replace placeholder migration cases with executable fixture coverage for partial migration, state drift, sequencing, and rollback [contracts/v1/fixtures/migration/cases.json].
- [x] [Review][Patch] Install the locked UV environment before migration validation and tests [.github/workflows/migrate-platform-release.yml:33-66].
- [x] [Review][Patch] Add explicit Terraform/state and ownership evidence requirements to the migration contract and runbook [scripts/migration_contract.py; docs/runbooks/platform-version-migration.md].

### Review Findings (rerun 2026-07-30)

- [x] [Review][Patch][High] Execute bounded expand/migrate/cutover/verification/rollback qualification through the migration executor, protected inputs, and retained evidence [.github/workflows/migrate-platform-release.yml:49-164; scripts/migration_executor.py].
- [x] [Review][Patch][High] Make phase evidence authoritative and operation-bound: the executor derives observations and the contract binds release checksums, schema/access/reducer/launch invariants, and non-empty operation/checkpoint IDs [scripts/migration_executor.py; scripts/migration_contract.py:345-390].
- [x] [Review][Patch][High] Bind predecessor evidence to manifest checksum, operation identity, and monotonic phase state [scripts/migration_contract.py:377-419; .github/workflows/migrate-platform-release.yml:112-114].
- [x] [Review][Patch][High] Bind plan evidence to migration ID, target checksum, source commit, expiry, and state migration evidence [scripts/migration_contract.py:413-438].
- [x] [Review][Patch][High] Resolve ownership identities from the migration catalog and require previous-major support plus fresh launch-disabled observations [scripts/migration_contract.py:438-466; contracts/v1/catalogs/migration.json].
- [x] [Review][Patch][High] Bind release manifests to the checked-out source commit and derive component/schema ranges from the target release [.github/workflows/migrate-platform-release.yml:96-113].
- [x] [Review][Patch][High] Derive rollback compatibility from rollback evidence instead of a constant and require validated source/target snapshots and launch-disabled state [.github/workflows/migrate-platform-release.yml:132-140; scripts/migration_executor.py].
- [x] [Review][Patch][Medium] Enforce non-empty checkpoints and temporal ordering/freshness for phase and acknowledgement evidence [scripts/migration_contract.py:335-390].
- [x] [Review][Patch][Medium] Validate state-migration evidence before publication for every phase [.github/workflows/migrate-platform-release.yml:124-131].
- [x] [Review][Patch][Medium] Route acknowledgements through the normative JSON Schema before custom cutover checks [scripts/migration_contract.py:304-342; contracts/v1/schemas/migration-acknowledgement.schema.json].
- [x] [Review][Patch][Medium] Add executable migration snapshot fixtures and assertions [scripts/migration_executor.py; tests/contract/test_migration_contract.py].
- [x] [Review][Patch][Medium] Add the migration catalog and fixture suite to release metadata and the top-level contract manifest [contracts/v1/catalogs/migration.json; contracts/releases/1.0.0.json; contracts/manifest.json].
