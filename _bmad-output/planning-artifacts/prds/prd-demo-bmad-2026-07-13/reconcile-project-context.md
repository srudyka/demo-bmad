# Reconciliation: Project Context

## Input

- Source: `_bmad-output/project-context.md`
- Compared with: `prd.md` and `addendum.md`
- Review focus: AWS, Terraform, CI/CD, security, IAM, observability, reliability, rollback, documentation, and definition of done

## Verdict

The PRD and addendum substantially preserve the repository's DevOps/SRE-first standards. The AWS runtime, least-privilege role separation, private networking, secrets model, Terraform delivery stages, production approval, immutable images, observability, runbooks, versioning, and rollback principles are aligned. One material contradiction and four incomplete requirements should be resolved before finalization.

## Findings

### 1. High: Non-production advisory rollout conflicts with unconditional validation and secret-safety rules

**Project-context rule**

- Terraform must validate successfully before work is complete.
- Secrets, credentials, `.env` files, and sensitive values must never be committed or exposed.
- Security is a default implementation requirement, not an optional production-only control.

**PRD/addendum state**

- FR-20 says required validation failures block merge, and NFR-2 says secrets never appear in source control or Terraform inputs.
- However, rollout step 5 / A12 says dev and staging findings are advisory during MVP and that invalid Terraform and obvious secret exposure become blocking only after pilot acceptance.

**Gap or contradiction**

The staged policy language can be read to permit invalid Terraform or secret exposure during MVP, contradicting both the project context and the PRD's own FR-20/NFR-2. Environment maturity does not make these acceptable.

**Required reconciliation**

Clarify that format/validation failures, detected secret exposure, committed credentials or state, and other unconditional repository-safety rules block in every environment from day one. Limit the advisory rollout only to explicitly identified governance controls whose temporary non-production relaxation is safe, such as selected IAM wildcard, alarm, retention, tag, or mutable-image findings. Do not allow an exception path for actual secret exposure.

### 2. High: Terraform and sensitive-artifact hygiene is incomplete

**Project-context rule**

- Never commit `.terraform/`, `terraform.tfstate`, plan output files, generated state, credentials, or `.env` files.
- Avoid Terraform provisioners and do not use `null_resource` for normal infrastructure workflows.
- Every infrastructure change must be reproducible through code.

**PRD/addendum state**

- FR-23 protects saved plans from repository storage and requires restricted, short-lived handling.
- NFR-2 covers secret exposure, and the product consistently requires Terraform-managed reproducibility.
- Neither artifact explicitly covers Terraform state, `.terraform/`, `.env`, generated credentials, provisioners, or `null_resource`.

**Gap**

The reusable workflow and documentation contract could satisfy the PRD while omitting mandatory repository hygiene or permitting non-reproducible imperative Terraform patterns.

**Required reconciliation**

Add a cross-cutting Terraform hygiene requirement or delivery acceptance item that prohibits committing generated state, `.terraform/`, plan files, credentials, and `.env` files; requires secure remote state according to the consuming environment's standard; and prohibits provisioners or `null_resource` for normal module behavior. Saved-plan handling in FR-23 should remain as the controlled CI exception, never a repository artifact.

### 3. Medium: Resource and log naming is described but not bound to the repository convention

**Project-context rule**

- Resource names follow `<environment>-<application>-<component>`.
- CloudWatch log-group names follow the project naming convention.

**PRD/addendum state**

- FR-3 requires "predictable resource names" and the standard tags.
- FR-14 requires a per-job CloudWatch log group but does not constrain its name.

**Gap**

"Predictable" is not testable against the repository's declared naming rule and allows consumers or implementers to introduce a competing convention.

**Required reconciliation**

Make compatibility with `<environment>-<application>-<component>` an explicit naming requirement for created resources, including the CloudWatch log group, while allowing only documented service-specific suffixes or AWS length/character adaptations. Any deliberate departure should be handled as an architecture decision rather than a hidden module default.

### 4. Medium: Rollback requirements omit expected recovery time and compatibility analysis

**Project-context rule**

Every production deployment should identify the rollback artifact/version, compatibility or migration concerns, whether rollback is safe for data/schema effects, and the expected recovery time.

**PRD/addendum state**

- FR-24 and the rollback principles require known-good versions, rollback or forward-fix instructions, compensating actions for data effects, and post-rollback verification.
- FR-25 requires migration notes for breaking platform releases.

**Gap**

The PRD does not require the job-specific rollback plan to state an expected recovery time or explicitly assess compatibility between the previous task definition/image/module version and current application data or dependencies.

**Required reconciliation**

Extend rollback evidence and the Runbook/Production Readiness Checklist to include a target or estimated recovery time, the exact known-good deployment identity, compatibility and migration constraints, data-side-effect safety, and the conditions under which forward-fix is safer than rollback.

### 5. Medium: Definition-of-done evidence is not fully represented in the delivery contract

**Project-context rule**

Completion requires tests or a documented reason for no tests, security and IAM review, safe secret handling, production logs/metrics/alarms, rollback, updated README/runbook, PR notes describing impact and risk, expected Terraform plan impact for production, and no unrelated refactoring.

**PRD/addendum state**

- FR-20, FR-21, FR-24, FR-26 through FR-28, NFR-10, and the addendum cover most of these controls.
- The addendum says production changes include expected impact and rollback notes.

**Gap**

The delivery or Production Readiness contract does not explicitly require a test-evidence-or-rationale decision, PR risk statement, expected production plan impact, or confirmation that unrelated changes are excluded. These omissions make the repository definition of done difficult to enforce consistently through the reusable workflow and PR template.

**Required reconciliation**

Add these items to the PR template or Production Readiness Checklist and make them auditable release evidence. For Terraform changes, retain explicit `terraform fmt -check` and `terraform validate` evidence, plus focused module/example/policy tests appropriate to the change.

## Rules Already Preserved

- **AWS and ECS:** AWS-only, ECS Fargate preference, EventBridge Scheduler, explicit CPU/memory, private subnet execution, public IP disabled, existing-network inputs, and required NAT/VPC endpoint reachability.
- **IAM and security:** separate scheduler, execution, and task roles; scoped `iam:PassRole`; explicit application permissions; justified wildcard exceptions; GitHub OIDC; immutable images; and approved secret references without plaintext values.
- **Tagging:** Environment, Application, Service, Owner, ManagedBy, and conditional CostCenter/Repository tags are present.
- **CI/CD:** format, validate, tests, security scan, plan, manual production approval, exact saved-plan apply, restricted concurrency, and attributable deployment identity are present.
- **Observability:** explicit log retention, four-plane failure detection, actionable alarms, optional operational dashboards, known failure modes, alert routing, and job-specific runbooks are present.
- **Reliability:** at-least-once semantics, retry boundaries, idempotency/overlap obligations, maximum-runtime detection, safe reruns, alarm testing, and explicit failure-mode mitigations are present.
- **Lifecycle and rollback:** semantic versioning, pinned module/workflow/image identities, deprecation and migration notes, known-good restoration, compensating actions, and post-rollback verification are present, subject to finding 4.
- **Documentation:** README, inputs/outputs, examples, architecture prerequisites, security guidance, observability guidance, troubleshooting, runbook, ownership, and rollback material are required.
- **Cost:** applicable cost tags, configurable retention, and controls against unbounded optional dashboard or retention cost are present.

## Recommended Disposition

Resolve finding 1 before the PRD is considered safe for downstream architecture or implementation. Findings 2 through 5 can be incorporated as narrow requirement/checklist edits without changing product scope or the approved MVP mechanism.
