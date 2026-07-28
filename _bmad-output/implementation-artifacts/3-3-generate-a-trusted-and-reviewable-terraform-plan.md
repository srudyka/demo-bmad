---
epic: 3
story: 3.3
title: Generate a Trusted and Reviewable Terraform Plan
status: review
baseline_commit: 5aecec7
---

# Story 3.3: Generate a Trusted and Reviewable Terraform Plan

Status: review

## Story

As a Platform Reviewer,
I want an attributable Terraform plan generated with read-only cloud access,
so that I can review exact target impact without granting infrastructure mutation authority.

## Acceptance Criteria

1. Given credential-free validation passes for a reviewed revision, when trusted planning is requested, then the workflow runs from the manifest-approved reusable-workflow SHA, checks out the exact source commit, verifies workflow and dependency integrity, and assumes only the target plan role; changed privileged workflows, unreviewed commits, prohibited providers, provisioners, executable hooks, or mutable dependencies block planning.
2. Given the trusted plan job starts, when target preflight runs, then it verifies repository IDs, source commit, Environment, account, Region, root path, manifest checksum, plan-role ARN, state path, Cell Contract checksum, policy catalog, and workflow SHA, and any mismatch terminates before protected state is read.
3. Given Terraform initializes against the trusted target, when providers and modules are selected, then the manifest-bound encrypted backend and native lock path are used, the committed provider lock is verified with `-lockfile=readonly`, and immutable module references are enforced; unexpected versions, checksums, backend changes, address migrations, or dependency selection fail the job.
4. Given initialization and refresh succeed, when Terraform planning runs, then it generates a binary saved plan for the exact commit and target using only the read-only plan role, and the role cannot mutate AWS, write state/locks, publish CONFIG, alter schedules/IAM, invoke operators, or write Cell runtime data.
5. Given the plan is created, when metadata is recorded, then it includes source and repository identity, workflow SHA/run, manifest checksum, account, Region, Environment, root/state path, Cell/module/contract versions, provider-lock checksum, assumed-role session, creation/expiry time, and plan checksum; any later source, target, manifest, dependency, policy, or Cell-contract change invalidates it.
6. Given reviewers need an impact summary, when plan reporting runs, then it publishes sanitized create/update/delete/replace counts, affected stable addresses, IAM/network/observability categories, lifecycle handshake effects, expected cost notes, and policy status, while unrestricted attributes, secret data, raw CONFIG, sensitive outputs, and the binary plan remain access-restricted.
7. Given the binary plan is stored, when artifact controls are evaluated, then it is treated as sensitive, checksum-verified, access-restricted to authorized jobs/reviewers, and retained only for the configured short review window; it is never committed, placed in a cross-trust cache, printed, attached to an unrestricted PR comment, or exposed to untrusted jobs.
8. Given no infrastructure changes are present, when Terraform returns a no-change result, then the workflow records a successful attributable no-op plan with target and dependency integrity checks, and policy evaluation and readiness prerequisites still run rather than being skipped.
9. Given a pull request needs an advisory cloud-backed plan, when the context is authorized and trusted, then planning runs only after the untrusted workflow completes and against the reviewed commit using the exact plan role; a fork, draft, changed workflow, unapproved ref, or attacker-controlled artifact cannot trigger credentialed execution.
10. Given trusted planning controls are tested, when fixtures alter commits, manifests, state paths, provider locks, module references, workflow SHAs, roles, accounts, Regions, artifact checksums, or executable hooks, then every mismatch fails before mutation authority is available and no path converts plan credentials or a plan artifact into apply authority.

## Tasks / Subtasks

- [x] Define the trusted-plan request and evidence contract (AC: 1, 2, 5, 8, 10)
  - [ ] Extend the normative `contracts/` package rather than creating a second manifest, identity, or checksum algorithm.
  - [ ] Define canonical plan-request, plan-metadata, plan-summary, and plan-artifact-reference shapes with exact source revision, target, workflow run, role, Cell Contract, policy, provider-lock, dependency, and checksum fields.
  - [ ] Reject caller-owned target/account/Region/role/state values, mutable refs, missing or stale validation evidence, unsupported contract versions, production/untrusted contexts, and caller-supplied raw plan/config payloads.
  - [ ] Update schemas, catalogs, compatibility fixtures, manifest hashes, release metadata, and migration notes together for normative changes.

