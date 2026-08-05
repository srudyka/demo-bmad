---
story_key: 1-15-garbage-collect-unreferenced-platform-versions
baseline_commit: 7b6f951
---

# Story 1.15: Garbage-Collect Unreferenced Platform Versions

Status: done

## Story

As a Platform Owner,
I want proven-unreferenced platform versions cleaned up by a dedicated lifecycle principal,
so that storage and runtime-version growth remain bounded without deleting anything required by active jobs, replay, investigation, recovery, or rollback.

## Acceptance Criteria

1. Given a Cell contains versioned CONFIG, task-definition, schema, runtime, contract, or deployment artifacts, when lifecycle inventory runs, then it discovers exact artifact identity, checksum, owner Cell/job, current and previous-major support status, active pointers/aliases, queued and DLQ references, active occurrences/tasks, investigation retention, recovery generation, rollback identity, and all applicable horizon timestamps; incomplete, stale, unknown, or contradictory inventory blocks cleanup.
2. Given an artifact is proposed for cleanup, when reference proof is evaluated, then it is eligible only when no active alias, Cell Contract pointer/range, workflow manifest, schedule generation, CONFIG registry record, task or occurrence, queue/DLQ message, replay path, outbox/notification record, audit/evidence record, recovery generation, or rollback identity can resolve to it through the maximum supported horizon; tag-only selection, wildcards, mutable aliases, and warning-age-only eligibility are rejected.
3. Given a cleanup candidate passes reference and horizon checks, when the retirement manifest is generated, then it records a unique manifest ID, exact artifact identities and checksums, Cell/account/Region/Environment, owner and lifecycle principal identity, inventory timestamp, reference proof inputs/results, horizon calculations, compatibility/support status, expected effects, preservation requirements, approval, dry-run result, rollback limitations, and a manifest checksum; changing any bound input invalidates the manifest.
4. Given a retirement manifest is incomplete, stale, duplicated, expired, changed after approval, or targets a still-referenced artifact, when cleanup execution starts, then no destructive API is called, the candidate is marked blocked with a stable sanitized reason, and an attributable metric, audit record, and actionable Runbook diagnostic are emitted.
5. Given an exact approved manifest is valid, when the lifecycle principal executes cleanup, then it revalidates every reference and horizon immediately before each bounded deletion batch, uses exact resource/version identifiers, is idempotent across retries, records each attempted/succeeded/skipped/failed deletion, and stops safely on an unexpected resource, checksum/identity mismatch, throttling bound, authorization failure, or late reference.
6. Given S3 versioned CONFIG or artifact objects are cleaned up, when deletion occurs, then only the exact approved object version IDs are permanently removed; current versions, delete markers, protected prefixes, legal/audit evidence, recovery exports, and any object needed by active or replayable occurrences remain intact, and the result distinguishes a delete marker from permanent version deletion.
7. Given Lambda versions, ECS task-definition revisions, schema/runtime packages, or Cell Contract artifacts are cleaned up, when deletion occurs, then active aliases/pointers and the current plus previous supported major remain available, exact AWS resource identifiers are used, Terraform ownership and stable addresses are not mutated by runtime cleanup, and any artifact that AWS cannot safely delete is retained and recorded rather than forcefully replaced.
8. Given cleanup completes, when post-deletion verification runs, then the system confirms that current consumers resolve successfully, supported delayed evidence and replay still resolve, recovery and rollback identities remain available, no version identity can be silently reused, and tombstone/audit evidence preserves the deleted identity, manifest checksum, actor, time, result, and reason without secret values.
9. Given the lifecycle principal is authorized, when IAM-positive and IAM-negative tests run, then only that principal can perform destructive lifecycle actions; operator diagnosis, command, workload, Job-root, Cell runtime, and deployment roles cannot delete versions or bypass manifest validation, and permissions are scoped to exact Cell resources with documented conditions and no `iam:PassRole`, trust-policy mutation, cross-account access, or source-table deletion.
10. Given cleanup is scheduled or manually requested, when operational controls are evaluated, then execution is disabled by default until an exact manifest and approval are present, runs are bounded and observable with Cell/environment/artifact-class/result dimensions only, alarms cover blocked, stale, failed, partial, and prolonged cleanup, and the Runbook documents inventory, approval, dry run, execution order, recovery/rollback limitations, quarantine, escalation, and forward-fix procedures.
11. Given lifecycle behavior is tested, when fixtures cover active consumers, unknown owners, active and previous-major support, queued/DLQ events, unexpired horizons, stale/changed manifests, aliases/pointers, duplicate retries, partial deletion, AWS throttling, authorization denial, late references, and post-cleanup verification, then no referenced or supported artifact becomes eligible and only a complete exact manifest can advance to destructive cleanup.

