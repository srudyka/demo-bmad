---
title: 'ECS Scheduled Jobs Platform Service'
type: 'feature'
created: '2026-07-09'
status: 'done'
review_loop_iteration: 0
baseline_commit: '3db149aee866e8faaf4a1c455d36074f090ddcab'
context:
  - '{project-root}/_bmad-output/project-context.md'
  - '{project-root}/AGENTS.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Teams need a repeatable internal platform pattern for ECS scheduled jobs across AWS accounts, but this repository does not yet provide Terraform modules, CI validation, alarms, IAM boundaries, or operational documentation for that pattern.

**Approach:** Add a focused Terraform-based platform baseline: one reusable ECS scheduled job module, one example environment showing cross-account/provider usage without hardcoded account data, GitHub Actions validation, and runbook-style documentation. The implementation should make the safe path obvious while leaving account IDs, regions, images, subnets, and job-specific policies as caller-supplied inputs.

## Boundaries & Constraints

**Always:** Use Terraform for AWS resources. Model scheduled jobs on ECS Fargate plus EventBridge Scheduler. Keep IAM least-privilege by separating execution role, task role, scheduler role, and caller-provided task permissions. Configure CloudWatch Logs and alarms for failed scheduler invocations. Require explicit CPU, memory, timeout, schedule, tags, networking, and container image inputs. Include examples and rollback notes. Keep all account-specific values variable-driven.

**Ask First:** Adding remote Terraform state, creating real AWS account IDs/role ARNs, choosing a production region, adding third-party Terraform modules, provisioning container image build/push, or adding deployment/apply automation beyond validation and plan scaffolding.

**Never:** Do not commit secrets, generated state, `.terraform/`, `.tfvars`, plan files, credentials, or hardcoded account IDs. Do not use broad IAM resources/principals unless a documented AWS API requires wildcard scope. Do not create public networking defaults. Do not use `null_resource` or provisioners for normal infrastructure flow.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Reusable scheduled job | Caller supplies cluster ARN, subnets, security groups, image, schedule, tags, and scoped task policy statements | Module creates task definition, log group, roles, scheduler, and failed-invocation alarm | Terraform validation rejects missing or invalid required values |
| Cross-account usage | Example config uses aliased AWS provider and caller-supplied assume-role ARN | Pattern shows how each account can instantiate the same module safely | No real account identifiers are committed |
| IAM scope | Caller provides task role policy statements for only job-specific AWS actions | Module attaches scoped task permissions and minimal scheduler/execution role policies | Any unavoidable wildcard is isolated and documented |
| Observability | Job is scheduled through EventBridge Scheduler | Logs go to CloudWatch; alarm covers scheduler invocation failures | Alarm action inputs are optional but documented |

</frozen-after-approval>

## Code Map

- `modules/ecs-scheduled-job/` -- new reusable Terraform module for one ECS Fargate scheduled job.
- `modules/ecs-scheduled-job/main.tf` -- AWS resources: log group, IAM roles/policies, task definition, EventBridge Scheduler schedule, CloudWatch alarm.
- `modules/ecs-scheduled-job/variables.tf` -- typed inputs, descriptions, and validation for schedule, compute, networking, IAM, tags, and observability.
- `modules/ecs-scheduled-job/outputs.tf` -- exported ARNs/names needed by callers and runbooks.
- `modules/ecs-scheduled-job/versions.tf` -- Terraform and AWS provider constraints.
- `modules/ecs-scheduled-job/README.md` -- module contract, examples, security notes, alarms, and rollback guidance.
- `envs/example/` -- non-production example showing provider alias/cross-account pattern without real IDs.
- `.github/workflows/terraform.yml` -- fmt, init without backend, validate, and static security checks where available.
- `README.md` -- repository-level platform service overview and usage entry point.

## Tasks & Acceptance

**Execution:**
- [x] `modules/ecs-scheduled-job/versions.tf` -- add Terraform/AWS provider constraints -- keeps module consumers on an explicit compatibility surface.
- [x] `modules/ecs-scheduled-job/variables.tf` -- define strict inputs with validation -- prevents unsafe implicit defaults.
- [x] `modules/ecs-scheduled-job/main.tf` -- create ECS task, scheduler, CloudWatch logs/alarms, and least-privilege IAM roles -- delivers the platform primitive.
- [x] `modules/ecs-scheduled-job/outputs.tf` -- export operational identifiers -- supports callers, dashboards, and runbooks.
- [x] `modules/ecs-scheduled-job/README.md` -- document contract, IAM model, alarms, and rollback -- makes adoption safe.
- [x] `envs/example/*.tf` -- add a runnable example with aliased provider and placeholder variables -- standardizes cross-account usage without secrets.
- [x] `.github/workflows/terraform.yml` -- add Terraform validation workflow -- gives PRs basic quality gates.
- [x] `README.md` -- add platform overview and quick start -- makes the repository navigable.
- [x] Verify Terraform formatting and module/example validation where the local toolchain allows.

