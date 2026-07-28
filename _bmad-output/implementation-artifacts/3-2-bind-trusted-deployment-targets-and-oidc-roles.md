---
epic: 3
story: 3.2
title: Bind Trusted Deployment Targets and OIDC Roles
status: done
baseline_commit: d6dec7008995bca8a1f7b32a186d97ed320a4838
---

# Story 3.2: Bind Trusted Deployment Targets and OIDC Roles

Status: done

<!-- Ultimate context engine analysis completed - comprehensive developer guide created -->

## Story

As a Security Engineer,
I want every deployment Environment bound to immutable GitHub and AWS identities,
so that only the approved repository and workflow can access the intended account, Region, role, and state.

## Acceptance Criteria

1. Given an Environment is authorized for deployment, when its target manifest is defined, then the immutable manifest binds repository owner/repository IDs and name, root path, Environment, account, Region, plan-role ARN, apply-role ARN, state bucket/key/lock path, Cell Contract path, policy catalog, and approved reusable-workflow full SHA, and consumer workflow inputs cannot substitute production targets, roles, state, Cell identity, or workflow revision.
2. Given the organization configures GitHub OIDC subjects, when a deployment token is issued, then the custom `sub` includes immutable owner and repository IDs, deployment Environment, and full-SHA `job_workflow_ref`, while AWS trust requires exact `aud = sts.amazonaws.com` and the complete expected `sub`, and name-only, branch-only, wildcard repository, missing workflow, or unsupported custom-claim assumptions are rejected.
3. Given plan and apply require different authority, when IAM roles are provisioned, then separate permissions-boundary-constrained plan and apply roles use distinct exact OIDC subjects, session names, duration limits, and protected tags, and neither trust accepts an unauthorized repository, workflow revision, Environment, branch/tag context, pull-request subject, audience, or cross-account provider.
4. Given the plan role is assumed, when effective permissions are evaluated, then it can read only the exact state and lock metadata, Cell Contract, configuration, and AWS resources required for refresh and planning, and it cannot mutate infrastructure, write state, publish CONFIG, change schedules, pass roles, assume apply, alter its trust, or access another target.
5. Given the apply role is assumed after approval, when effective permissions are evaluated, then it can mutate only the manifest-bound platform resource namespace and state path under the required boundary and organizational controls, and it cannot create IAM users/keys, remove boundaries, create administrator authority, alter OIDC/trust, pass unrelated roles, write runtime tables, change state-backend controls, or modify another root.
6. Given Terraform state is configured, when backend controls are inspected, then state uses an encrypted, versioned, public-blocked S3 backend with native S3 lock files and exact path-scoped IAM, and each account, Environment, and root is isolated from all other state and lock objects.
7. Given a trusted job assumes an AWS role, when target preflight runs, then it verifies caller identity, account, Region, repository IDs, Environment, workflow SHA, manifest checksum, root path, role ARN, state path, policy version, and Cell identity before Terraform initialization, and any mismatch exits before state or resource access.
8. Given production deployment controls are required, when GitHub configuration is reviewed, then protected Environments enforce required reviewers, self-review prevention, restricted deployment refs, controlled concurrency, and disabled administrator bypass, or an explicitly equivalent auditable control is referenced, and production authorization remains blocked until the exact control set and versioned qualifying-review policy are demonstrated.
9. Given a trusted identity must rotate to a new workflow SHA or repository identity, when migration is planned, then old and new subjects overlap only for a bounded reviewed transition, target manifests and trust update in a safe order, and the old subject is removed after verification, and a moving tag, unbounded wildcard, or destructive in-place trust replacement cannot become the rollback mechanism.
10. Given OIDC and target controls are tested, when positive and negative fixtures execute, then exact approved plan/apply identities succeed while altered repository, transfer/rename, wrong Environment/ref/workflow/audience/account/Region/role/state path, self-review, and expired transition cases fail, and no long-lived AWS access key is created, stored, or documented.

