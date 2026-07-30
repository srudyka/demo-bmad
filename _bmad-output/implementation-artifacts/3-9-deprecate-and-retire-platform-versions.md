---
epic: 3
story: 3.9
title: Deprecate and Retire Platform Versions
status: done
baseline_commit: d9b286cdd339036d1253e989dfbaa511500176e5
---

# Story 3.9: Deprecate and Retire Platform Versions

## Story

As a Platform Owner,
I want deprecated platform versions retired only after consumers and recovery horizons are clear,
so that support obligations end predictably without breaking active or replayable jobs.

## Acceptance Criteria

1. **Deprecation is additive and attributable.** A backward-compatible release that deprecates an input, output, workflow, schema, runtime, policy, or behavior publishes release notes and machine-readable metadata naming the replacement, warning behavior, affected consumers, migration steps, support status, earliest removal major, owner, and review date. It neither changes existing behavior nor removes compatibility in that release.
2. **Support status honors compatibility.** The current and previous major remain supported through the documented maximum compatibility horizon. A security-emergency deviation records the risk, compensating control, migration path, approvers, and exact end date.
3. **Retirement inventory fails closed.** Before removal, inventory finds every Cell, job, repository, CONFIG, schedule generation, workflow, runtime, queue/DLQ event, rollback identity, owner, and last observed use. Unknown ownership, missing telemetry, or unresolved references block retirement.
4. **Notices are complete and tracked.** GitHub release and internal-engineering notices state version, impact, action, migration guide, deadline, support contact, and rollback guidance. Track acknowledgement and unresolved exceptions without secrets or sensitive deployment data.
5. **Removal requires evidence beyond time elapsed.** Production policy requires the documented major, completed migration evidence, expired support/replay/retention/rollback horizons, no active reference, and reviewed destructive-plan impact. A warning period alone never proves safety.
6. **The retirement manifest is exact and immutable.** Generation binds exact artifact identities and raw-byte checksums, consumer inventory, reference proofs, horizon calculation, approvals, expected effects, preservation evidence, and rollback limitations. Wildcards, tag-only selection, and mutable aliases are rejected.
7. **Only the lifecycle principal deletes.** With an approved retirement manifest, protected fresh-plan changes stop active aliases, Cell Contract ranges, workflow manifests, documentation, and support metadata from advertising the retired version. Physical deletion is delegated only to Story 1.15's lifecycle principal with that exact manifest.
8. **Late references invalidate retirement.** A pre-deletion recheck that finds an incompatible consumer or late reference invalidates the manifest, updates support status and communications, preserves the artifact, and fails launch for unsupported configuration closed with actionable migration guidance.
9. **Post-cleanup remains recoverable and unambiguous.** After physical cleanup, verify current consumers, previous-major support, delayed evidence handling, rollback identities, documentation, monitoring, and canary operation. Tombstones and audit evidence prevent silent reuse and historical ambiguity.
10. **Qualification is deterministic.** Fixtures cover active consumers, unknown owners, delayed DLQ events, unexpired horizons, stale manifests, changed aliases, emergency deprecation, safe retirement, and post-cleanup validation. No referenced or supported artifact may become eligible; only a complete exact manifest may advance to lifecycle cleanup.

## Tasks / Subtasks

- [x] Define deprecation, support-policy, notice, exception, and retirement-handoff contracts (AC: 1, 2, 4-6)
  - [x] Extend the normative Compatibility Package with strict local JSON Schemas/catalog entries and stable secret-safe `TargetViolation`/lifecycle rejection codes; update `contracts/manifest.json` and the immutable release snapshot checksums in the same change.
  - [x] Reuse Story 3.7's release manifest/provenance and Story 3.8's consumer inventory/horizon format; do not create another SemVer, canonicalization, checksum, release registry, or evidence format.
  - [x] Define security-emergency records that require risk, compensating control, migration path, approvers, and an expiry/review timestamp; never treat the exception as a permanent removal authorization.