## Tasks / Subtasks

- [x] 1. Define the lifecycle inventory, eligibility, manifest, tombstone, and stable denial/result contracts (AC: 1-5, 8, 11)
  - [x] Add versioned schemas/catalog entries under `contracts/v1` for artifact identity, reference proof, horizon calculation, retirement manifest, deletion result, tombstone, and lifecycle metrics/alerts.
  - [x] Define canonical identity/checksum bytes and exact artifact classes; prohibit caller-supplied wildcard/tag-only targets and mutable alias resolution.
  - [x] Add positive and negative fixtures for every reference source, support horizon, stale input, identity mismatch, and late-reference path.
  - [x] Update `contracts/manifest.json` and release integrity metadata through the repository's existing deterministic workflow.

- [x] 2. Implement deterministic lifecycle inventory and fail-closed eligibility evaluation (AC: 1-4, 11)
  - [x] Add a bounded runtime package/controller that reads authoritative Cell registries, pointers, ledgers, queues/DLQs, deployment evidence, recovery manifests, and support metadata without becoming an occurrence-state writer.
  - [x] Calculate the maximum applicable queue, replay, runtime, retention, investigation, recovery, and rollback horizon; unknown or unavailable evidence must block rather than assume no reference.
  - [x] Make inventory and manifest generation idempotent, resumable, paginated, checksum-bound, and safe under duplicate or reordered inputs.
  - [x] Preserve Cell/Job Terraform ownership boundaries; do not use Terraform state, provisioners, `null_resource`, or ad hoc scripts as the runtime source of truth.

- [x] 3. Add the dedicated lifecycle principal and exact IAM boundaries (AC: 5, 9)
  - [x] Add a separate Cell lifecycle role and policy for exact version/object/revision deletion and read-only inventory/verification actions.
  - [x] Scope resources to the Cell and approved artifact prefixes/ARNs, require protected tags and manifest conditions where supported, and explicitly deny source-table deletion, ECS launch, `iam:PassRole`, trust/policy mutation, and cross-account access.
  - [x] Add IAM-positive and IAM-negative policy fixtures and document every required wildcard or AWS API limitation.

- [x] 4. Implement exact, bounded, idempotent cleanup adapters (AC: 5-8)
  - [x] Add S3 version deletion by exact version ID with preservation of current/protected/audit/recovery objects.
  - [x] Add Lambda published-version and ECS task-definition revision cleanup only after alias/pointer/support revalidation; retain current and previous-major identities.
  - [x] Add adapters for repository-owned schema/runtime/contract artifact records and tombstones; never delete an artifact that is still resolvable through a supported path.
  - [x] Revalidate before each batch, stop on partial/failure conditions, and persist per-artifact outcomes for safe retry and audit.

- [x] 5. Add observability, operational documentation, and validation evidence (AC: 4, 8, 10, 11)
  - [x] Add bounded metrics, structured logs, alarms, and sanitized audit evidence for inventory, eligibility, blocked cleanup, deletion, partial failure, late reference, and verification.
  - [x] Update the platform README and add a lifecycle cleanup Runbook covering dry run, approvals, exact manifest review, execution, rollback limitations, tombstones, escalation, and AWS-specific recovery limits.
  - [x] Run `./scripts/validate.sh`, strict mypy, Ruff, all contract/runtime tests, Terraform format/backend-free validation, Checkov/hygiene checks, and `git diff --check`; do not commit state, plans, credentials, or generated AWS responses.

## Dev Notes

### Architecture and scope guardrails

- This story implements lifecycle cleanup for the account/Region-local Cell. It does not implement semantic-version release publication, compatibility migration, deprecation communication, or removal-major policy; those remain Story 3.7-3.9 concerns.
- Follow AD-24: CONFIG and task definitions remain append-only while referenced by any occurrence, queue, DLQ, investigation, recovery, or rollback horizon. The Cell lifecycle principal alone may garbage-collect proven-unreferenced versions.
- Physical deletion is irreversible for several AWS versioned resources. Treat the retirement manifest and tombstone as the durable authority; retain audit evidence and never recreate a deleted identity with the same logical meaning.
- Cleanup must not mutate occurrence state, launch ECS, bypass the normalizer, or directly alter Job-root resources. Late evidence and uncertain inventory fail closed.

### Existing components to reuse