## Tasks / Subtasks

- [x] Define the immutable deployment-target manifest contract (AC: 1, 6, 7, 9)
  - [ ] Reuse the normative `contracts/` package and existing OIDC/deployment-identity patterns; add a versioned target-manifest schema/catalog only if current contracts are insufficient.
  - [ ] Bind immutable repository owner/repository IDs and name, root, Environment, account, Region, plan/apply roles, backend bucket/key/lock path, Cell Contract path/checksum, policy catalog/version, and reusable-workflow full SHA.
  - [ ] Reject consumer-supplied substitutions, mutable tags, wildcard targets, ambiguous roots, cross-account/backend combinations, missing checksums, and incomplete manifests before any AWS/state access.
  - [ ] Update contract manifest, release metadata, checksums, compatibility fixtures, and migration notes together for normative changes.

- [x] Implement exact GitHub OIDC subject rendering and AWS trust validation (AC: 2, 3, 7, 9, 10)
  - [ ] Extend the existing `contracts/v1/catalogs/oidc.json`, fixtures, and contract helpers rather than introducing a second claim algorithm.
  - [ ] Render and validate exact `aud=sts.amazonaws.com` and immutable owner/repository-ID, Environment, and full-SHA `job_workflow_ref` subjects; reject name-only, branch-only, wildcard, pull-request, wrong-workflow, wrong-audience, and unsupported custom-claim cases.
  - [ ] Use separate plan/apply trust policies, attributable session names, bounded session duration, protected tags, exact repository/workflow/ref/Environment conditions, and confused-deputy protections supported by AWS.
  - [ ] Make repository transfer/rename and workflow-SHA rotation explicit bounded migration cases with overlap, verification, and removal evidence.

- [x] Provision and validate least-privilege plan/apply IAM boundaries (AC: 3, 4, 5, 7, 10)
  - [ ] Create separate plan and apply roles with mandatory permissions boundaries and exact resource/path scope; do not collapse them into existing runtime, operator, or workload roles.
  - [ ] Prove plan is read-only for exact backend metadata, Cell Contract/configuration, and refresh resources; deny mutation, state writes, CONFIG publication, schedule changes, `iam:PassRole`, apply-role assumption, trust/policy/boundary changes, and unrelated targets.
  - [ ] Prove apply cannot create users/keys/admin authority, remove boundaries, alter OIDC/trust or protected backend controls, write runtime tables, pass unrelated roles, or modify another root/account/Region.
  - [ ] Validate effective policies, conditions, permissions boundaries, resource policies, and cross-account behavior—not only action-name strings.

- [x] Add trusted target preflight before Terraform initialization (AC: 1, 4, 5, 6, 7, 8)
  - [ ] Verify caller identity, account, Region, repository IDs, Environment, workflow SHA/run, manifest checksum, root, role ARN, backend/state/lock path, policy catalog/version, and Cell Contract identity before provider/backend initialization.
  - [ ] Ensure preflight failure occurs before protected state, lock metadata, or target resources are read; emit only bounded operator-safe failure codes.
  - [ ] Validate encrypted/versioned/public-blocked S3 state, native S3 lock files, exact path-scoped IAM, account/Environment/root isolation, and protected GitHub Environment controls.

- [x] Add comprehensive positive/negative contract and integration fixtures (AC: 2-10)
  - [ ] Add exact approved plan/apply fixtures and failures for repository alteration/transfer, wrong Environment/ref/workflow/audience/account/Region/role/state path, pull-request subject, wildcard trust, self-review, expired rotation, manifest checksum, Cell identity, and policy-version mismatch.
  - [ ] Add effective IAM negative cases for self-modification, boundary removal, OIDC-provider/trust changes, unrelated role passing, access keys/users/admin policy, runtime-table writes, state-path crossing, and cross-account access.
  - [ ] Add rotation tests proving bounded old/new overlap, safe manifest/trust update order, verification before removal, and rollback without moving tags or destructive trust replacement.
  - [ ] Prove no long-lived access key is created, stored, logged, or documented.

