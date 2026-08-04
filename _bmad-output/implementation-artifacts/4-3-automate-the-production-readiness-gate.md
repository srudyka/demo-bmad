---
epic: 4
story: 4.3
title: Automate the Production Readiness Gate
status: done
baseline_commit: 2ef3c7e
---

# Story 4.3: Automate the Production Readiness Gate

Status: done

## Story

As a Production Approver,
I want production readiness backed by attributable machine-verifiable evidence,
so that no job generation is activated with missing security, reliability, or operational controls.

## Acceptance Criteria

1. A readiness workflow creates a versioned, secret-free evidence record bound to repository/source commit, workflow SHA/run, plan checksum, Deployment Identity, account, Region, Environment, job ID, CONFIG hash, schedule generation, Cell version, policy bundle, and target manifest. Evidence from another revision, target, plan, job, generation, or run is rejected.
2. Evidence collection covers formatting, Terraform validation, module/examples, contracts, runtime tests, provider-lock verification, security scans, IAM analysis, policy results, representative plan impact, immutable image proof, Cell compatibility, target verification, and address-migration checks. Every item records tool/policy version, timestamp, result, artifact checksum, and sensitivity classification.
3. The gate verifies ownership/tags, permissions boundaries, least-privilege roles, confused-deputy conditions, secret references, private networking, bounded egress, public-IP prohibition, encrypted state, retained logs, occurrence-aware completion, alarms, notification routing, and lifecycle acknowledgement. Missing, contradictory, stale, or placeholder evidence blocks readiness.
4. Operational readiness requires the completed job Runbook, alarm mapping, runtime/overlap/idempotency declaration, escalation, rollback/forward-fix, compensation, RTO, known limitations, post-deployment verification plan, and attributable attestations bound to the exact Deployment Identity.
5. Deterministic Compatibility Package fixtures prove the gate accepts complete signed schedule, launch/runtime, completion/alert, security, and recovery evidence and rejects every missing or mismatched category. Production readiness remains blocked until later qualification stories provide equivalent target-release/disposable-Cell evidence.
6. Approval routing requires Platform Engineering and the Job Owner; the versioned qualifying-change catalog determines whether Security or another control owner is required. Self-approval, placeholder approvers, stale reviews, unknown policy versions, and approvals for another revision are rejected.
7. Missing or failed items produce an exact remediation, evidence owner, and resolution point. Free-form comments, lower-environment results, or manual workflow inputs cannot convert failure to success. Valid exceptions require exact policy/resource, owner, justification, approver, expiry/review date, compensating control, source, target, plan, and audit trail.
8. A completed decision emits a checksum-bound pass/fail/exception/limitation record conforming to the Story 3.5 readiness schema plus an authorized reviewer summary with access-controlled evidence links. The summary excludes secrets, binary plans, credentials, raw CONFIG, unrestricted logs, and sensitive application data.
9. Any bound input or evidence change invalidates the decision; activation preflight must recompute and reapprove readiness. Only a current passing exact-generation decision can authorize the production phase-two plan.
10. Positive and negative fixtures deterministically cover every mandatory category, exception rule, approval classification, mismatch, expiry, and invalidation path; policy/schema changes cannot silently reduce required evidence.

## Tasks / Subtasks

- [x] Define the readiness evidence and decision contract (AC: 1-5, 8-10)
  - [x] Reuse `contracts/v1/schemas/production-readiness-decision.schema.json`, `contracts/manifest.json`, Compatibility Package identifiers, Deployment Identity, target manifests, and existing checksum algorithms; do not create a second readiness or plan identity format.
  - [x] Add any additive schema/catalog fields needed for evidence categories, tool versions, sensitivity, attestations, remediation ownership, exception/limitation disposition, and reviewer summary without weakening Story 3.5 exact bindings.
  - [x] Update manifest/release checksums and schema fixtures together; preserve production `epic4` provenance versus disposable-fixture provenance and fail closed for production fixture evidence.
- [x] Implement machine-verifiable evidence collection and evaluation (AC: 1-5, 7-9)
  - [x] Extend existing `scripts/production_apply.py`, `scripts/production_bundle.py`, `scripts/production_policy.py`, and deployment/target validators rather than duplicating parsers or checksum formats.
  - [x] Build a deterministic evaluator that checks exact source/workflow/run/target/plan/Cell/job/CONFIG/schedule/Deployment Identity bindings, freshness/expiry, category completeness, sensitivity, artifact checksums, policy version, and lifecycle state.
  - [x] Emit bounded sanitized findings with remediation, owner, and resolution point; reject comments or lower-environment evidence as substitutes for required records.
  - [x] Invalidate and require recomputation when any bound input, evidence checksum, policy/schema version, target, plan, generation, or Deployment Identity changes.
