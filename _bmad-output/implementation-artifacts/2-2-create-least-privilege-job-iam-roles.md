---
baseline_commit: d094252b2e1c7962663303321dfc3c3a8ce47201d
---

# Story 2.2: Create Least-Privilege Job IAM Roles

Status: done

## Story

As a Security Reviewer,
I want each scheduled job to use separate, reviewable roles with bounded authority,
so that launch, ECS execution, and application access cannot combine into an escalation path.

## Acceptance Criteria

1. Given a reserved job identity and approved permissions boundary, when IAM resources are planned, the module creates distinct job-launch, ECS task-execution, and application-task roles under the platform-managed role path; every role has protected ownership tags, the mandatory boundary, predictable naming, and no permissions beyond its responsibility.
2. Given the Process Manager must assume the job-launch role, when launch-role trust is rendered, only the exact stable Process Manager principal for the target Cell major is trusted with the narrowest supported source-account and Cell conditions; GitHub, humans, Scheduler, ECS tasks, unrelated Lambdas, cross-account principals, and stale Cell roles cannot assume it.
3. Given the launch role invokes ECS, when its policy is evaluated, `ecs:RunTask` is restricted to the intended task-definition family/revision scope and exact ECS cluster, and `iam:PassRole` is restricted to this job’s execution and application roles with `iam:PassedToService = ecs-tasks.amazonaws.com`; any ECS-required family-revision wildcard is isolated, documented, and denied outside the canonical family.
4. Given ECS pulls the immutable image, writes logs, and injects agent-managed secrets, when the execution policy is rendered, it grants only required ECR image-pull actions, the exact derived job log-group scope, exact approved Secrets Manager or SSM references, and required KMS permissions; the AWS-required ECR authorization-token wildcard is isolated and documented.
5. Given the application needs AWS API access, when explicit application policy statements are supplied, they attach only to the application-task role and remain inspectable with statement identity, action, resource, and condition preserved; invalid statements, IAM self-management, role passing, boundary changes, trust mutation, OIDC changes, Terraform/runtime control-plane access, ledger writes, cross-job CONFIG access, and administrator-equivalent authority fail validation.
6. Given application permissions contain wildcard, cross-account, or escalation-sensitive authority, when non-production policy analysis runs, findings use the versioned policy catalog’s advisory or blocking severity and identify remediation; the same authority remains production-blocking unless a later governed exception supplies owner, scope, justification, approver, expiry, and compensating control.
7. Given a customer-managed policy attachment is requested, when validation runs, it must be same-account, explicitly allowlisted, version-governed, compatible with the required boundary, and included in effective-policy analysis; AWS-managed, cross-account, unapproved, or externally mutable attachments are rejected.
8. Given ECS-agent secret injection is configured, when policies are generated, only the execution role receives exact secret and KMS decrypt access required by the references; secret values never enter inputs, task environment variables, CONFIG, plans, outputs, fixtures, or documentation.
9. Given approved application-pull secret mode is selected, when policies are generated, only the application-task role receives exact secret and KMS access, and the declaration identifies the required network path; cross-account, customer-managed KMS, or external-platform access fails without explicit resource, key, trust, and network-policy validation.
10. Given ECS assumes the execution or application role, when trust policies are analyzed, trust is limited to `ecs-tasks.amazonaws.com`, the target account, and the narrowest supported source-resource condition; named positive and negative confused-deputy fixtures prove correct source-account/source-ARN handling.
11. Given IAM validation executes, when static analysis, effective-policy analysis, and negative tests run, approved workload actions succeed while user/key creation, administrator policies, boundary removal, trust mutation, unrelated `iam:PassRole`, OIDC changes, ledger writes, cross-job CONFIG access, and self-modification fail; every unavoidable wildcard or standards deviation is documented at the exact statement.
12. Given role resources change, when module tests and migration checks run, stable role addresses, trust principals, policy statement identities, boundary attachment, and output types are preserved or accompanied by reviewed migration guidance; rollback restores prior compatible policies without deleting roles referenced by task definitions or CONFIG.

## Tasks / Subtasks

- [x] 1. Extend the job module IAM interface and canonical role identity (AC: 1, 2, 3, 12)
- [x] Add typed, described, validated inputs for the approved permissions boundary, stable Cell-major Process Manager role, ECR repository, secret mode, optional KMS/network-path metadata, and governed customer-managed policy attachments.
- [x] Derive stable role names and the platform-managed path from the reserved job identity and Cell ID; preserve the `JOB#<job_id>` ownership binding and use protected tags from Story 2.1.
- [x] Validate account/Region/path/ARN alignment and fail closed for production, missing boundary, stale Process Manager identity, cross-account inputs, mutable image references, and invalid secret references.
- [x] Preserve existing module addresses and outputs; document any new address or output migration explicitly.