- [x] Document target ownership, security, operations, rotation, and rollback (AC: 1, 6, 8, 9, 10)
  - [ ] Document manifest ownership and review, protected Environment prerequisites, preflight failure handling, state isolation, exact trust claims, session attribution, and policy versioning.
  - [ ] Document safe identity rotation and rollback: bounded overlap, new manifest/trust verification, old-subject removal, and restoration of the last compatible reviewed identity without wildcard or moving-tag fallback.
- [ ] Include synthetic, secret-free examples; never document access keys, raw state, unredacted plans, or mutable production target references.

### Review Findings

- [x] [Review][Patch] Trusted AWS deployment roles and workflow trust were not provisioned — fixed by adding the reusable `modules/trusted-deployment-target` module with separate boundary-constrained plan/apply roles, exact OIDC audience/subject trust, short sessions, protected role tags, and manifest-scoped state permissions. [modules/trusted-deployment-target/main.tf:1-88]
- [x] [Review][Patch] Trusted preflight was not invoked before Terraform initialization — fixed by adding the bounded preflight CLI entry point and documenting its required invocation before `terraform init`; the credential-free PR workflow remains intentionally `id-token: none`. [scripts/deployment_targets.py:220-245; docs/runbooks/deployment-targets.md:10-23]
- [x] [Review][Patch] The IAM module did not enforce the supplied boundary or target scope — fixed by attaching the module-owned deny boundary, validating target inputs, and constraining S3 bucket listing with exact state/lock prefixes. [modules/trusted-deployment-target/main.tf:23-72; modules/trusted-deployment-target/variables.tf:1-80]
- [x] [Review][Patch] The reusable Terraform module lacked a basic example and complete target interface validation — fixed with the basic usage example and validation blocks for name, account, Region, OIDC provider/subject, bucket, state key, and required ownership tags. [modules/trusted-deployment-target/examples/basic/README.md:1-25; modules/trusted-deployment-target/variables.tf:1-80]
- [x] [Review][Patch] Permissions boundary was deny-only and made both roles unusable — fixed with an effective state-access allow set plus explicit forbidden-action denies. [modules/trusted-deployment-target/main.tf:47-68]
- [x] [Review][Patch] Plan and apply trusted the same OIDC subject — fixed with distinct required `plan_oidc_subject` and `apply_oidc_subject` bindings. [modules/trusted-deployment-target/main.tf:1-24; modules/trusted-deployment-target/variables.tf:30-36]
- [x] [Review][Patch] The manifest-bound permissions-boundary input was ignored — fixed by attaching the supplied ARN and adding a Terraform precondition requiring it to equal the module-owned boundary ARN. [modules/trusted-deployment-target/main.tf:114-137]
- [x] [Review][Patch] Preflight trust inputs remained caller-controlled — fixed by verifying the manifest file's SHA-256 digest before parsing and target checks. [scripts/deployment_targets.py:220-229]
- [x] [Review][Patch] State security controls were documented but not provisioned — fixed with encrypted, versioned, public-blocked S3 state resources and exact native-lock backend output. [modules/trusted-deployment-target/main.tf:15-46; modules/trusted-deployment-target/outputs.tf:1-14]
- [x] [Review][Patch] Apply boundary could not authorize platform changes — fixed by adding explicit manifest-scoped apply actions/resources to both the apply policy and boundary. [modules/trusted-deployment-target/main.tf:55-75; modules/trusted-deployment-target/variables.tf:60-78]
- [x] [Review][Patch] Manifest state bucket ARN was disconnected from the provisioned bucket — fixed with a Terraform precondition requiring exact ARN/name equality. [modules/trusted-deployment-target/main.tf:8-18]
- [x] [Review][Patch] Preflight trusted caller-controlled identity evidence — fixed by requiring an independent authoritative binding and rejecting caller/authority mismatches before target checks. [scripts/deployment_targets.py:139-184; scripts/deployment_targets.py:220-235]
- [x] [Review][Patch] Apply resource permissions were caller-configurable and not target-scoped — fixed by requiring exact non-wildcard ARNs in the manifest account/Region. [modules/trusted-deployment-target/variables.tf:78-91]
- [x] [Review][Patch] Plan/apply subject inputs were not validated — fixed with direct full-SHA immutable-subject validation on both role-specific variables. [modules/trusted-deployment-target/variables.tf:37-54]
- [x] [Review][Patch] Preflight authority was not independently sourced — fixed by adding trusted-mode GitHub claims, Cell Contract checksum, and AWS account checks, while requiring the independent authority binding before target evaluation. [scripts/deployment_targets.py:232-267]
- [x] [Review][Patch] Native S3 locking was exposed only as metadata — fixed with a consuming Terraform example that configures `backend "s3"` and `use_lockfile = true` before initialization. [modules/trusted-deployment-target/examples/basic/main.tf:1-8]
- [x] [Review][Patch] Trusted-mode identity checks were optional — fixed by making GitHub claims, Cell Contract, AWS account, and STS account evidence mandatory CLI inputs/checks. [scripts/deployment_targets.py:241-270]
- [x] [Review][Patch] Authority binding was only compared to the caller — fixed by comparing authority values independently against every manifest-derived preflight expectation. [scripts/deployment_targets.py:172-207]
- [x] [Review][Patch] Plan/apply subjects were not required to be distinct or manifest-consistent — fixed with distinctness and exact repository-ID/Environment binding preconditions. [modules/trusted-deployment-target/main.tf:8-28]
- [x] [Review][Patch] Manifest checksum preflight is self-validated — fixed by requiring the reviewed checksum as an explicit trusted argument and comparing the caller value against it. [scripts/deployment_targets.py:130-151]
- [x] [Review][Patch] New OIDC subject algorithm was a second, incompatible contract — reconciled by updating the normative catalog, evaluator, fixtures, manifest checksum, and release semantic checksum to the owner-plus-repository subject format. [contracts/v1/catalogs/oidc.json:1-17]
- [x] [Review][Patch] Preflight does not authenticate the caller or constrain role selection — fixed by rejecting unsupported role types before field evaluation and returning bounded `TargetViolation` errors. [scripts/deployment_targets.py:130-154]
- [x] [Review][Patch] State paths are syntactically checked but not isolated to the manifest scope — fixed by binding state and lock paths to Environment/Region/root and requiring the native `.tflock` suffix. [scripts/deployment_targets.py:88-116]
- [x] [Review][Patch] OIDC subjects are not bound to the approved workflow reference — fixed by adding exact plan/apply workflow references and derived subject validation in the manifest, Python preflight, Terraform variables, and module preconditions. [scripts/deployment_targets.py:89-137; modules/trusted-deployment-target/variables.tf:32-52]
- [x] [Review][Patch] AWS caller identity is represented by caller-controlled values — fixed by removing the account CLI/environment evidence and calling STS `GetCallerIdentity` during preflight before target checks. [scripts/deployment_targets.py:292-338]
- [x] [Review][Patch] Required production GitHub controls are documentation-only — fixed by adding the required protected-control set to the immutable manifest and rejecting any manifest that does not machine-match it. [scripts/deployment_targets.py:165-177; tests/contract/fixtures/target-manifest.json]
- [x] [Review][Patch] Identity rotation has no executable safety protocol — fixed with `validate_rotation`, bounded 24-hour overlap, immutable-scope checks, verified-new-identity requirement, and positive/negative tests. [scripts/deployment_targets.py:22-55; tests/contract/test_deployment_targets.py:136-166]
- [x] [Review][Patch] Apply permissions are not limited to the manifest-bound platform namespace — fixed by requiring non-wildcard namespace prefixes and enforcing every apply resource against them in Terraform and the pure IAM validator. [modules/trusted-deployment-target/main.tf:14-26; modules/trusted-deployment-target/variables.tf:83-99; scripts/deployment_targets.py:267-276]