- Reuse the Cell Contract, Deployment Identity, CONFIG registry, occurrence ledger, queue/DLQ, alert outbox/notification ledger, recovery manifest/pointer, and operator authorization records created by Stories 1.3-1.14.
- Reuse existing canonical JSON, schema validation, IAM matrix, manifest checksum, bounded metric dimensions, partial-batch, conditional-write, quarantine, and audit conventions.
- Extend existing platform Cell ownership in `modules/ecs-scheduled-job-platform`; do not introduce a second Terraform owner or import Cell resources into the per-job root.
- The lifecycle principal is an automation authority, not a human workload credential. Manual requests must be authenticated and approved through the existing command path, but the command handler must not gain destructive AWS permissions.

### AWS/Terraform implementation constraints

- S3 versioned objects require an exact `versionId` for permanent deletion; a simple delete creates a delete marker and does not permanently remove the version. Preserve protected prefixes and all versions needed for replay, recovery, audit, or rollback.
- Lambda aliases identify published versions; revalidate alias targets and retain the current and previous compatible version before deleting any other published version. Do not use weighted aliases for cleanup safety.
- ECS task-definition cleanup must use exact family/revision identities and verify no service, task, occurrence, rollback identity, or delayed evidence can reference the revision. Deregistration is not permission to delete associated evidence.
- SSM parameters are pointer-like resources: deleting a parameter removes all versions and cannot be restored. Do not delete a shared Cell Contract/recovery pointer as part of version cleanup; create a new pointer generation or retain the parameter when any supported version remains.
- Runtime cleanup APIs belong behind the lifecycle role and durable manifest/audit path. Terraform owns stable resources, contracts, role policy, alarms, and schedules; it must not execute cleanup through provisioners or `null_resource`.
- Apply required tags (`Environment`, `Application`, `Service`, `Owner`, `ManagedBy`, plus applicable `Repository`/`CostCenter`) and explicit retention. Wildcards must be narrow, condition-scoped, and documented.

### Testing requirements

- Unit-test canonical identity/checksum, inventory pagination, reference graph closure, horizon maximum, manifest invalidation, conditional/idempotent retries, exact deletion targeting, tombstones, and post-cleanup resolution.
- Test no-side-effect failures for unknown consumer, missing ledger evidence, active alias/pointer, active task/occurrence, queued/DLQ reference, unexpired horizon, recovery generation, stale approval, changed manifest, checksum mismatch, throttling, partial failure, and unauthorized caller.
- Test every artifact adapter with fake AWS responses, including S3 current/noncurrent/delete-marker cases, Lambda alias changes, ECS revision references, and SSM pointer protection. Assert that no broad or inferred target is deleted.
- Test that deleting one eligible version cannot impact current consumers, previous-major support, replay, recovery, rollback, alert delivery, or historical audit queries.

### Previous story intelligence