- [x] 2. Create the three separate job-owned roles (AC: 1, 2, 10)
  - [x] Create exactly `launch`, `execution`, and `task` roles in `modules/ecs-scheduled-job`, each with the mandatory permissions boundary, platform-managed IAM path, predictable name, and protected tags.
  - [x] Render launch trust for only the exact Cell Process Manager role and supported account/Cell conditions; do not trust GitHub, humans, Scheduler, ECS tasks, arbitrary Lambda principals, cross-account roots, or stale role IDs.
  - [x] Render execution/task trust for `ecs-tasks.amazonaws.com` with `aws:SourceAccount` and the AWS-supported `aws:SourceArn` pattern for the target Region/account; do not falsely claim cluster-specific source ARN narrowing if ECS does not support it.

- [x] 3. Render least-privilege launch policy (AC: 3, 11)
- [x] Allow only `ecs:RunTask` for the canonical job task-definition family/revision strategy with an exact `ecs:cluster` condition.
- [x] Allow only `iam:PassRole` for this job’s execution and task role ARNs with `iam:PassedToService = ecs-tasks.amazonaws.com`.
- [x] Avoid `ecs:DescribeTasks`/`ecs:ListTasks` unless a separately justified catalog entry requires them; add negative tests for unrelated actions, families, clusters, accounts, and roles.
- [x] If a family revision wildcard is required before Story 2.4 creates the task definition, isolate it in a named statement constrained to the canonical family and document the reason.

- [x] 4. Render execution-role policy and secret-mode isolation (AC: 4, 8, 9)
- [x] Scope ECR pull actions to the approved repository and isolate `ecr:GetAuthorizationToken` on `Resource = "*"` with an exact AWS-required-wildcard explanation.
- [x] Scope log writes to the deterministic `/platform/jobs/<job_id>` log-group ARN pattern without creating the log group before Story 2.4.
- [x] For ECS-agent secret mode, grant only exact Secrets Manager/SSM read and KMS decrypt permissions to the execution role, with encryption-context/ViaService conditions where supported.
- [x] For application-pull mode, keep those permissions exclusively on the task role and emit the required network-path declaration for Story 2.3 without creating networking here.
- [x] Prohibit secret values in all module inputs, plans, outputs, examples, docs, CONFIG shapes, and logs.

- [x] 5. Render reviewable application permissions and governed attachments (AC: 5, 6, 7, 11)
- [x] Extend the existing structured `permissions` input with stable statement IDs and explicit action/resource/condition semantics; attach inline statements only to the task role.
- [x] Reject IAM user/key creation, administrator or wildcard escalation, `iam:PassRole`, trust/boundary/OIDC mutation, Terraform/runtime control-plane access, ledger writes, cross-job CONFIG access, and self-modification.
- [x] Add same-account, allowlisted, version-pinned customer-managed policy attachments only; reject AWS-managed, cross-account, unapproved, externally mutable, wrong-version, and boundary-incompatible policies.
- [x] Classify policy findings with the checked-in policy catalog; do not silently approve production exceptions owned by Story 3.4.

- [x] 6. Add effective-policy and IAM negative fixtures (AC: 2-11)
  - [x] Reuse the existing contract IAM evaluator and fixtures through the repository contract test suite; no parallel evaluator was introduced.
  - [x] Add job-module contract tests proving role separation, trust, exact RunTask/PassRole, exact ECR/log/secret/KMS scopes, statement identity preservation, and secret-free outputs.
  - [x] Cover negative principal/account/source, boundary, cross-job, unrelated PassRole, wrong service, wildcard trust, administrator, IAM self-management, OIDC, ledger/CONFIG, and secret-mode leakage through validation guards and static negatives.
  - [x] Add static tests proving no future-story resources or Cell-owned resources are created.

- [x] 7. Add safe outputs, documentation, migration, and rollback evidence (AC: 1, 9, 12)
  - [x] Expose role ARNs and immutable role IDs, boundary ARN, role path, policy statement identities/version, secret mode, and effective-policy compatibility evidence without secrets.
  - [x] Update the job README with purpose, ownership, inputs, outputs, role responsibilities, trust conditions, wildcard exception, secret modes, policy catalog, observability handoff, validation, and rollback.
  - [x] Record that denied AssumeRole/PassRole, secret retrieval, and task execution signals are consumed by later operational stories; do not create alarms or dashboards here.
  - [x] Document rollback as policy restoration while retaining roles referenced by future task definitions/CONFIG; never delete roles or enable schedules as part of rollback.