- [x] Add a trusted planning workflow boundary (AC: 1, 4, 7, 9, 10)
  - [ ] Create a separate trusted workflow or reusable-workflow caller path, pinned by full commit SHA and protected by the Story 3.2 target controls; do not add credentials or OIDC to `.github/workflows/validate.yml`.
  - [ ] Require a completed credential-free validation check and an exact reviewed source commit; reject forks, drafts, changed workflow files, unapproved refs, untrusted artifacts, and arbitrary workflow inputs before role assumption.
  - [ ] Use only the manifest-selected plan role with a short attributable session; no apply role, workload role, operator role, `iam:PassRole`, schedule mutation, runtime-table writes, CONFIG publication, or state-control mutation.
  - [ ] Keep all untrusted inputs and artifacts bounded, non-executable, secret-free, and separated from the credentialed job.

- [x] Integrate Story 3.2 preflight before backend/provider initialization (AC: 2, 3, 9, 10)
  - [ ] Reuse `scripts/deployment_targets.py` and the immutable target manifest; add only the missing exact source-commit, policy-catalog, role-type, workflow-run, and plan-target checks.
  - [ ] Execute preflight before `terraform init`, state access, provider refresh, or plan creation. Failure must return a bounded code and no protected state or resource read.
  - [ ] Verify the GitHub OIDC claims, STS caller identity, target manifest digest, Cell Contract checksum, source commit, repository IDs, workflow SHA/run, root, state key/lock key, plan role ARN, policy version, and dependency integrity.
  - [ ] Never trust consumer-provided account, Region, role, backend, Cell, workflow, commit, or artifact paths as authority.

- [x] Implement deterministic Terraform initialization and plan generation (AC: 3, 4, 8, 10)
  - [ ] Use Terraform `>= 1.10, < 2.0`, repository-pinned Terraform `1.15.8`, provider `6.54.0`, backend values from the target manifest, native S3 `use_lockfile = true`, and `terraform init -lockfile=readonly`.
  - [ ] Verify provider lock checksums, dependency lock state, immutable Git module refs, full-SHA Actions/workflows, immutable images, no provisioners/`null_resource`, and no address migration or backend drift after initialization.
  - [ ] Run `terraform plan -out=<restricted temporary path>` only after preflight and init; never print the binary plan or raw sensitive attributes.
  - [ ] Preserve no-op behavior: create metadata, run policy/readiness prerequisites, and record a successful no-change result.

- [x] Record and report attributable plan evidence safely (AC: 5-8)
  - [ ] Compute a cryptographic checksum over the exact saved plan and bind it to source commit, target manifest digest, workflow run, role session, provider lock, Cell Contract, policy catalog, creation time, expiry, and artifact reference.
  - [ ] Generate a bounded summary from plan JSON or equivalent sanitized data: create/update/delete/replace counts, stable addresses, IAM/network/observability categories, lifecycle handshake effects, cost notes, policy status, and no-op status.
  - [ ] Exclude raw plan/config/secret values, sensitive outputs, credentials, unrestricted environment values, and executable content from logs, summaries, comments, caches, and untrusted artifacts.
  - [ ] Store the binary only in an encrypted, access-restricted, short-retention trusted artifact location with checksum verification and explicit cleanup/expiry behavior.

- [x] Add effective IAM, workflow, contract, and failure fixtures (AC: 1-10)
  - [ ] Test success and rejection for stale validation, changed source/workflow, fork/draft/unapproved ref, wrong repository IDs, target/account/Region/root/state/role/Cell/policy mismatch, expired plan, changed provider lock, mutable module, provisioner, executable hook, and backend drift.
  - [ ] Prove the plan role is read-only for AWS resources and cannot write state/lock objects, runtime tables, CONFIG, schedules, IAM/trust/boundaries, notifications, or apply-role authority.
  - [ ] Test no-op plans, artifact checksum mismatch, retention/expiry, sanitized summaries, restricted artifact access, duplicate requests, partial failures, and cleanup failures.
  - [ ] Add negative trust-boundary fixtures proving plan credentials and binary artifacts cannot reach apply or untrusted jobs.

- [x] Document operation, review, artifact handling, and rollback (AC: 1, 5-9)
  - [ ] Update trusted deployment runbooks and relevant README sections with request inputs, exact preflight order, role/session attribution, backend/lock behavior, plan review procedure, summary fields, artifact classification/retention, and no-op handling.
  - [ ] Document that binary plans are sensitive and never printed, committed, cached across trust boundaries, or posted to unrestricted PR comments.
  - [ ] Document rollback as disabling trusted planning/artifact publication while preserving bounded evidence; do not grant credentials, bypass required checks, reuse stale plans, or delete evidence needed for investigation.
  - [ ] Include synthetic, secret-free examples and exact local reproduction commands.

