---
epic: 3
story: 3.1
title: Expand Credential-Free Pull Request Validation
status: done
baseline_commit: 3b66eee4c8c47f89e6d66e9a51a4135316377466
---

# Story 3.1: Expand Credential-Free Pull Request Validation

Status: done

<!-- Ultimate context engine analysis completed - comprehensive developer guide created -->

## Story

As a Platform Reviewer,
I want every pull request validated without cloud credentials,
so that malformed, insecure, or non-reproducible changes are rejected before they can access AWS or protected state.

## Acceptance Criteria

1. Given a pull request changes Terraform, runtime, contracts, examples, workflows, policy, documentation, or dependency files, when credential-free validation runs, then it identifies every affected root, module, module-local example, runtime package, contract suite, policy bundle, and generated reference, and no changed validation target is silently skipped.
2. Given Terraform files change, when Terraform checks run, then they execute recursive `terraform fmt -check`, backend-free initialization, validation for every changed root/module/example, focused module tests, and address/migration checks under Terraform `>= 1.10, < 2.0`, and failures identify the exact target and command needed to reproduce them locally.
3. Given runtime or contract files change, when code checks run, then pinned dependency installation, formatting, linting, type checks, unit tests, schema tests, identity vectors, schedule fixtures, reducer permutations, IAM fixtures, and compatibility matrices run as applicable, and unsupported schema changes or test removals cannot pass by changing only expected output.
4. Given static security and repository-hygiene checks run, when the pull request is scanned, then Terraform, IAM, workflows, dependencies, documentation, fixtures, and committed files are checked for credentials, secret values, state, saved plans, `.terraform/`, committed `.tfvars`, mutable production references, prohibited provisioners, `null_resource`, hardcoded deployment identifiers, and undocumented standards deviations, and obvious secrets, invalid Terraform, formatting failures, and prohibited artifacts block every Environment.
5. Given Terraform resource addresses or module structure change, when migration validation runs, then stable addresses are preserved or reviewed `moved` blocks and explicit consumer migration guidance are present, and accidental replacement or undocumented address churn fails with the impacted resource list.
6. Given a pull request originates from a fork or another untrusted context, when validation executes, then it receives no AWS credential, protected state, Environment secret, deployment manifest secret, write token, or privileged reusable-workflow input, and untrusted code cannot reach a privileged job through artifacts, caches, outputs, workflow commands, reusable-workflow indirection, or modified workflow files.
7. Given validation needs repository permissions or pull-request reporting, when `GITHUB_TOKEN` permissions are evaluated, then each job declares the minimum read-only scope and any trusted reporting job consumes only sanitized non-executable results, and untrusted code never runs with pull-request write, Actions write, OIDC token, Environment, or contents-write authority.
8. Given providers, modules, Actions, workflows, Python packages, or container references are resolved, when supply-chain validation runs, then immutable constraints, full-SHA workflow/Action pins, provider locks, dependency locks, checksums, and approved managed-runtime exceptions are verified, and unexpected selection, checksum change, floating production reference, or mutable image fails the applicable policy.
9. Given a check produces logs, caches, summaries, or artifacts, when results are retained, then output excludes secret values, credentials, unrestricted environment dumps, raw sensitive plans, raw CONFIG, and executable content crossing trust boundaries, and artifact access and retention match the data classification.
10. Given non-production enforcement is staged, when a policy finding is reported, then severity comes from the versioned rollout catalog and clearly distinguishes advisory from blocking status with its future enforcement point, and production-equivalent controls cannot inherit a lower Environment's advisory severity.
11. Given workflow security fixtures execute, when they simulate forked changes, malicious outputs, workflow edits, cache poisoning, generated-file injection, changed locks, committed `.tfvars`, and failing checks, then none obtain privileged execution or satisfy required statuses, and all valid baseline fixtures pass without AWS credentials or network access beyond pinned dependency retrieval.

## Tasks / Subtasks