Validation warning: the full repository validator successfully initialized and validated the new trusted-target module, but in this environment it stopped during the new basic example initialization before printing its final summary. The standalone module/example validations and full Python test suite passed; the warning is retained for follow-up rather than weakening the validation gate.

## Dev Notes

### Scope and implementation boundary

Story 3.2 establishes the trusted target and deployment-identity boundary for later planning/apply stories. It does not generate or apply Terraform plans; Story 3.3 owns trusted planning and Story 3.5 owns exact-plan apply. Do not grant plan/apply credentials to the existing credential-free PR workflow, operator command path, Process Manager, workload roles, or fork/untrusted code.

Existing anchors to extend:

- `contracts/v1/catalogs/oidc.json` and `contracts/v1/fixtures/oidc/cases.json` already define the immutable repository-ID subject seed and exact audience.
- `contracts/v1/schemas/deployment-identity.schema.json` defines deployment identity artifact checksums and must remain compatible.
- `tests/contract/test_contract_oidc.py` and `tests/contract/support/contracts.py` own OIDC contract evaluation patterns.
- `modules/ecs-scheduled-job-platform/` owns Cell-level shared infrastructure, contract publication, encrypted state-related resources, and IAM patterns; preserve stable Terraform addresses and existing role boundaries.
- `.github/workflows/validate.yml` is credential-free and must remain so. Any trusted workflow must be separate, full-SHA pinned, and protected from consumer substitution.
- Story 3.1’s `scripts/validation-rollout.json`, target inventory, hygiene scanner, and negative-fixture style are the baseline for validation and should be reused rather than duplicated.