- [x] 8. Run the complete validation and migration gates (AC: 6, 11, 12)
  - [x] Run module and basic-example Terraform format, backend-free init, and validate.
  - [x] Run Ruff, strict mypy, repository contract/runtime tests, IAM positive/negative/effective-policy tests, secret/hardcoding scans, Checkov, hygiene, and `git diff --check`.
  - [x] Keep credential-free validation separate from any live AWS qualification; do not claim deployed IAM enforcement from local tests.

### Review Findings

- [x] [Review][Patch] Boundary approval is only validated by account and `platform-` naming, not against the exact Cell-approved boundary policy [modules/ecs-scheduled-job/main.tf:122-130] — fixed by publishing and requiring the exact boundary ARN in the Cell Contract.
- [x] [Review][Patch] Secret references are not constrained to the target account, Region, or partition [modules/ecs-scheduled-job/variables.tf:150-159; modules/ecs-scheduled-job/iam.tf:58-60] — fixed with target identity preconditions.
- [x] [Review][Patch] Application policy validation does not reject wildcard actions/resources or cross-account resources, and catalog findings are generic output only [modules/ecs-scheduled-job/variables.tf:239-249; modules/ecs-scheduled-job/iam.tf:61-70] — fixed with wildcard/resource guards and versioned task-catalog blocking checks.
- [x] [Review][Patch] Application statement IDs are not unique and actions/resources may be empty [modules/ecs-scheduled-job/variables.tf:231-249; modules/ecs-scheduled-job/iam.tf:198-204] — fixed with nonempty action/resource and unique-ID validation.
- [x] [Review][Patch] Governed customer-managed attachments are not version-pinned or actually analyzed [modules/ecs-scheduled-job/variables.tf:261-276; modules/ecs-scheduled-job/iam.tf:259-270] — fixed with approved version/digest inputs, effective-policy digest checks, and output evidence.
- [x] [Review][Patch] Customer-managed attachments always target the task role, including `ecs-agent` mode [modules/ecs-scheduled-job/iam.tf:266-270] — fixed by rejecting attached secret/KMS permissions in ECS-agent mode.
- [x] [Review][Patch] The immutable image digest is not checked against the approved ECR repository [modules/ecs-scheduled-job/variables.tf:91-96,181-186] — fixed with an image/ECR repository identity precondition.

## Dev Notes

### Current state and implementation boundary

- Story 2.1 leaves `modules/ecs-scheduled-job` declaration-only and explicitly defers IAM. Story 2.2 is the first story allowed to create job-owned IAM roles and inline policies.
- The job root owns the three per-job roles. The Cell root owns the Process Manager, permissions-boundary policy, shared queues/ledgers/processors, and Cell Contract. Do not move Cell-owned IAM or shared resources into the job module.
- Story 2.2 creates no task definition, log group, security group, networking, schedule, CONFIG object, alarm, dashboard, or activation. Stories 2.3–2.5 consume the role outputs.
- `RESERVED` remains an ownership state. IAM role creation must not grant launch authority to the consumer apply role; only the exact Process Manager principal may assume the launch role.

### Reuse these repository patterns

- `fixtures/canary/main.tf:49-168` — role separation, policy-document structure, permissions boundaries, ECR pull, log scope, and isolated ECR auth-token wildcard. Tighten its trust conditions and remove unneeded reconciliation permissions rather than copying them blindly.
- `modules/ecs-scheduled-job-platform/main.tf:744-749` — stable platform-managed role path `/platform/ecs-scheduled-jobs/<cell-id>/v1/`, mandatory boundary, and protected tags.
- `modules/ecs-scheduled-job-platform/main.tf:446-449` and the Cell Contract — stable `process_manager` integration. The approved permissions boundary is a Cell/platform input and must be validated against the target account and policy path; do not discover it through remote state.
- `contracts/v1/catalogs/iam.json:33-44` — normative execution/job-launch action, resource, trust, condition, and boundary expectations.
- `contracts/v1/catalogs/ownership.json:43-51` — job-launch role Terraform ownership and Process Manager producer boundary.
- `contracts/v1/fixtures/iam/cases.json` and `tests/contract/support/contracts.py:evaluate_iam_case` — canonical IAM cases and structured denial codes.
- `tests/contract/test_contract_iam.py` and `tests/contract/test_canary_fixture.py` — existing test harnesses and static assertion style.
- `scripts/check_repository.py` — repository-wide secret, mutable-image, state, provisioner, and Terraform hygiene scanner.

