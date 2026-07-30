---
epic: 3
story: 3.7
title: Publish Immutable Platform Releases
status: done
baseline_commit: ab8b9c60972420792689e82d3d4541ced0194dea
---

# Story 3.7: Publish Immutable Platform Releases

## Story

As a Platform Owner,  
I want modules, workflows, runtimes, and contracts published as one attributable immutable release,  
so that consumers can pin exactly what was tested and deployed.

## Acceptance Criteria

1. Semantic-version classification maps fixes/documentation to patch, compatible capabilities to minor, and breaking interface/schema/workflow/behavior changes to major. Classification fails closed when changed inputs, outputs, schemas, fixtures, workflow contracts, resource addresses, or documented behavior disagree with the requested class.
2. A release candidate cannot publish unless credential-free validation, Terraform modules/examples, contracts, runtime tests, policy fixtures, IAM-negative tests, schedule/reducer suites, trusted-plan checks, and required disposable-Cell evidence are complete, fresh, and checksum-bound.
3. The release manifest records exact source commit, release version, Terraform/AWS provider/Python/Fargate tested matrix, Cell/module/workflow/contract versions, schema ranges, policy bundle, known limitations, checksums, qualification evidence, and migration class. Dated test observations are distinct from permanent constraints and managed-runtime exceptions.
4. Every published artifact is immutable and bound to the same release manifest, source commit, builder workflow SHA/run, checksums, qualification evidence, OIDC actor, and publication timestamp. Mutable refs, mutable images, rewritten artifacts, long-lived credentials, untrusted PR artifacts, and manual rebuilds are rejected.
5. Consumer validation rejects mutable module/workflow/Action/image references, missing provider locks, unexpected provider selection, unsupported contract/schema ranges, and contract checksum mismatches.
6. Release notes describe capabilities, security and operational impact, compatibility, state/address changes, required two-phase actions, limitations, rollback identity, and whether Stories 3.8/3.9 apply. Notices use approved GitHub and internal engineering channels.
7. A defective release is marked affected without overwrite or deletion; a corrected release uses a new version, preserves prior evidence through the rollback horizon, and provides exact rollback/upgrade guidance.
8. Fixtures cover wrong version class, source drift, checksum mismatch, mutable references, missing/stale evidence, untrusted builder, partial publication, duplicate version, compliant reproduction, and consumer rejection without live AWS, state, credentials, production environments, committed plans, or secrets.

## Tasks / Subtasks

- [x] Define immutable release manifest, provenance, qualification, affected-release, and release-note contracts (AC: 1-4, 6-7)
  - [x] Reuse contracts/manifest.json, release snapshots, RFC8785 canonical JSON, Deployment Identity, policy, and artifact-integrity formats.
  - [x] Add schema and stable runtime errors for class mismatch, mutable refs, provenance, and checksum failures.
  - [x] Update contract manifest, release metadata, and raw-byte checksums together.
- [x] Implement semantic classification and release assembly (AC: 1-3)
  - [x] Extend existing semantic-version and artifact-integrity conventions without a second checksum format.
  - [x] Compare requested SemVer class against changed schema/workflow/interface and module boundaries.
  - [x] Assemble only from an exact source commit and checksum-bound qualification evidence.
- [x] Add protected immutable publication workflow (AC: 2, 4, 7)
  - [x] Require immutable source, protected Environment, same-manifest qualification, and workflow provenance.
  - [x] Publish release evidence using a full-SHA action and immutable release identity.
  - [x] Verify manifest checksums before publication and retain prior records.
- [x] Enforce consumer compatibility (AC: 5)
  - [x] Reject mutable references, missing provider-lock checksums, and unsupported component ranges before side effects.
- [x] Document release operations (AC: 6-7)
  - [x] Document manifest verification, immutable correction, evidence retention, and rollback identity.
  - [x] Keep migration in Story 3.8, deprecation/removal in Story 3.9, and pilot qualification in Epic 4.