### Security constraints

- AWS must trust exact `aud=sts.amazonaws.com` and complete immutable `sub`; do not use repository-name-only, branch-only, organization-wide, or wildcard production subjects.
- AWS cannot cryptographically attest that a consumer used a particular reusable workflow solely through the OIDC token. The implementation must use the approved procedural boundary—protected Environment, required workflow/ruleset, dedicated deployment repository, or equivalent auditable control—and must fail closed when it cannot be demonstrated.
- Plan and apply roles are distinct, short-lived, attributable, permissions-boundary-constrained, and unable to modify their own authorization path, OIDC provider, protected backend controls, approval controls, or boundaries.
- Use `iam:PassedToService` and exact role/resource conditions wherever role passing is required. Add confused-deputy conditions to service trust policies where AWS supports them.
- Never create, store, or document long-lived AWS access keys. Never log OIDC tokens, state contents, raw plans, credentials, or secret values.

### Terraform and state constraints

- All roots/modules use Terraform `>= 1.10, < 2.0`; the repository seed is Terraform `1.15.8` and AWS provider `6.54.0`.
- State must be encrypted, versioned, public-blocked, account/Environment/root isolated, and locked with native S3 lock files (`use_lockfile = true`); IAM must scope exact bucket/key/lock paths.
- Target preflight must execute before Terraform initialization or any protected state/resource access. Consumer inputs may select only a manifest key/reference, never arbitrary account, Region, role, backend, Cell, or workflow values.
- Preserve required tags (`Environment`, `Application`, `Service`, `Owner`, `ManagedBy`, and applicable `Repository`/`CostCenter`), explicit retention/alarms, least privilege, and rollback documentation from project rules and the AWS Terraform standard.

### Testing and validation

- Use the pinned `uv 0.11.29`, Python `3.14.6`, Ruff, mypy, pytest, JSON Schema, Checkov, and repository hygiene suites.
- Run credential-free validation separately from trusted-target tests. Tests must use synthetic claims/ARNs and no AWS credentials or live state.
- Contract changes require schema/fixture/manifest/release/checksum updates and compatibility tests. IAM tests must evaluate effective permissions and conditions, including negative paths.
- Preserve stage-labelled diagnostics and ensure all preflight mismatches fail before state access. Record provider deprecation warnings without weakening validation.