**Acceptance Criteria:**
- Given a caller supplies required ECS cluster, networking, schedule, image, tags, and task policy inputs, when `terraform validate` runs for the module and example, then configuration validates without hardcoded AWS account values.
- Given a scheduled job is instantiated from the module, when Terraform applies it in an AWS account, then the job has separate execution, task, and scheduler IAM roles with scoped policies.
- Given a scheduler invocation fails, when CloudWatch evaluates the created metric alarm, then the configured failed-invocation alarm can notify supplied alarm action ARNs.
- Given a reviewer inspects the repository, when they follow README guidance, then they can identify module inputs, security boundaries, validation workflow, and rollback steps.

## Spec Change Log

## Design Notes

Prefer EventBridge Scheduler over legacy CloudWatch Events rules because Scheduler has first-class ECS target support, flexible retry behavior, and explicit schedule state. The module should remain one-job-per-instance; standardization comes from repeated module use, not from a giant central registry module.

## Verification

**Commands:**
- `terraform fmt -check -recursive` -- expected: all Terraform files are formatted.
- `terraform -chdir=modules/ecs-scheduled-job init -backend=false` -- expected: provider initialization succeeds.
- `terraform -chdir=modules/ecs-scheduled-job validate` -- expected: module validates.
- `terraform -chdir=envs/example init -backend=false` -- expected: example initializes without remote backend.
- `terraform -chdir=envs/example validate` -- expected: example validates without real account IDs.

**Local verification performed:**
- `tofu fmt -check -recursive` -- passed.
- `tofu -chdir=modules/ecs-scheduled-job init -backend=false` -- passed with network approval.
- `tofu -chdir=modules/ecs-scheduled-job validate` -- passed.
- `tofu -chdir=envs/example init -backend=false` -- passed with network approval.
- `tofu -chdir=envs/example validate` -- passed.
- Repository guard for committed `*.tfstate`, `*.tfstate.*`, `*.tfvars`, and `*.tfvars.json` files -- passed.
- Terraform policy guard for broad principals/resources, public ingress, and committed `:latest` image assignments -- passed.

## Suggested Review Order

**Module Design**

- Start here for the one-job module shape and derived safety defaults.
  [`main.tf:1`](../../modules/ecs-scheduled-job/main.tf#L1)

- Review the public API constraints before resource behavior.
  [`variables.tf:1`](../../modules/ecs-scheduled-job/variables.tf#L1)

**IAM And Execution**

- Scheduler trust is source-constrained to the generated schedule ARN.
  [`main.tf:78`](../../modules/ecs-scheduled-job/main.tf#L78)

- Secret access splits Secrets Manager, SSM, and KMS permissions.
  [`main.tf:120`](../../modules/ecs-scheduled-job/main.tf#L120)

- Task policies support scoped statements and optional IAM conditions.
  [`main.tf:173`](../../modules/ecs-scheduled-job/main.tf#L173)

- Scheduler role gets RunTask, PassRole, and optional DLQ permissions.
  [`main.tf:243`](../../modules/ecs-scheduled-job/main.tf#L243)

**Runtime And Observability**

- Task definition carries logs, tags, and Fargate sizing checks.
  [`main.tf:211`](../../modules/ecs-scheduled-job/main.tf#L211)

- Scheduler waits on role attachments and propagates task-definition tags.
  [`main.tf:296`](../../modules/ecs-scheduled-job/main.tf#L296)

- ECS task failure events catch non-zero container exits.
  [`main.tf:348`](../../modules/ecs-scheduled-job/main.tf#L348)

- Scheduler delivery alarms cover target errors and dropped invocations.
  [`main.tf:379`](../../modules/ecs-scheduled-job/main.tf#L379)

**Input Guards**

- Image, secret, JSON, retry, and task-policy validations prevent apply-time surprises.
  [`variables.tf:85`](../../modules/ecs-scheduled-job/variables.tf#L85)

- Task policy schema keeps least-privilege conditions expressible.
  [`variables.tf:246`](../../modules/ecs-scheduled-job/variables.tf#L246)

**Adoption Surface**

- Example shows aliased-provider cross-account usage without real IDs.
  [`main.tf:12`](../../envs/example/main.tf#L12)

- CI covers Terraform paths, policy guards, init, and validate.
  [`terraform.yml:3`](../../.github/workflows/terraform.yml#L3)

- Repository README gives the platform entry point and rollback pattern.
  [`README.md:1`](../../README.md#L1)