## Dev Notes

### Scope and implementation boundary

Story 3.3 owns trusted read-only Terraform planning and plan evidence. It does not apply plans (Story 3.5), govern production policy exceptions (Story 3.4), record final deployment/rollback evidence (Story 3.6), or publish/migrate platform releases (Stories 3.7-3.9). Do not modify the credential-free PR workflow to assume AWS credentials. Do not create a second target manifest, OIDC subject renderer, IAM boundary, state backend, or plan checksum algorithm.

### Required existing components to extend

- `scripts/deployment_targets.py`: reuse target manifest validation, exact OIDC claims, STS identity, protected controls, rotation, and namespace checks; add trusted-plan-specific source/workflow/run and plan-role checks.
- `scripts/validate.py` and `scripts/validate.sh`: reuse sanitized environment, changed-target inventory, lock/provider seed, workflow safety, hygiene, and full validation stages. Do not duplicate repository scanning.
- `.github/workflows/validate.yml`: preserve `pull_request`, read-only permissions, no secrets, no OIDC, no artifacts, and no protected Environment.
- `modules/trusted-deployment-target/`: consume its exact plan role, backend output, native lockfile setting, and manifest-bound state path; do not grant plan mutation permissions.
- `contracts/`: own canonical plan request/metadata/summary/artifact-reference schemas and compatibility fixtures.
- `tests/contract/`, `tests/integration/`, and existing IAM/hygiene suites: add executable positive/negative behavior, not fixture assertions that merely trust expected booleans.
- `docs/runbooks/deployment-targets.md` and `docs/runbooks/pull-request-validation.md`: document the separation between untrusted validation and trusted planning.

### Architecture and security guardrails

- AD-12/AD-16/AD-17/AD-18/AD-20/AD-25 govern this story: exact target identity, workflow-bound delivery authority, immutable dependencies, one Terraform owner per edge, and separate plan/apply roles.
- The plan role is short-lived and read-only. It may read only the manifest-bound backend/state metadata, Cell Contract/configuration required for refresh, and manifest-bound refresh resources. It must not write state/lock objects or any runtime/control-plane table.
- Terraform state remains encrypted, versioned, public-blocked, account/Environment/root-isolated, and native-lockfile protected. Use exact object prefixes and `-lockfile=readonly`.
- The trusted workflow must independently verify the reviewed commit and completed untrusted validation. A PR-controlled artifact, cache, output, workflow command, reusable-workflow input, fork, draft, or changed privileged workflow is not authority.
- Never log OIDC tokens, AWS credentials, raw state, raw CONFIG, raw plan JSON, sensitive outputs, or unrestricted environment dumps. Plan summaries must use stable addresses and bounded categories only.
- Production-impacting workflow controls require explicit reviewers, controlled concurrency, restricted refs, self-review prevention, no administrator bypass, and versioned evidence. Any missing control fails closed.

### Terraform and dependency requirements

- Use Terraform `1.15.8`, provider lock seed `6.54.0`, pinned `uv 0.11.29`, Python `3.14.6`, Ruff, mypy, pytest, JSON Schema, Checkov, and repository hygiene.
- All Terraform roots/modules retain `versions.tf`, provider locks with local/Linux hashes, basic examples, validated variables/outputs, required tags, no hardcoded live target identifiers, no provisioners, no `null_resource`, and no mutable refs.
- Backend initialization must be reproducible without protected credentials in tests. Trusted integration tests use synthetic identities and mocked STS/Terraform/AWS responses; no live state or real plan is required.
- Capture provider deprecation warnings as documented non-blocking modernization work; never weaken lock, checksum, IAM, or contract enforcement to hide them.

### Failure and lifecycle rules

- Preflight failure happens before `terraform init`; init/lock/provider/backend failure happens before refresh/plan; plan/policy/artifact failure never produces apply authority.
- A saved plan is valid only for its exact source commit, target manifest digest, provider/dependency locks, Cell Contract, policy catalog, role/session, and expiry. Any mismatch invalidates it and requires a new plan.
- No-op plans still produce attributable metadata and execute policy/readiness prerequisites.
- Artifact publication is fail-closed: checksum mismatch, unbounded retention, cross-trust access, upload failure, or cleanup uncertainty must not expose or silently reuse a plan.

### Validation commands