- [x] Integrate approval and protected activation preflight (AC: 6, 8, 9)
  - [x] Require Platform Engineering and Job Owner approval and route Security/other control owners from the versioned qualifying-change catalog; reject self-review, placeholders, stale/unknown approvals, and mismatched revisions.
  - [x] Keep readiness credential-free and separate from apply credentials; publish only sanitized summaries and access-controlled evidence references.
  - [x] Ensure Story 3.5 phase-two preflight consumes the exact current readiness checksum and remains fail-closed until real Epic 4 evidence exists.
- [x] Add deterministic fixtures, regression tests, and documentation (AC: 5, 7, 10)
  - [x] Add complete and one-category-missing/mismatched/expired/changed-input fixtures for schedule, launch/runtime, completion/alerts, security, recovery, approvals, exceptions, and invalidation.
  - [x] Test secret/plan/raw-CONFIG exclusion, evidence tampering, wrong target/job/generation/run, unknown policy/schema, stale attestations, duplicate approvals, exception expiry, and fixture evidence in production.
  - [x] Document readiness inputs, evidence ownership, remediation states, exception boundaries, reviewer routing, evidence retention, rollback, and DNS/toolchain failure reporting in the relevant runbooks and contract README.
  - [x] Run focused tests, `terraform fmt -check` where applicable, `git diff --check`, and `./scripts/validate.sh` with pinned uv; report registry/PyPI DNS failures separately.

## Dev Notes

### Architecture and security guardrails

- Production readiness is a gate, not a reporting convenience. Missing, contradictory, stale, placeholder, unsigned, or cross-generation evidence blocks activation.
- Preserve separation between Scheduler delivery, evidence normalizer, Process Manager, command, launch, ECS execution, Terraform plan, and Terraform apply roles. The readiness evaluator cannot mutate runtime state or assume apply credentials.
- Bind all evidence to the exact account, Region, Environment, Terraform root/state identity, Cell Contract/version, repository/source commit, workflow full SHA/run, target manifest, provider/backend locks, plan checksum, job ID, CONFIG hash/version, schedule generation, and Deployment Identity.
- Use the versioned production-readiness policy/catalog for non-exemptible controls (`TARGET_BINDING`, `PLAINTEXT_SECRET`, `PRIVILEGE_ESCALATION`, `MUTABLE_DEPLOYMENT_IDENTITY`, `OCCURRENCE_TRACKING_MISSING`) and reviewer routing. Unknown policy versions fail closed.
- Production evidence must prove private networking, bounded egress, no public IP, scoped IAM/PassRole and confused-deputy conditions, immutable images, secret references, retained logs, alarms/notifications, lifecycle acknowledgement, occurrence-aware completion, rollback, and Runbook readiness.

### Existing code and reuse requirements

- Keep the strict Story 3.5 readiness decision schema as the apply-facing decision. Prefer a separate versioned, manifest-listed readiness-evidence envelope/aggregate schema for category items, attestations, remediation, sensitivity, and reviewer summary; if the decision schema must change, make an explicitly additive versioned change, update all checksums/fixtures, and never weaken `additionalProperties: false` or silently alter the apply contract.
- Extend `scripts/production_bundle.py` only as an evidence join/manifest boundary. It must never manufacture approval or readiness evidence.
- Reuse `scripts/production_policy.py`, `scripts/deployment_targets.py`, `scripts/deployment_evidence.py`, `scripts/trusted_plan.py`, `scripts/check_repository.py`, and `scripts/validate.py`; do not create alternate policy evaluation, plan checksum, target identity, or Deployment Identity formats.
- Existing fixtures and tests under `contracts/v1/fixtures/`, `tests/contract/test_trusted_plan.py`, and related contract tests are normative patterns. Update `contracts/manifest.json` and release metadata whenever contract artifacts change.
- Reuse Story 4.2’s actionable template/canary Runbooks and `docs/runbooks/deployment-targets.md`, `pull-request-validation.md`, and `README.md`; do not duplicate operational authority.

### Evidence contract and decision semantics