- [x] Define a changed-target inventory and validation plan (AC: 1, 2, 3, 5)
  - [x] Extend the existing `scripts/validate.py` discovery rather than creating a second validator; map changed files to every affected Terraform root, reusable module, module-local example, runtime package, contract/policy suite, documentation/generated reference, and workflow policy.
  - [x] Fail closed when a changed path has no known validation owner; print the target, stage, and exact local reproduction command.
  - [x] Keep full-repository validation available for non-PR/local runs and ensure target selection cannot omit shared contracts, manifests, locks, or generated references.

- [x] Strengthen credential-free Terraform validation (AC: 2, 4, 5, 8)
  - [x] Preserve sanitized AWS/environment execution, backend-free initialization, temporary `TF_DATA_DIR`, provider mirror/dev Cell override, and committed lock-file integrity.
  - [x] Validate every affected root/module/example with Terraform `>= 1.10, < 2.0`; add focused module tests and explicit address/migration checks for resource/module moves and consumer guidance.
  - [x] Detect provider/module selection or checksum changes, mutable module/image references, state/plan artifacts, deprecated or prohibited constructs, and undocumented standards deviations with actionable output.
  - [x] Keep provider deprecation warnings non-blocking only where documented; do not weaken validation or checksum enforcement.

- [x] Expand runtime, contract, policy, and dependency coverage (AC: 3, 4, 8, 10)
  - [x] Reuse the pinned `uv` lock and existing Ruff, mypy, pytest, JSON Schema, identity, schedule, reducer, IAM, compatibility, Checkov, and hygiene suites.
  - [x] Add negative fixtures proving schema/test expectations cannot be weakened by editing expected outputs alone, and classify policy findings through a versioned rollout catalog.
  - [x] Make unconditional safety failures (credentials, state, invalid Terraform, prohibited artifacts, formatting) blocking in every Environment; only explicitly approved governance findings may be advisory.

- [x] Harden GitHub Actions trust boundaries (AC: 6, 7, 9, 11)
  - [x] Keep pull-request validation on `pull_request` with no cloud credentials or protected Environment secrets and explicit least-privilege read-only permissions per job.
  - [x] Add executable fixtures for fork changes, modified workflows, malicious outputs, cache poisoning, generated injection, untrusted artifacts, reusable-workflow indirection, and failing required checks; prove none can reach a privileged job or satisfy its status.
  - [x] Sanitize logs, summaries, caches, and artifacts; prohibit unrestricted environment dumps, raw plan/CONFIG content, credentials, and executable trust-crossing artifacts. Any trusted reporting path must consume only bounded, non-executable results.
  - [x] Verify all workflow/action references remain full-SHA pinned and document approved managed-runtime exceptions.

- [x] Document operation, rollout, and rollback behavior (AC: 1, 4, 5, 9, 10)
  - [x] Update the validation README/runbook with target discovery, local reproduction commands, credential-free guarantees, artifact classification/retention, advisory-versus-blocking rollout policy, and migration/address review guidance.
  - [x] Document rollback as restoring the prior validator/workflow policy while preserving validation evidence; never restore cloud credentials or bypass required checks as a rollback mechanism.

## Dev Notes

### Scope and implementation boundary

Story 3.1 is the pull-request safety boundary for Epic 3. Extend the existing validator and workflow. Do not create a second CI framework, cloud-backed PR plan, privileged `pull_request_target` execution path, or workflow that executes untrusted checkout content with secrets. Trusted planning/OIDC/apply authority belongs to later Epic 3 stories and must remain separate.

Current implementation anchors:

- `scripts/validate.py` owns Terraform root discovery, credential sanitization, backend-free Terraform validation, Ruff/mypy/pytest/Checkov execution, hygiene, and stage-labelled failures.
- `scripts/validate.sh` owns the pinned `uv` lock/sync setup and invokes the repository validator with sanitized AWS settings.
- `.github/workflows/validate.yml` is the existing credential-free pull-request workflow; preserve its full-SHA Action pins, Terraform `1.15.8`, Python `3.14.6`, uv `0.11.29`, `pull_request` trigger, and read-only contents permission unless a reviewed change is required.
- `scripts/check_repository.py` owns committed-file, Terraform hygiene, credential, action-pin, and mutable-reference checks; extend it or its tests rather than duplicating scanners.
- `pyproject.toml` and `uv.lock` are the pinned Python dependency contract. Terraform lock files and the compatibility/contract manifests are normative inputs, not disposable generated output.