- [x] Implement complete retirement inventory and support-status evaluation (AC: 2, 3, 5, 8)
  - [x] Project every required consumer/reference source from checked-in fixture evidence: Cell/job/repository, ownership generation, CONFIG, schedule generation, workflow/runtime, queues/DLQs, occurrences/task attempts, aliases/pointers, rollback identity, documentation/support metadata, owner, and last observed use.
  - [x] Fail closed for empty/unknown owners, incomplete telemetry, unresolved references, stale observations, wildcard/mutable identity, incomplete horizon evidence, current or previous-supported-major versions, and migration evidence that is absent, stale, or checksum-mismatched.
  - [x] Calculate and retain the maximum support/replay/retention/investigation/recovery/rollback horizon from the Story 3.8 manifest; present a machine-readable decision and migration guidance before any side effect.
- [x] Bind retirement to immutable releases, migration evidence, policy, and exact lifecycle manifests (AC: 5-7)
  - [x] Extend, rather than bypass, `runtime/lifecycle_gc` proof/manifest/execution gates. Map an approved deprecation decision to `unsupported-candidate` only when every release, inventory, ownership, horizon, plan, approval, and reference binding is current and exact.
  - [x] Require fresh reviewed destructive-plan evidence, protected approval, exact source commit/release checksums, and an explicit lifecycle-principal handoff. The deprecation workflow may never invoke AWS deletion adapters or grant lifecycle permissions to a deployment, operator, workflow, runtime, or Job-root role.
  - [x] Ensure lifecycle revalidation treats changed aliases/ranges/manifests, a late reference, or stale manifest as a block; retain audit/recovery/tombstone data and invalidate—not amend—the old manifest.
- [x] Implement protected communication and advertisement withdrawal (AC: 1, 4, 7-9)
  - [x] Generate sanitized GitHub-release/internal-engineering notice payloads, acknowledgement/exception records, support contact, deadline, migration/rollback links, and review status without CONFIG, state, credentials, raw plans, task ARNs, or sensitive deployment data.
  - [x] Use protected fresh-plan changes to remove only the deprecated version from aliases, Cell Contract ranges/pointers, workflow manifests, support metadata, docs, and release advertising; preserve prior artifacts and rollback identity until lifecycle cleanup succeeds.
  - [x] On blocked/invalidation outcomes, restore/retain supported advertising as applicable, update notice/support status, disable unsupported launch through existing compatibility checks, and emit bounded observability for decision, stale manifest, late reference, exception expiry, handoff, and post-cleanup verification.
- [x] Add deterministic contract, runtime, workflow, and policy qualification (AC: 1-10)
  - [x] Add positive and negative fixtures for every required retirement condition, including active consumers, unknown owners, delayed DLQ, unexpired horizons, stale/changed manifest or alias, emergency exception, safe handoff, lifecycle late-reference rejection, and post-cleanup tombstone verification.
  - [x] Assert no physical-delete adapter is reachable outside `lifecycle-garbage-collection`; assert exact raw-byte checksum, expiry, approval, source release/migration, inventory, and fresh-plan bindings on the handoff.
  - [x] Test both supported and unsupported configuration before side effects, existing current/previous-major interoperability, notice sanitization, exception expiry, and post-retirement delayed replay/recovery behavior with no AWS session.
- [x] Document the deprecation-to-cleanup operating procedure (AC: 1, 4-9)
  - [x] Update Compatibility Package and lifecycle/migration runbooks with release classification, notice channels, support horizon, inventory/review, exception process, fresh-plan advertisement withdrawal, lifecycle handoff, blocked cleanup, verification, observability, and irreversible-deletion rollback limitations.
  - [x] State the authority boundary plainly: Story 3.9 decides and hands off retirement; Story 1.15's dedicated lifecycle principal alone performs exact physical deletion.

### Review Findings

- [x] [Review][Patch] Require retirement handoffs at the lifecycle execution boundary [`runtime/lifecycle_gc/src/lifecycle_gc/cleanup.py`] — direct raw-manifest execution now fails closed; only the full handoff executor reaches an adapter.
- [x] [Review][Patch] Bind retirement to verified migration completion, trusted plan policy, and protected approval [`scripts/deprecation_contract.py`] — the validator checks immutable cutover evidence, acknowledgement, fresh policy decision, and independently authorized approval cross-bindings.
- [x] [Review][Patch] Replace caller-asserted retirement inventory with complete immutable evidence [`scripts/deprecation_contract.py`] — a checksum-bound inventory projects every required source, owner, observation, reference, and horizon.
- [x] [Review][Patch] Bind the retired artifact and support status to immutable releases [`scripts/deprecation_contract.py`] — source-release artifact checksums and package current/previous-major policy are derived and enforced before lifecycle eligibility.
- [x] [Review][Patch] Integrate retirement into a protected operational path [`.github/workflows/retire-platform-version.yml`] — a full-SHA protected workflow validates withdrawal and publishes only a lifecycle handoff envelope; it never deletes.
- [x] [Review][Patch] Reject sensitive notice values, not only sensitive key names [`scripts/deprecation_contract.py`] — notice values now pass the common secret-safety screen.
- [x] [Review][Patch] Enforce independently authorized emergency approvers [`scripts/deprecation_contract.py`] — duplicates and owner/self-approval are rejected.
- [x] [Review][Patch] Make retirement fixture scenarios executable [`contracts/v1/fixtures/deprecation/cases.json`] — each declared scenario is marked executable and driven by parameterized validator/executor coverage.