- [x] Add deterministic fixtures and tests (AC: 1-8)
  - [x] Test classification, checksum binding, immutable references, artifact reproduction, and consumer rejection.
  - [x] Run full validation without live AWS credentials, state, production Environment, binary plans, or secrets.

## Dev Notes

### Required reuse and invariants

- contracts/ is the normative compatibility package. Reuse its semantic-version rules, canonical JSON, artifact inventory, schema registry, release snapshots, and migration metadata.
- Extend scripts/validate.py, scripts/trusted_plan.py, scripts/production_policy.py, scripts/deployment_evidence.py, and existing provenance helpers.
- Preserve full-SHA Actions/workflows, digest-pinned images, committed provider locks, terraform init -lockfile=readonly, and Story 3.5/3.6 target, plan, policy, evidence, and recovery boundaries.
- A published manifest and artifact are immutable. Corrections create a new version and retain prior evidence and known-good artifacts.

### Architecture guardrails

- AD-17 requires immutable module/workflow/action/image/provider inputs and explicit managed-runtime exceptions in Deployment Identity.
- AD-20 requires credential-free validation, reviewed policy gates, short-lived OIDC/operator authority, and no human workload-role assumption.
- AD-22 requires security/IAM evidence, immutable identity, logs/retention, alarms, cost/impact notes, and rollback/runbook evidence.
- AD-23 requires every module, producer, workflow, and runtime to consume the same checked-in compatibility package.
- AD-29 requires release-related schedule/CONFIG changes to preserve RESERVED → PUBLISHED → VALIDATED → MATERIALIZED → ENABLED and two-phase action boundaries.

### File and integration map

- Contracts and fixtures: contracts/v1/schemas/, contracts/v1/fixtures/, contracts/manifest.json, contracts/releases/, contracts/migrations/.
- Pure classification/provenance/validation: scripts/ beside existing contract, policy, trusted-plan, target, bundle, and deployment-evidence helpers.
- Protected publication: .github/workflows/ with full-SHA Actions, immutable refs, protected Environment, concurrency, and short-lived OIDC.
- Consumer checks: existing repository hygiene, policy, trusted-plan, and validation paths.
- Documentation: docs/runbooks/ and contracts/README.md.
- Do not add Terraform resources, live registry credentials, committed state, binary plans, raw CONFIG, or secrets.

### Testing and validation

Use uv 0.11.29, Python 3.14.6, Terraform 1.15.8, AWS provider 6.54.0, Ruff, mypy, pytest, JSON Schema, and Checkov.

    PATH=/private/tmp/demo-bmad-uv-01129/bin:$PATH UV_CACHE_DIR=/private/tmp/demo-bmad-uv-cache uv run --locked pytest tests runtime -q -p no:cacheprovider
    PATH=/private/tmp/demo-bmad-uv-01129/bin:$PATH UV_CACHE_DIR=/private/tmp/demo-bmad-uv-cache ./scripts/validate.sh
    git diff --check

If registry/PyPI access is required, use host-networked validation with DNS 192.168.1.1 and distinguish network/toolchain failures from code failures.

### Scope boundary

This story publishes and verifies immutable release artifacts and provenance. It does not migrate consumers (3.8), deprecate/remove versions (3.9), or qualify the production pilot (Epic 4).

## Previous Story Intelligence

- Story 3.6 established Deployment Identity, sanitized evidence, checksum-bound artifacts, protected recovery gates, emergency evidence, and fail-closed verification.
- Story 3.6 review showed documentation-only claims are insufficient: every workflow consumer needs a producer, schema/runtime inventories must match, and tests must cover workflow boundaries.
- Keep release provenance separate from terminal/recovery evidence; never place binary plans, raw state, CONFIG, credentials, or unrestricted logs in release artifacts.

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-3.7-Publish-Immutable-Platform-Releases]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-17]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-20]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-22]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-23]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-29]
- [Source: _bmad-output/implementation-artifacts/3-6-record-deployment-and-rollback-evidence.md]
- [Source: _bmad-output/implementation-artifacts/3-5-approve-and-apply-the-exact-production-plan.md]
- [Source: contracts/README.md]
- [Source: _bmad-output/project-context.md]
- [Source: _bmad/custom/standards/aws-terraform-implementation.md]

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story derived from Epic 3, architecture AD-17/20/22/23/29, project standards, contracts, Story 3.5, and Story 3.6 review learnings.
- Implemented immutable release classification, manifest/schema validation, artifact verification, consumer compatibility checks, protected publication workflow, contract registration, documentation, and deterministic tests.
- Full validation passed: Terraform validation, Ruff, mypy, 296 tests and 266 subtests, and Checkov (1,012 checks passed).