### Security and trust constraints

- No PR validation step may receive AWS keys, OIDC permission, protected Environment secrets, deployment manifest secrets, write tokens, or protected state access.
- Do not use `pull_request_target` to run source-controlled or fork-controlled code. Do not trust artifact names, caches, outputs, workflow commands, generated files, or reusable-workflow inputs without bounded validation and an explicit trust boundary.
- Keep `GITHUB_TOKEN` permissions explicit and read-only. A reporting job, if needed, must consume sanitized structured results and must not execute PR-controlled code.
- Validate action references by full 40-character commit SHA; validate provider lock checksums and dependency locks; keep immutable module/image requirements and documented managed-runtime exceptions.
- Preserve the project rule that secret exposure, invalid Terraform, formatting failures, generated state, saved plans, `.terraform/`, committed `.tfvars`, credentials, and prohibited artifacts block every Environment. Advisory rollout applies only to explicitly catalogued governance findings.

### Terraform and repository rules

- All roots/modules require Terraform `>= 1.10, < 2.0`; the tested seed is Terraform `1.15.8` and AWS provider `6.54.0`.
- Use `terraform fmt -check -recursive`, `terraform init -backend=false`, and `terraform validate`; use `-lockfile=readonly` where a target is intended to verify an existing lock without mutation.
- Preserve stable Terraform addresses. Any intentional move needs a reviewed `moved` block plus consumer migration guidance and an impacted-address report; do not use state inspection as an operator shortcut.
- Preserve private networking, least privilege, required tags, immutable references, encrypted storage/queues, explicit retention/alarms, and rollback documentation from `_bmad-output/project-context.md` and `_bmad/custom/standards/aws-terraform-implementation.md`.

### Testing and validation

- Add focused unit/contract fixtures for changed-target mapping, unknown changed paths, exact command diagnostics, lock/checksum drift, migration/address churn, workflow trust crossings, artifact leakage, staged severity, and all listed malicious PR scenarios.
- Run repository validation with the pinned toolchain and no credentials. Preserve stage labels and explicit exit status so registry/network, dependency, and code failures remain distinguishable.
- Existing deprecation warnings in the AWS provider are documented and non-blocking; do not hide warnings by weakening provider or Terraform validation.

### Project Structure Notes