- Each evidence item must identify category, exact binding projection, producer, tool/policy version, evaluated timestamp, result, artifact checksum, sensitivity classification, and sanitized location/reference.
- Required categories are schedule/expectation, launch/runtime, completion/alert durability, security/IAM/network/secrets, recovery/rollback/compensation, operational Runbook/ownership, target/Cell compatibility, policy/plan impact, and provider/lock/hygiene validation.
- A category is satisfied only by attributable exact-generation evidence with valid checksum, freshness, provenance, and required fields. A passed lower-environment or disposable fixture can exercise evaluator logic but cannot satisfy production evidence provenance.
- Findings are bounded and actionable: stable code, severity/disposition, exact missing or mismatched field, evidence owner, remediation, resolution point, and whether production-blocking. Never include secrets, binary plans, credentials, raw CONFIG, unrestricted logs, or sensitive application data.
- Exceptions are not a free-form override. Validate policy/resource, source commit, target, plan checksum, owner, justification, approver, compensating control, expiry, review date, signature/audit reference, and exact scope; expired or changed-plan exceptions fail.
- Any change to source, workflow, target manifest, Cell Contract, provider/backend lock, policy/schema/catalog, plan, CONFIG, schedule generation, Deployment Identity, evidence checksum, approval, or exception invalidates the decision and requires recomputation/reapproval.

### Workflow and file structure

- Keep `.github/workflows/validate.yml` credential-free. Readiness collection/reporting may use protected evidence inputs, but apply credentials remain unavailable until Story 3.5’s exact-plan boundary.
- Likely update targets: `scripts/production_apply.py`, `scripts/production_bundle.py`, readiness/policy schema/catalog and manifest files under `contracts/`, `tests/contract/test_trusted_plan.py` or dedicated readiness tests, `.github/workflows/production-approval-bundle.yml`/trusted-plan integration only where required, and relevant runbooks/README files.
- Do not add Terraform resources or live AWS qualification in this story. Use deterministic credential-free fixtures and disposable fixtures only; real target-release qualification belongs to Stories 4.4–4.8.
- Do not commit `.terraform/`, state, `.tfvars`, saved plans, credentials, secret values, raw CONFIG, unrestricted logs, or generated evidence outside controlled fixture/artifact paths.

### Testing and validation

Use the pinned repository toolchain: uv `0.11.29`, Python `3.14.6`, Terraform `1.15.8`, AWS provider `6.54.0`, Ruff, mypy, pytest, JSON Schema, and Checkov. Tests must run without AWS credentials and must preserve the validator’s final summary/exit status.

Minimum negative matrix: missing category; wrong source/workflow/run; wrong account/Region/Environment/root/state; changed plan/target/Cell/job/CONFIG/schedule/Deployment Identity; stale/expired evidence or approval; unknown policy/schema; fixture provenance in production; unsigned/tampered evidence; self/placeholder/unrelated approver; expired/overbroad exception; secret/raw-CONFIG/plan leakage; and changed inputs after a passing decision.

### Scope boundary

This story owns machine-verifiable readiness evidence, decision evaluation, approval routing, invalidation, sanitized publication, and protected preflight integration. It does not execute live production qualification, implement schedule/launch/completion/security/recovery fault injection, create pilot metrics, or authorize production activation without the later Epic 4 evidence stories.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-4.3-Automate-the-Production-Readiness-Gate`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-12`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-15`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-16`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-17`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-20`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-22`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-28`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-29`]
- [Source: `_bmad-output/project-context.md`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]
- [Source: `_bmad-output/implementation-artifacts/3-4-enforce-production-policies-and-govern-exceptions.md`]
- [Source: `_bmad-output/implementation-artifacts/3-5-approve-and-apply-the-exact-production-plan.md`]
- [Source: `_bmad-output/implementation-artifacts/4-2-complete-an-actionable-job-runbook.md`]
- [Source: `contracts/v1/schemas/production-readiness-decision.schema.json`]
- [Source: `contracts/v1/catalogs/production-policy.json`]
- [Source: `scripts/production_apply.py`]
- [Source: `scripts/production_bundle.py`]
- [Source: `scripts/production_policy.py`]
- [Source: `scripts/deployment_targets.py`]
- [Source: `scripts/deployment_evidence.py`]
- [Source: `scripts/validate.py`]

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Added additive `readiness-evidence` contract and strict credential-free evaluator with exact-generation bindings, category completeness, expiry, sensitivity, attestation, remediation, and invalidation checks.
- Integrated readiness evidence into the protected production bundle and apply preflight without weakening the Story 3.5 decision schema.
- Added deterministic positive/negative tests for missing categories, mismatches, expiry, sensitive content, checksum sealing, and changed-input invalidation.
- Updated contract manifest/release checksums and readiness documentation.
- Applied all adversarial review patches: mandatory approvals, complete control projection, strict dispositions, reviewer summaries, provenance-bound checksums, exact Terraform/lock bindings, schema alignment, freshness, artifact manifests, and pre-seal validation.
- Validation: focused readiness suite passed (`11 passed`); full Python regression passed (`347 passed, 355 subtests`); Ruff, mypy, and diff checks passed. `./scripts/validate.sh` was attempted with uv 0.11.29 but blocked by DNS resolution for PyPI.

### File List

- `.github/workflows/production-apply.yml`
- `.github/workflows/production-approval-bundle.yml`
- `_bmad-output/implementation-artifacts/4-3-automate-the-production-readiness-gate.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `contracts/README.md`
- `contracts/manifest.json`
- `contracts/releases/1.0.0.json`
- `contracts/v1/schemas/readiness-evidence.schema.json`
- `docs/runbooks/deployment-targets.md`
- `scripts/production_apply.py`
- `scripts/production_bundle.py`
- `scripts/readiness_gate.py`
- `tests/contract/test_contract_schemas.py`
- `tests/contract/test_documentation.py`
- `tests/contract/test_readiness_gate.py`
- `tests/contract/test_trusted_plan.py`