### Review Findings — Rerun 2026-07-30

- [x] [Review][Patch][Critical] Bind the lifecycle-manifest artifact to the inventory artifact and retirement-evidence digest [`scripts/deprecation_contract.py`, `runtime/lifecycle_gc/src/lifecycle_gc/cleanup.py`] — exact artifact equality and the artifact identity in the evidence digest prevent a recomputed handoff from proving artifact A while delegating artifact B.
- [x] [Review][Patch][High] Make an `active` record in every retirement-inventory source block eligibility [`scripts/deprecation_contract.py`] — active source records now fail closed independently of the summary reference list.
- [x] [Review][Patch][High] Require per-source collection completeness and zero-result evidence [`scripts/deprecation_contract.py`] — every source now provides a query ID, timestamp, completion assertion, result count, and records list.
- [x] [Review][Decision][High] Use the repository's existing protected production-approval evidence as the authoritative approval source; do not add a GitHub API review lookup in this story.
- [x] [Review][Decision][High] Bind the next provenance integration to checked-in immutable Compatibility Package artifacts; do not introduce an external signed-artifact service in this story.
- [x] [Review][Patch][High] Require complete `ReferenceEvidence` from late revalidation [`runtime/lifecycle_gc/src/lifecycle_gc/cleanup.py`] — boolean callback results are rejected before an adapter can be reached.
- [x] [Review][Patch][High] Provision the locked Python toolchain in the protected retirement workflow [`.github/workflows/retire-platform-version.yml`] — the workflow installs uv 0.11.29 and uses `uv sync/run --locked`.
- [x] [Review][Patch][High] Publish the complete checksum-verified lifecycle handoff [`.github/workflows/retire-platform-version.yml`] — the protected workflow publishes the raw full handoff and an envelope binding source/workflow/logical/raw-file checksums.
- [x] [Review][Patch][High] Enforce `earliest_removal_major` before retirement [`scripts/deprecation_contract.py`] — retirement now fails closed until the authoritative package major reaches the recorded threshold.
- [x] [Review][Decision][Medium] Verify protected committed-state changes and immutable release evidence for notices and advertising withdrawal; do not integrate external notification/API receipts in this story.

#### Decisions Recorded — 2026-07-30

- Protected approval: reuse the repository's existing protected production-approval evidence rather than introduce a GitHub API review lookup.
- Release, migration, and policy provenance: bind validation to checked-in immutable Compatibility Package artifacts rather than an external signed-artifact service.
- Notice and advertisement withdrawal: verify protected committed-state changes and immutable release evidence rather than integrate external notification/API receipts.

### Review Findings — Parallel rerun 2026-07-30