- Keep validator logic under `scripts/`, CI under `.github/workflows/`, policy/hygiene fixtures under existing `tests/` locations, and operational guidance under `docs/runbooks/` or the relevant README.
- Do not add generated caches, `.terraform/`, state, saved plans, credentials, or local environment files to the repository.
- If a new catalog or contract is normative, update its manifest/release/checksum metadata and compatibility fixtures in the same change.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Epic 3 / Story 3.1]
- [Source: `_bmad-output/project-context.md` — Agent Operating Rules, CI/CD, Security, Terraform Quality Gates, Definition of Done]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md` — AD-15, AD-16, AD-17, AD-20, stack/version matrix, Terraform hygiene]
- [Source: `_bmad-output/implementation-artifacts/epic-2-retro-2026-07-28.md` — Epic 3 preparation and action items]
- [Source: `scripts/validate.py`, `scripts/validate.sh`, `scripts/check_repository.py`, `.github/workflows/validate.yml`, `pyproject.toml`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]
- [GitHub Docs: GITHUB_TOKEN](https://docs.github.com/en/actions/concepts/security/github_token)
- [GitHub Docs: Workflow syntax and fork permissions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
- [Terraform CLI init](https://developer.hashicorp.com/terraform/cli/commands/init)
- [Terraform CLI validate](https://developer.hashicorp.com/terraform/cli/commands/validate)

## Previous Story Intelligence

- Epic 2 retrospective: adversarial review found boundary defects late, so this story must include negative fixtures and exact failure diagnostics rather than only happy-path validation.
- Preserve the completed review workflow for every Epic 3 story: acceptance audit, adversarial review, edge-case review, and full pinned validation.
- Carry forward the action item to cover every affected Epic 3 target without silent skips.
- Track the documented AWS provider deprecation migration separately; do not mix it into this story unless required to make validation deterministic.

## Git Intelligence

- Recent implementation commits completed Epic 2 through focused runtime, contract, IAM, Terraform, documentation, and review fixes. Preserve that small-change pattern.
- The current branch already has a clean baseline and a passing credential-free validator; this story should improve target coverage and trust fixtures without broad unrelated refactoring.

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

- Story created from Epic 3 Story 3.1 and the Epic 2 retrospective.
- Existing validator, workflow, hygiene scanner, architecture decisions, and pinned toolchain were inspected before story creation.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Added conservative changed-path inventory and `VALIDATION_BASE_SHA` diagnostics to the existing credential-free validator; unknown paths select the full safety suite.
- Hardened pull-request workflow permissions to explicit read-only scopes and preserved `pull_request` execution without credentials, secrets, OIDC, or write tokens.
- Added workflow/target-discovery contract tests and credential-free validation runbook guidance.
- Full pinned validation passed: Terraform 1.15.8, uv 0.11.29, Ruff, mypy, 245 tests, 227 subtests, Checkov 118/796/98, and repository hygiene.
- Addressed review findings with per-path owner reporting, versioned rollout severity validation, migration/address churn checks, workflow-security fixtures, and PR artifact-safety enforcement.
- Revalidated after fixes: 248 tests, 235 subtests, Checkov 118/796/98, and repository hygiene passed.

## Change Log

- 2026-07-28: Implemented changed-target discovery, explicit PR permissions, validation fixtures, and credential-free validation documentation; moved story to review.
- 2026-07-28: Addressed adversarial review findings and reran the full pinned validation gate successfully.

### File List

- `_bmad-output/implementation-artifacts/3-1-expand-credential-free-pull-request-validation.md`
- `scripts/validate.py`
- `scripts/validate.sh`
- `scripts/check_repository.py`
- `.github/workflows/validate.yml`
- `tests/`
- `docs/runbooks/`
- `runtime/`
- `contracts/`
- `.github/workflows/validate.yml`
- `scripts/validate.py`
- `tests/contract/test_ci_workflow.py`
- `tests/contract/test_validation_targets.py`
- `docs/runbooks/pull-request-validation.md`
- `scripts/validation-rollout.json`
- `tests/contract/fixtures/workflow-security.json`

### Review Findings

- [ ] [Review][Patch] Changed-target inventory does not identify concrete affected Terraform roots or modules — AC 1/2 require every affected root, module, and module-local example to be identified with reproducible target commands, but `classify_changed_paths` emits only broad categories and the validator always runs the full root set without a per-root ownership map. [scripts/validate.py:46-111; scripts/validate.py:225-240]
- [x] [Review][Patch] Changed-target inventory did not identify concrete affected Terraform roots or modules — fixed by reporting every changed Terraform root alongside the broad validation owners. [scripts/validate.py:104-119; scripts/validate.py:278-290]
- [x] [Review][Patch] Migration validation missed module and non-resource address churn — fixed by analyzing resource, data, module, output, and variable block address changes and requiring explicit migration guidance or `moved` blocks. [scripts/validate.py:150-196]
- [x] [Review][Patch] Workflow-security fixtures were declarative rather than executable — fixed by deriving privileged-execution and required-status outcomes from the shared scanner rather than trusting fixture booleans. [scripts/validate.py:215-223; tests/contract/test_ci_workflow.py:89-98]
- [x] [Review][Patch] Artifact safety did not scan composite actions or reusable workflow trust crossings — fixed by applying the same artifact policy scanner to workflow files and composite action metadata. [scripts/validate.py:225-241]