## Change Log

- 2026-07-31: Created implementation-ready context for Story 4.3.
- 2026-07-31: Implemented the machine-verifiable production readiness evidence gate and protected preflight integration.

### Review Findings

- [x] [Review][Patch] Enforce mandatory Platform Engineering and Job Owner approvals, qualifying-change catalog routing, independent actors, freshness, and exact revision/Deployment Identity bindings; one arbitrary attestation currently passes AC6 [scripts/readiness_gate.py:229-247; contracts/v1/schemas/readiness-evidence.schema.json:73-87]
- [x] [Review][Patch] Replace coarse category-name checks with machine-verifiable claims for every required technical, security, infrastructure-control, and operational Runbook control; placeholder artifact references currently satisfy AC2-4 [scripts/readiness_gate.py:23-33,141-170,217-228]
- [x] [Review][Patch] Add strict exception, limitation, remediation, owner, and resolution-point semantics; non-passed statuses and malformed findings can currently pass without valid disposition [scripts/readiness_gate.py:195-205,248-269; contracts/v1/schemas/readiness-evidence.schema.json:89]
- [x] [Review][Patch] Add an authorized reviewer summary and access-controlled evidence-link contract; the evaluator currently returns only a local summary and accepts arbitrary references [scripts/readiness_gate.py:168-169,270-281; contracts/v1/schemas/readiness-evidence.schema.json:7-18]
- [x] [Review][Patch] Expand deterministic negative fixtures to cover all required category controls, approval classifications, exceptions, every binding mismatch, policy/schema changes, tampering, stale attestations, and production fixture provenance [tests/contract/test_readiness_gate.py:111-145]
- [x] [Review][Patch] Stop deriving the expected readiness-evidence checksum from the same downloaded evidence file; bind it to independently trusted approval/manifest provenance and verify the evidence-run identity [production-approval-bundle.yml:70-82; production-apply.yml:94-103]
- [x] [Review][Patch] Require the full exact binding projection, including Terraform root/state and provider/backend lock identities, and fail when expected bindings are absent instead of comparing only keys present in the caller [scripts/readiness_gate.py:43-60,122-139; scripts/production_apply.py:425-446]
- [x] [Review][Patch] Align the JSON schema with runtime semantics for exact findings, categories, timestamps, binding checksums, artifact references, and evidence checksums; current schema/runtime drift permits schema-valid but unenforceable envelopes [contracts/v1/schemas/readiness-evidence.schema.json:53-92; scripts/readiness_gate.py:141-269]
- [x] [Review][Patch] Enforce freshness windows for envelope, item, and attestation timestamps, rejecting future or arbitrarily old evidence [scripts/readiness_gate.py:209-247]
- [x] [Review][Patch] Verify artifact references and checksums against a controlled artifact manifest/access policy rather than accepting format-only hashes and arbitrary URLs [scripts/readiness_gate.py:141-170]
- [x] [Review][Patch] Validate before sealing an evidence envelope so the sealing helper cannot create checksums for incomplete or invalid records [scripts/readiness_gate.py:284-290]