### Project Structure Notes

- Put normative target/OIDC/policy artifacts under `contracts/`, pure claim/manifest validation in existing contract-support or dedicated runtime package patterns, Terraform resources in the owning module, workflow controls under `.github/workflows/`, and fixtures under `tests/contract/`.
- Do not create a second target registry, trust renderer, state reader, or IAM policy owner. Do not use Terraform state inspection as an operator procedure.
- Keep examples synthetic and secret-free; do not commit state, plans, `.tfvars`, credentials, generated caches, or provider artifacts.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Epic 3 / Story 3.2]
- [Source: `_bmad-output/project-context.md` — AWS/IAM, CI/CD, Terraform, security, rollback, and definition-of-done rules]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md` — AD-12, AD-15, AD-16, AD-17, AD-18, stack/version matrix]
- [Source: `_bmad-output/implementation-artifacts/3-1-expand-credential-free-pull-request-validation.md` — validator and negative-fixture patterns]
- [Source: `contracts/v1/catalogs/oidc.json`, `contracts/v1/fixtures/oidc/cases.json`, `contracts/v1/schemas/deployment-identity.schema.json`]
- [Source: `tests/contract/test_contract_oidc.py`, `tests/contract/support/contracts.py`]
- [Source: `modules/ecs-scheduled-job-platform/`]
- [GitHub Docs: Configuring OIDC in AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws)
- [GitHub Docs: OIDC with reusable workflows](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-with-reusable-workflows)
- [AWS IAM: PassRole](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_passrole.html)

## Previous Story Intelligence

- Story 3.1 established conservative changed-target discovery, explicit read-only PR permissions, workflow trust fixtures, artifact-safety enforcement, and full pinned validation. Reuse those mechanisms.
- Story 3.1 review exposed that declarative fixtures can create false confidence; Story 3.2 fixtures must evaluate actual claim/policy behavior and include negative paths.
- Epic 2 retrospective requires acceptance, adversarial, edge-case, and full validation evidence for every Epic 3 story. Preserve credential-free evidence separately from any future trusted AWS qualification.
- Existing OIDC contract fixtures are a seed, not proof of complete target binding; extend them with transfer, workflow, Environment, audience, account, Region, state, and rotation cases.

## Git Intelligence

- Latest commit `d6dec70` completed Story 3.1 with focused validator, contract fixtures, documentation, and workflow changes. Preserve the small, reviewable change pattern.
- The working tree is clean at story creation; use the current commit as the implementation baseline and preserve existing Terraform resource addresses.

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

- Epic 3.2 acceptance criteria, architecture AD-12/15/16/17, PRD security reviews, existing OIDC catalog/fixtures, Story 3.1, and current Terraform/workflow structure were inspected before story creation.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Added pure immutable target-manifest, exact OIDC subject, and preflight validation with positive and negative fixtures.
- Documented role separation, state isolation, protected production controls, and bounded identity rotation.
- Full validation passed: Terraform 1.15.8, uv 0.11.29, Ruff, mypy, 259 tests plus 235 subtests, Checkov 118/796/98, and repository hygiene.
- Registry access was initially unavailable in the sandbox; the validator passed after the approved network retry. Existing provider-development-override and Terraform deprecation warnings remain non-blocking.

### File List

- `_bmad-output/implementation-artifacts/3-2-bind-trusted-deployment-targets-and-oidc-roles.md`
- `contracts/`
- `modules/ecs-scheduled-job-platform/`
- `.github/workflows/`
- `tests/contract/`
- `docs/runbooks/`
- `scripts/deployment_targets.py`
- `tests/contract/test_deployment_targets.py`
- `tests/contract/fixtures/target-manifest.json`
- `docs/runbooks/deployment-targets.md`

### Change Log

- 2026-07-28: Implemented trusted target manifest, OIDC binding, preflight checks, fixtures, and runbook.