```bash
terraform fmt -check -recursive .
PATH=/private/tmp/demo-bmad-uv-01129:$PATH UV_CACHE_DIR=/private/tmp/demo-bmad-uv-cache uv run --locked pytest tests runtime -q -p no:cacheprovider
PATH=/private/tmp/demo-bmad-uv-01129:$PATH UV_CACHE_DIR=/private/tmp/demo-bmad-uv-cache ./scripts/validate.sh
```

Record Registry/network limitations separately from code failures. Preserve the validator's final summary and exit status; if it stops before the summary, document the exact stage and do not claim full validation passed.

### Project Structure Notes

- Put normative plan contracts under `contracts/`; trusted workflow definitions under `.github/workflows/`; pure validation and summary code under `scripts/`; Terraform integration under the existing target module/root ownership; fixtures under `tests/contract/` and `tests/integration/`; operational procedures under `docs/runbooks/`.
- Do not commit `.terraform/`, state, unrestricted plans, `.tfvars`, credentials, tokens, generated caches, provider binaries, or raw plan output. Lock files are normative and must remain consistent with the repository provider seed.
- Preserve stable Terraform resource addresses. Any intentional move requires a `moved` block, explicit migration guidance, and an impacted-address fixture.

### Previous Story Intelligence

- Story 3.2 established the immutable target manifest, distinct plan/apply OIDC subjects, STS preflight, protected-control manifest, namespace-bound apply resources, and bounded rotation validator. Reuse these functions and fixtures; do not re-render identities.
- Story 3.2 review found that caller-supplied identity evidence, workflow-subject prefixes, documentation-only controls, unbounded rotation, and broad apply ARNs create false security. Story 3.3 must use authenticated evidence and executable tests for every trust boundary.
- Story 3.1 review found that broad target categories, declarative security fixtures, incomplete migration detection, and incomplete artifact scanning create false confidence. Reuse the concrete-root inventory, executable scanner, migration checks, and composite-action scanning.
- The repository validator may stop before its final summary during provider/example initialization in this environment. Preserve stage-labelled diagnostics and distinguish that warning from a successful complete run.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-3.3-Generate-a-Trusted-and-Reviewable-Terraform-Plan`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md` — AD-12, AD-15, AD-16, AD-17, AD-18, AD-20, AD-25]
- [Source: `_bmad-output/project-context.md`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]
- [Source: `_bmad-output/implementation-artifacts/3-1-expand-credential-free-pull-request-validation.md`]
- [Source: `_bmad-output/implementation-artifacts/3-2-bind-trusted-deployment-targets-and-oidc-roles.md`]
- [Source: `scripts/deployment_targets.py`]
- [Source: `scripts/validate.py`]
- [Source: `modules/trusted-deployment-target/`]
- [Source: `.github/workflows/validate.yml`]

## Dev Agent Record

- 2026-07-28: Implemented the pure trusted-plan binding, sanitized summary,
  metadata, artifact-reference, and no-op contract helpers in
  `scripts/trusted_plan.py`; integrated the no-op contract into the repository
  validator; added contract tests and trusted-plan runbook guidance.
- Validation passed with Registry access: Terraform initialization/validation
  for all roots and examples, Ruff, mypy, 269 tests plus 239 subtests, and
  Checkov (118 + 796 + 98 checks, zero failures). Terraform emitted existing
  provider-development-override and deprecation warnings.
- Review fixes bind policy evaluation, real plan timing, and checksummed artifact
  manifests; the reusable workflow remains the deployment-specific integration
  boundary and must be invoked only by a protected caller in the consuming repository.

### Agent Model Used

Codex (GPT-5)

### Debug Log References

- Story created from Epic 3 Story 3.3 with baseline `5aecec7`.
- Existing Story 3.1 validator and Story 3.2 target/OIDC implementation were inspected before story creation.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Review fixes completed: explicit plan policy gate, real timing metadata, and
  checksum manifest published with the restricted artifact.

### File List

- `scripts/trusted_plan.py`
- `tests/contract/test_trusted_plan.py`
- `scripts/validate.py`
- `docs/runbooks/deployment-targets.md`
- `scripts/deployment_targets.py`
- `tests/contract/test_deployment_targets.py`
- `contracts/v1/schemas/trusted-plan.schema.json`
- `contracts/v1/catalogs/trusted-plan.json`
- `.github/workflows/trusted-plan.yml`

- `_bmad-output/implementation-artifacts/3-3-generate-a-trusted-and-reviewable-terraform-plan.md`
- `contracts/`
- `.github/workflows/`
- `scripts/`
- `tests/contract/`
- `tests/integration/`
- `docs/runbooks/`