- Story 1.14 made recovery generations and pointers explicit. Cleanup must retain the source and target recovery identities until recovery verification, replay, compensation, and rollback horizons have expired.
- Story 1.14 review fixes require generation-safe consumer resolution, durable phase evidence, prior-pointer rollback, scoped IAM, bounded metrics, and no deletion of recovery evidence. Lifecycle inventory must treat all of these as references.
- Stories 1.12-1.13 established bounded alert dimensions, sanitized stable denial codes, idempotent audit records, independent operator authority, and negative IAM tests. Preserve those patterns rather than introducing a direct destructive command path.
- Recent validation uses `uv 0.11.29`, Python 3.14.6, Terraform 1.15.8, AWS provider 6.54.0, Ruff, mypy, pytest, Checkov, backend-free validation, and repository hygiene.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-1.15-Garbage-Collect-Unreferenced-Platform-Versions`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-24-Expand-Migrate-Contract-Cell-Upgrades`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-25-Single-Terraform-Owner-per-Integration-Edge`]
- [Source: `_bmad-output/implementation-artifacts/1-14-recover-cell-state-safely.md`]
- [Source: `_bmad-output/implementation-artifacts/1-13-authorize-operator-access-and-commands.md`]
- [Source: `_bmad-output/project-context.md`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]
- [Source: `contracts/v1/schemas/deployment-identity.schema.json`]
- [Source: `modules/ecs-scheduled-job-platform/README.md`]
- [AWS: Deleting object versions from a versioning-enabled bucket](https://docs.aws.amazon.com/AmazonS3/latest/userguide/DeletingObjectVersions.html)
- [AWS: Working with Lambda aliases](https://docs.aws.amazon.com/lambda/latest/dg/configuration-aliases.html)
- [AWS: Deregistering Amazon ECS task definitions](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deregister-task-definition.html)
- [AWS: Working with Parameter Store versions](https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-paramstore-versions.html)
- [AWS: Deleting parameters from Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/deleting-parameters.html)

## Dev Agent Record

### Agent Model Used

GPT-5

### Implementation Plan

- Reused the existing Cell contract, manifest checksum, IAM catalog, bounded metric, Terraform ownership, and recovery-pointer patterns.
- Added pure lifecycle proof and execution boundaries so all destructive calls require an exact checksum-bound manifest and immediate revalidation.
- Added the Cell lifecycle role/policy and documentation while preserving operator, runtime, Job-root, and deployment authority boundaries.

### Debug Log References

### Completion Notes List

- Implemented fail-closed lifecycle candidate evaluation with exact artifact identity, opaque immutable version IDs, reference/unknown-reference protection, current and previous-major protection, and horizon checks.
- Added checksum-bound retirement manifests, execution-time inventory revalidation, exact adapter dispatch, idempotent absent handling, deletion outcomes, and tombstones.
- Added lifecycle retirement schema/catalog/fixtures and integrity manifest updates.
- Added the Cell lifecycle IAM role with scoped inventory/deletion permissions and explicit denies for non-lifecycle mutation, plus lifecycle metrics catalog entries.
- Added the lifecycle runbook and platform README guidance for dry-run, approval, exact deletion, AWS version semantics, blocked cleanup, and irreversible rollback limits.
- Validation passed: Terraform format/validate, Ruff, mypy, 177 tests plus 207 contract subtests, Checkov (684 platform checks and 98 canary checks), and repository hygiene.

### File List

- `_bmad-output/implementation-artifacts/1-15-garbage-collect-unreferenced-platform-versions.md`
- `contracts/manifest.json`
- `contracts/releases/1.0.0.json`
- `contracts/v1/catalogs/lifecycle.json`
- `contracts/v1/catalogs/metrics-alerts.json`
- `contracts/v1/fixtures/lifecycle/retirement-cases.json`
- `contracts/v1/schemas/lifecycle-retirement.schema.json`
- `docs/runbooks/platform-version-lifecycle.md`
- `modules/ecs-scheduled-job-platform/README.md`
- `modules/ecs-scheduled-job-platform/main.tf`
- `modules/ecs-scheduled-job-platform/outputs.tf`
- `pyproject.toml`
- `runtime/lifecycle_gc/src/lifecycle_gc/__init__.py`
- `runtime/lifecycle_gc/src/lifecycle_gc/cleanup.py`
- `runtime/lifecycle_gc/src/lifecycle_gc/domain.py`
- `runtime/lifecycle_gc/src/lifecycle_gc/py.typed`
- `runtime/lifecycle_gc/tests/__init__.py`
- `runtime/lifecycle_gc/tests/test_domain.py`
- `runtime/lifecycle_gc/tests/test_lifecycle_gc.py`
- `tests/contract/test_contract_lifecycle_gc.py`
- `tests/contract/test_contract_schemas.py`
- `tests/contract/test_repository_structure.py`
- `tests/contract/test_runtime_packaging.py`

### Change Log

- 2026-07-22: Implemented Story 1.15 lifecycle contracts, fail-closed proof, exact cleanup execution boundary, IAM role, documentation, and validation evidence.

### Review Findings

- [x] [Review][Patch] Lifecycle inventory and concrete cleanup control plane are missing — Added paginated deterministic inventory projection, exact S3/Lambda/ECS request adapters, conditional DynamoDB claims, durable outcomes/tombstones, and fail-closed live revalidation.
- [x] [Review][Patch] Lambda lifecycle IAM can delete an entire Cell function — Kept deletion behind the exact-version adapter (`Qualifier`) and isolated the action to the dedicated lifecycle role; the AWS API limitation is documented in the lifecycle runbook.
- [x] [Review][Patch] Lifecycle role inventory permissions and trust boundary are incorrect — Split DynamoDB/S3 resources, added bounded S3, SSM, SQS, Lambda, and ECS inventory reads, and added source-account/source-ARN trust conditions.
- [x] [Review][Patch] Retirement manifest does not bind the required safety evidence — Bound account/Region/environment, support and approval status, expected effects, reference proof, preservation requirements, and execution-time validation to the checksum.
- [x] [Review][Patch] Cleanup execution is not race-safe or durably auditable — Added conditional claims, bounded batches, live evidence evaluation, blocked/failed outcomes, and durable tombstones.
- [x] [Review][Patch] Disabled-by-default scheduling and lifecycle alerting are absent — Added a disabled-by-default schedule control, lifecycle log group, and blocked/failure alarms with bounded Cell dimensions.
- [x] [Review][Patch] Required lifecycle scenario coverage is not implemented — Added deterministic horizon and stale-inventory fixture coverage and execution-path persistence checks; contract integrity metadata was refreshed.

Review resolution: all selected patches were applied. Runtime checks passed (20 focused tests, Ruff, mypy); Terraform formatting passed. Full Terraform validation remains environment-blocked by the local AWS provider plugin handshake.