- [x] [Review][Decision] Define the maximum age and ordering of retirement evidence — one-hour freshness and chronological evidence ordering are enforced.
- [x] [Review][Decision] Define the lifecycle invalidation integration for changed aliases, ranges, and manifests — typed durable invalidation records require completed support, communications, and launch-blocking remediation.
- [x] [Review][Decision] Define the post-cleanup verification boundary — a typed verifier persists all checks and terminal outcomes.
- [x] [Review][Patch] Decouple the handoff sealing commit from immutable release provenance [`.github/workflows/retire-platform-version.yml`, `scripts/deprecation_contract.py`] — protected submission provenance is validated independently of release provenance.
- [x] [Review][Patch] Make the protected workflow import the lifecycle runtime [`.github/workflows/retire-platform-version.yml`] — the workflow configures the lifecycle source root.
- [x] [Review][Patch] Bind lifecycle execution to verified protected approval and submission evidence [`runtime/lifecycle_gc/src/lifecycle_gc/cleanup.py`, `scripts/deprecation_contract.py`, `.github/workflows/retire-platform-version.yml`] — execution retrieves the envelope and raw handoff from a lifecycle-owned evidence store and cross-binds protected approval.
- [x] [Review][Patch] Reject future individual approver timestamps [`scripts/deprecation_contract.py`] — approver freshness is bounded and ordered.
- [x] [Review][Patch] Bind release artifacts to the full exact lifecycle identity [`scripts/deprecation_contract.py`] — kind, checksum, and complete immutable identity must match.
- [x] [Review][Patch] Persist and validate immutable deprecation notice, acknowledgement, and exception evidence [`contracts/v1/schemas/deprecation-record.schema.json`, `scripts/deprecation_contract.py`] — immutable evidence references and raw-byte digest verification are required.
- [x] [Review][Patch] Execute deprecation fixtures rather than only asserting their labels [`contracts/v1/fixtures/deprecation/cases.json`, `tests/contract/test_deprecation_contract.py`] — fixtures now execute late-reference and post-cleanup failure/incomplete paths.

#### Decisions Recorded — Parallel rerun 2026-07-30

- Freshness: require one-hour maximum evidence age and chronological ordering from inventory through plan/policy, approval, and withdrawal.
- Late invalidation: persist typed live-surface-digest invalidation outcomes for the existing support/launch handlers; do not create a lifecycle-triggered workflow.
- Post-cleanup verification: require a typed verifier callback and persist its durable result; do not create an asynchronous verification workflow.

### Review Findings — Parallel follow-up 2026-07-30

- [x] [Review][Patch] Align the normative lifecycle schema with generated retirement manifests [`contracts/v1/schemas/lifecycle-retirement.schema.json`] — generation and schema now require the evidence digest and all three surface digests.
- [x] [Review][Patch] Bind retirement horizons to the validated Story 3.8 migration manifest [`scripts/deprecation_contract.py`] — inventory horizons must cover the authoritative migration cutoff.
- [x] [Review][Patch] Require authoritative protected-submission evidence at lifecycle execution [`runtime/lifecycle_gc/src/lifecycle_gc/cleanup.py`] — lifecycle-owned evidence storage supplies the raw submission and notice evidence before any adapter is reachable.
- [x] [Review][Patch] Parse protected-workflow handoffs with a strict JSON loader [`.github/workflows/retire-platform-version.yml`] — duplicate keys and non-finite values are rejected before validation.
- [x] [Review][Patch] Bind immutable notice, acknowledgement, and unresolved-exception evidence [`contracts/v1/schemas/deprecation-record.schema.json`] — each required artifact is fetched and raw-byte hash verified.
- [x] [Review][Patch] Route late surface invalidation to the recorded support and launch handlers [`runtime/lifecycle_gc/src/lifecycle_gc/cleanup.py`] — incomplete handler remediation blocks retirement and is durably recorded.
- [x] [Review][Patch] Persist complete post-cleanup verification and handle verifier failures [`runtime/lifecycle_gc/src/lifecycle_gc/cleanup.py`] — prior-major replay is included and failures persist `POST_DELETE_BLOCKED`.
- [x] [Review][Patch] Execute declared deprecation fixture data [`contracts/v1/fixtures/deprecation/cases.json`] — post-cleanup failure/incomplete scenarios run through the executor.

### Review Findings — Final remediation 2026-07-30

- [x] [Review][Patch] Preserve a durable pre-delete intent for reconciliation [`runtime/lifecycle_gc/src/lifecycle_gc/cleanup.py`] — an external deletion followed by an audit/tombstone write failure raises `LIFECYCLE_DELETE_RECONCILIATION_REQUIRED` while retaining the exact intent.
- [x] [Review][Patch] Replace blanket type suppression with narrowed JSON boundaries [`scripts/deprecation_contract.py`] — mypy passes without file-wide disabled error codes.

## Dev Notes

### Required reuse and invariants