### Role contract

- Role names: `${environment}-${application}-${job}-launch`, `-execution`, and `-task`, subject to IAM name/path limits and stable derived-name rules.
- Role path: `/platform/ecs-scheduled-jobs/${cell_id}/v1/` unless the existing Compatibility Package establishes a more specific immutable path; any deviation requires explicit migration guidance.
- Protected tags: `Environment`, `Application`, `Service`, `Owner`, `ManagedBy`, `Repository`, and applicable `CostCenter`. Consumer tags cannot override them.
- Launch trust: exact stable Process Manager role ARN/Role ID from the validated Cell Contract, target account and Cell conditions, no stale role aliases.
- Execution/task trust: `ecs-tasks.amazonaws.com`, `aws:SourceAccount` equal to the target account, and `aws:SourceArn` using the AWS-supported `arn:<partition>:ecs:<region>:<account>:*` pattern because ECS does not support narrowing this condition to one cluster.
- Launch policy: only canonical-family `ecs:RunTask` and exact execution/task `iam:PassRole`; `iam:PassedToService` must equal `ecs-tasks.amazonaws.com`.
- Execution policy: ECR pull, exact job log stream writes, and only the selected ECS-agent secret/KMS references. ECR authorization-token `Resource = "*"` is the sole expected service-required wildcard and must be isolated/documented.
- Task policy: explicit application permissions and application-pull secret/KMS references only; it must never receive launch, PassRole, boundary, trust, OIDC, Terraform, ledger, or cross-job CONFIG authority.

### Policy and secret safety

- A permissions boundary limits maximum role permissions but grants no permissions by itself; every role still needs its own identity policy. Effective-policy tests must evaluate identity policy ∩ boundary, trust policy, and approved attachments.
- Keep statement IDs stable. They are part of review/migration evidence and must not be generated from unordered maps.
- Secret references are locators only. Never accept `name=value`, secret values, decrypted SSM values, or credentials. Keep ECS-agent and application-pull modes mutually exclusive and test that the non-selected role receives no secret/KMS permission.
- Customer-managed attachments require explicit same-account allowlisting, immutable policy version/governance, boundary compatibility, and inclusion in effective-policy analysis. Do not attach AWS-managed policies by default.

### Cross-story handoffs

- Story 2.3 consumes secret-mode/network-path outputs and owns private subnet/security-group enforcement.
- Story 2.4 consumes execution/task role ARNs and owns task definition, log group, retention, structured logs, and runtime configuration.
- Story 2.5 owns Scheduler delivery role, disabled schedule, CONFIG publication, and apply-role boundaries; it must not duplicate these three roles.
- Story 2.6 binds actual immutable Role IDs and permissions into Cell acknowledgement/validation.
- Story 3.4 owns production policy enforcement and governed exceptions; Story 2.2 may classify but cannot approve production exceptions.

### Project and AWS Terraform standards

- Use Terraform `>= 1.10, < 2.0` and AWS provider `>= 6.0, < 7.0` with the committed lock convention.
- Every new variable/output needs a description and meaningful validation. Avoid hardcoded account IDs, Regions, ARNs, secrets, `.tfvars`, provisioners, `null_resource`, and remote state.
- Preserve stable resource addresses, role names, paths, policy statement IDs, boundaries, and output types. Use reviewed `moved` blocks or migration notes for intentional changes.
- Document validation and rollback. IAM denied actions and failed role assumptions are operational handoffs, not a reason to add observability resources early.

## Testing Requirements

Minimum evidence before review:

1. Positive/negative Terraform module tests for all new IAM inputs and role identity.
2. Rendered trust-policy tests for exact Process Manager and ECS principals, source-account/source-ARN conditions, and rejected confused-deputy variants.
3. Rendered launch-policy tests for exact cluster/family RunTask and execution/task-only PassRole.
4. Execution-policy tests for ECR, log, secret, and KMS scope, including both secret modes and the isolated ECR wildcard.
5. Application-policy and attachment tests for statement identity, catalog classification, boundary intersection, effective permissions, and every named escalation denial.
6. Static tests proving no future-story resources or Cell-owned resources are created.
7. Backend-free Terraform init/validate for the module and `examples/basic`.
8. Ruff format/check, strict mypy, pytest/contract/runtime tests, Checkov, repository hygiene, and `git diff --check`.

Tests must use synthetic ARNs and fake policy inputs. They must not claim live IAM enforcement, deployed role assumption, secret retrieval, ECS launch, or AWS policy analysis unless separately credentialed qualification tests perform those actions.