### Review Findings

- [x] [Review][Patch] Adopt 30-day rollback evidence retention, an immutable GitHub release/tag registry, and GitHub plus internal engineering notifications; implement duplicate-version, affected-release, and corrected-version handling [`.github/workflows/publish-platform-release.yml:35-64`]
- [x] [Review][Patch] Enforce all required qualification gates and checksum-bound, fresh evidence before publication [`.github/workflows/publish-platform-release.yml:35-57`]
- [x] [Review][Patch] Bind builder workflow identity, run identity, OIDC actor, and publication timestamp to the actual trusted workflow [`.github/workflows/publish-platform-release.yml:35-52`]
- [x] [Review][Patch] Publish and verify every manifest-listed artifact against the same immutable release identity and source commit [`.github/workflows/publish-platform-release.yml:58-64`]
- [x] [Review][Patch] Enforce the release schema and metadata formats in runtime validation, including evidence, policy, migration, limitations, compatibility, and timestamp fields [`scripts/release_manifest.py:159-206`]
- [x] [Review][Patch] Reject mutable Git branches/tags and plain SemVer module references [`scripts/release_manifest.py:81-98`]
- [x] [Review][Patch] Reject unknown artifact kinds before reference validation [`scripts/release_manifest.py:132-138`]
- [x] [Review][Patch] Constrain artifact paths to the release root before hashing [`scripts/release_manifest.py:209-219`]
- [x] [Review][Patch] Compare the consumer provider-lock checksum with the release manifest and verify provider selections [`scripts/release_manifest.py:222-246`]
- [x] [Review][Patch] Make SemVer classification fail closed for empty changes, resource-address changes, behavior/documentation changes, fixtures, and workflow contracts [`scripts/release_manifest.py:28-78`]
- [x] [Review][Patch] Align release-version validation so builders reject leading-zero SemVer components [`scripts/release_manifest.py:101-120`]
- [x] [Review][Patch] Use the repository’s RFC8785 canonical JSON implementation for manifest digests [`scripts/release_manifest.py:22-25`]
- [x] [Review][Patch] Add required tested version matrix, component/schema ranges, runtime exceptions, and dated qualification observations to the manifest schema [`contracts/v1/schemas/release-manifest.schema.json:7-20`]
- [x] [Review][Patch] Implement release notes, affected-release records, corrected-version linkage, and exact rollback/upgrade guidance [`contracts/README.md:81-86`]
- [x] [Review][Patch] Add deterministic fixtures for stale/missing evidence, source drift, untrusted builders, partial publication, duplicate versions, checksum mismatches, and consumer rejection [`tests/contract/test_release_manifest.py:37-102`]

### File List

- _bmad-output/implementation-artifacts/3-7-publish-immutable-platform-releases.md
- .github/workflows/publish-platform-release.yml
- contracts/v1/schemas/release-manifest.schema.json
- scripts/release_manifest.py
- tests/contract/test_release_manifest.py
- contracts/README.md
- contracts/manifest.json
- contracts/releases/1.0.0.json
- scripts/validate.py
- tests/contract/test_contract_schemas.py

### Change Log

- 2026-07-30: Implemented immutable release manifest, SemVer classification, protected publication evidence, consumer compatibility validation, contract registration, documentation, and tests; moved story to review.