- `contracts/` remains the normative local Compatibility Package. Use strict UTF-8/local schema validation, RFC8785/JCS canonical bytes, existing raw-byte integrity manifest/release snapshot conventions, and stable rejection codes.
- Reuse `scripts/release_manifest.py` for immutable release identity and affected/corrected release records; `scripts/migration_contract.py` and `scripts/migration_executor.py` for inventory, compatibility horizon, owner/readiness, phase, plan, acknowledgement, and completion evidence; and `scripts/production_policy.py`, `trusted_plan.py`, `production_apply.py`, and `deployment_evidence.py` for reviewed-plan/policy/approval/evidence gates.
- Reuse `runtime/lifecycle_gc` for exact `ArtifactIdentity`, `ReferenceEvidence`, `evaluate_candidate`, checksum-bound retirement manifests, immediate revalidation, bounded execution, outcomes, and tombstones. Do not duplicate lifecycle proof, deletion adapters, DynamoDB claim storage, or `LIFECYCLE_*` semantics.
- Current and previous major are supported for at least the package minimum and longer through any CONFIG, occurrence, queue, DLQ, investigation, recovery, or rollback reference. A release age or notice deadline is never sufficient.
- Physical deletion is non-reversible. Delete only exact opaque version IDs through the lifecycle role after a protected approved manifest. Never delete a shared Cell Contract/recovery parameter, mutate another root, or reuse a tombstoned identity.

### Architecture and AWS guardrails

- AD-17/20/22 require immutable references, credential-free validation, full-SHA Actions, reviewed fresh plans, protected Environment approval, short-lived attributable authority, evidence, safe logs/metrics, security/IAM review, runbook, and rollback/forward-fix guidance.
- AD-23/24 preserve the checked-in Compatibility Package, stable Process Manager principal, two-major coexistence, append-only referenced CONFIG/task definitions, expand/migrate/cutover before delayed removal, and dedicated lifecycle cleanup.
- AD-18/26/29 preserve disabled launch during recovery and only re-enable with exact current acknowledgement. A deprecation failure or late reference must retain compatible identities and use canonical replay/recovery paths.
- Keep Cell and job Terraform ownership separate (AD-25). If Terraform is changed, preserve addresses or provide exact moved/import/ordering/expected-plan/rollback documentation; no provisioners, `null_resource`, state, plans, credentials, broad IAM, public access, or unpinned dependency.
- Lifecycle IAM remains least-privilege and sole destructive authority. Any wildcard must be AWS-required, condition-scoped, catalog-owned, and documented. Do not invent account IDs, regions, notification targets, or production environments.

### Expected files and integration map

- Contracts: `contracts/v1/schemas/`, `contracts/v1/catalogs/`, `contracts/v1/fixtures/`, `contracts/manifest.json`, `contracts/releases/1.0.0.json`, `contracts/README.md`, and the applicable migration note.
- Logic: extend existing `scripts/release_manifest.py`, `scripts/migration_contract.py`, `scripts/production_policy.py`, and lifecycle package modules only where each owns the authoritative boundary. New pure helper modules are acceptable under `scripts/` or `runtime/lifecycle_gc/src/lifecycle_gc/` if existing owners cannot express the contract.
- Workflow: add/extend only a protected, full-SHA GitHub Actions workflow that validates/hands off retirement evidence. No workflow may execute physical cleanup directly.
- Documentation: `docs/runbooks/platform-version-lifecycle.md`, `docs/runbooks/platform-version-migration.md`, and `contracts/README.md`; tests in `tests/contract/` and `runtime/lifecycle_gc/tests/`.

### Previous-story intelligence

- Story 3.8 now has authoritative inventory scope, maximum compatibility horizon, immutable source/target release checksum, ownership resolution, exact acknowledgements, trusted-plan binding, retained phase evidence, and bounded snapshot execution. Consume it; do not downgrade its semantics to a report or make retirement callable before a successful migration.
- Story 3.7 owns immutable release classification, provenance, release notes, affected/corrected versions, internal/GitHub notice channels, and the 30-day rollback evidence horizon. Deprecation metadata must bind to those records rather than a mutable tag or ad hoc notice.
- Story 1.15 already provides the exact cleanup principle, adapters, revalidation, outcomes, tombstones, IAM, and runbook. A retirement handoff is a stronger input gate for that implementation—not a parallel delete service.
- Earlier Epic 3 reviews found stale-plan reuse, self-asserted provenance, incomplete artifact handoffs, weak terminal evidence, and missing negative tests. Independently bind every producer-controlled input and test workflow boundaries with checked-in fixtures.

### Scope boundary