## References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-2.2-Create-Least-Privilege-Job-IAM-Roles`]
- [Source: `_bmad-output/planning-artifacts/epics.md#Epic-2-Run-a-Secure-Scheduled-Job-in-Non-Production`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-12-Explicit-IAM-Boundaries`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-15-Terraform-State-and-Cell-Discovery`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-20-Delivery-and-Operator-Authority`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-23-Checked-in-Compatibility-Package`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-25-Single-Terraform-Owner-per-Integration-Edge`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-28-Globally-Registered-Job-Ownership`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-29-Publish-Validate-Materialize-Enable-Handshake`]
- [Source: `_bmad-output/planning-artifacts/prds/prd-demo-bmad-2026-07-13/prd.md#FR-10-Separate-IAM-Responsibilities`]
- [Source: `_bmad-output/planning-artifacts/prds/prd-demo-bmad-2026-07-13/prd.md#FR-11-Declare-Application-Permissions-Explicitly`]
- [Source: `_bmad-output/planning-artifacts/prds/prd-demo-bmad-2026-07-13/prd.md#FR-12-Reference-Secrets-Safely`]
- [Source: `_bmad-output/planning-artifacts/prds/prd-demo-bmad-2026-07-13/prd.md#FR-13-Require-Private-Task-Networking`]
- [Source: `_bmad-output/implementation-artifacts/2-1-declare-and-reserve-a-scheduled-job.md`]
- [Source: `_bmad-output/implementation-artifacts/epic-1-retro-2026-07-22.md`]
- [Source: `contracts/v1/catalogs/iam.json`]
- [Source: `contracts/v1/catalogs/ownership.json`]
- [Source: `contracts/v1/fixtures/iam/cases.json`]
- [Source: `fixtures/canary/main.tf`]
- [Source: `modules/ecs-scheduled-job-platform/main.tf`]
- [Source: `tests/contract/support/contracts.py`]
- [Source: `tests/contract/test_contract_iam.py`]
- [Source: `tests/contract/test_canary_fixture.py`]
- [Source: `_bmad-output/project-context.md`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]
- [AWS permissions boundaries](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html)
- [Amazon ECS task IAM roles](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html)
- [Amazon ECS task execution IAM role](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html)
- [Terraform IAM role resource](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role)

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Added IAM resources in a dedicated `iam.tf` to preserve the Story 2.1 declaration boundary while introducing only the three approved job roles.
- The repository validator required `uv==0.11.29`; validation used that pinned tool in a temporary directory. The individual Terraform, test, lint, type, Checkov, and hygiene gates were also run directly.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story 2.1 review-hardening requirements and Epic 1 retrospective action items incorporated.
- Current baseline is commit `d094252b2e1c7962663303321dfc3c3a8ce47201d`.
- Implemented stable launch/execution/task role identities, Cell Process Manager/ECS trust guards, mandatory boundaries, protected tags, exact launch and execution policies, isolated ECR authorization wildcard, secret-mode isolation, task-only application permissions, governed attachment inputs, safe role outputs, and rollback documentation.
- Validation evidence: `192 passed, 216 subtests passed`; Terraform module and basic example validate; Ruff format/lint, strict mypy, Checkov (`80 passed, 0 failed` for the job module), repository hygiene, and `git diff --check` pass. Checks are credential-free and do not claim live AWS enforcement.
- Code review remediation completed: Cell boundary contract publication, target-identity ARN guards, catalog-backed permission blocking, unique statement IDs, attachment digest/effective-policy checks, ECS-agent attachment isolation, and image/ECR repository matching.

### File List

- `_bmad-output/implementation-artifacts/2-2-create-least-privilege-job-iam-roles.md`
- `modules/ecs-scheduled-job/variables.tf`
- `modules/ecs-scheduled-job/main.tf`
- `modules/ecs-scheduled-job/outputs.tf`
- `modules/ecs-scheduled-job/README.md`
- `modules/ecs-scheduled-job/examples/basic/main.tf`
- `modules/ecs-scheduled-job/iam.tf`
- `tests/contract/test_repository_structure.py`
- `tests/contract/test_scheduled_job_declaration.py`
- `tests/contract/test_scheduled_job_iam.py`
- `modules/ecs-scheduled-job-platform/main.tf`
- `contracts/v1/schemas/cell-contract.schema.json`
- `contracts/manifest.json`
- `contracts/releases/1.0.0.json`

### Change Log

- 2026-07-23: Created comprehensive Story 2.2 implementation context.
- 2026-07-23: Implemented least-privilege job IAM roles, secret-mode isolation, policy validation, contract tests, outputs, documentation, and rollback evidence; moved story to review.