This story governs compatible deprecation, support status, notification, retirement proof, protected advertising withdrawal, and lifecycle handoff. It does not publish a release (3.7), migrate consumers (3.8), delete an artifact itself (1.15), use live AWS credentials, or authorize Epic 4 pilot activation.

### Testing and validation

Use uv 0.11.29, Python 3.14.6, Terraform 1.15.8, AWS provider 6.54.0, Ruff, mypy, pytest, JSON Schema, and Checkov.

```bash
PATH=/private/tmp/demo-bmad-uv-01129:$PATH UV_CACHE_DIR=/private/tmp/demo-bmad-uv-cache uv run --locked pytest tests runtime -q -p no:cacheprovider
PATH=/private/tmp/demo-bmad-uv-01129:$PATH UV_CACHE_DIR=/private/tmp/demo-bmad-uv-cache ./scripts/validate.sh
git diff --check
```

If Terraform Registry or PyPI access is required, use nameserver `192.168.1.1` and distinguish network/toolchain failures from code failures. Do not use live AWS credentials, state, production Environments, binary plans, raw CONFIG, or secrets.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-3.9-Deprecate-and-Retire-Platform-Versions`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-17`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-18`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-20`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-22`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-23`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-24`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-29`]
- [Source: `_bmad-output/implementation-artifacts/3-8-migrate-compatible-platform-versions.md`]
- [Source: `_bmad-output/implementation-artifacts/3-7-publish-immutable-platform-releases.md`]
- [Source: `_bmad-output/implementation-artifacts/1-15-garbage-collect-unreferenced-platform-versions.md`]
- [Source: `contracts/README.md#Versioning-And-Migration`]
- [Source: `contracts/v1/catalogs/lifecycle.json`]
- [Source: `docs/runbooks/platform-version-lifecycle.md`]
- [Source: `_bmad-output/project-context.md`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

### Completion Notes List

- Implemented an additive, catalog-backed deprecation record with warn-only behavior, complete sanitized notices, support/review metadata, and time-bounded independently approved security exceptions.
- Implemented checksum-bound retirement handoff validation that reuses Story 3.8 migration evidence and Story 1.15 lifecycle proof. It rejects stale plans, mutable/incomplete inventory, bad release bindings, unsupported lifecycle authority, and any active/unknown reference before a delete adapter can be reached.
- Closed the rerun review patches: lifecycle and inventory artifacts are bound, source collection evidence is explicit, removal-major and typed late-recheck gates fail closed, and the trusted protected workflow publishes the complete handoff with its checksum envelope.
- Added contract schema/catalog/fixture integrity registration and lifecycle/Compatibility Package operating guidance. Physical deletion remains exclusively delegated to `lifecycle-garbage-collection`.
- Validation passed: focused contract/lifecycle tests, Ruff, mypy, `pytest tests runtime -q` (314 passed, 270 subtests), full `python -m scripts.validate`, and `git diff --check`. Full validation used host networking with nameserver `192.168.1.1` after sandboxed PyPI DNS failed; no AWS credentials, state, plans, production Environments, raw CONFIG, or secrets were used.

### File List

- `_bmad-output/implementation-artifacts/3-9-deprecate-and-retire-platform-versions.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `contracts/README.md`
- `contracts/manifest.json`
- `contracts/releases/1.0.0.json`
- `contracts/v1/catalogs/deprecation.json`
- `contracts/v1/fixtures/deprecation/cases.json`
- `contracts/v1/schemas/deprecation-record.schema.json`
- `docs/runbooks/platform-version-lifecycle.md`
- `.github/workflows/retire-platform-version.yml`
- `scripts/deprecation_contract.py`
- `runtime/lifecycle_gc/src/lifecycle_gc/cleanup.py`
- `runtime/lifecycle_gc/src/lifecycle_gc/domain.py`
- `scripts/validate.py`
- `tests/contract/test_contract_schemas.py`
- `tests/contract/test_deprecation_contract.py`

### Change Log

- 2026-07-30: Implemented fail-closed deprecation and exact lifecycle-retirement handoff contracts; moved story to review.
- 2026-07-30: Closed all code-review patches with immutable evidence bindings, direct-execution denial, protected validation workflow, and executable retirement scenarios.
- 2026-07-30: Closed rerun review patches for exact handoff artifact binding, complete source evidence, removal-major enforcement, typed revalidation, and locked protected-workflow delivery.
