---
title: 'ECS Scheduled Jobs Platform Service'
type: 'feature'
created: '2026-07-10'
status: 'done'
review_loop_iteration: 0
baseline_commit: '3db149aee866e8faaf4a1c455d36074f090ddcab'
context:
  - '{project-root}/_bmad-output/project-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The repository does not yet provide a reusable, production-ready pattern for internal teams to run ECS Fargate scheduled jobs consistently across AWS accounts. Without a standard module, teams are likely to duplicate IAM, logging, retry, alarm, and CI/CD decisions inconsistently.

**Approach:** Add a focused Terraform module that defines one ECS scheduled job pattern with explicit Fargate task configuration, EventBridge Scheduler, CloudWatch Logs, alarms, retry/DLQ behavior, and least-privilege IAM. Add a non-production example environment, GitHub Actions validation workflow, and README/runbook documentation so the pattern is repeatable across accounts without embedding account-specific values.

## Boundaries & Constraints

**Always:** Follow the existing DevOps/SRE project context; use Terraform module structure under `modules/`; keep account IDs, ARNs, regions, cluster names, subnet IDs, and security groups configurable; separate ECS task role, ECS execution role, and scheduler role; configure log retention; include required tags; scope IAM to the target task definition, cluster, and roles wherever AWS supports it; include alarms for failed scheduling/target delivery and DLQ backlog; include rollback notes and operator runbook guidance.

**Ask First:** Any production account deployment, destructive resource replacement, broad IAM wildcard beyond documented AWS service limitations, public networking, secret material in examples, or auto-apply to production.

**Never:** Do not commit Terraform state, plans, generated provider directories, secrets, concrete account IDs, or real ARNs. Do not create a bespoke script-based scheduler when AWS EventBridge Scheduler and ECS Fargate can satisfy the requirement. Do not use `Resource = "*"` for IAM unless the spec or README documents the specific AWS limitation and the action is tightly constrained by condition.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Standard scheduled job | Caller supplies naming, image, command, schedule, ECS cluster, subnets, and security groups | Terraform creates task definition, schedule, logs, IAM roles, DLQ, alarms, and required tags | Terraform validation fails early on malformed required values |
| Cross-account reuse | Another AWS account uses different provider credentials and account-local ECS/network inputs | No committed account, region, or ARN values block reuse | README documents where account-specific values belong |
| Failed ECS launch | Scheduler cannot invoke ECS or target delivery fails | Retries apply, failed delivery lands in DLQ, and alarms can notify SNS topics | Alarms are optional without SNS topics, but DLQ and metrics remain |
| Job log inspection | Operators debug a run | Task logs go to an explicitly retained CloudWatch Log Group | Runbook points to logs, DLQ, Scheduler, and ECS task events |
| Least privilege review | Security reviews generated IAM | Execution, task, and scheduler permissions are separate and scoped | Wildcards are narrow, justified, and condition-scoped where possible |

</frozen-after-approval>

## Code Map

- `README.md` -- currently minimal; should become the entry point for usage, validation, rollback, and runbook notes.
- `.github/workflows/terraform.yml` -- new CI workflow for Terraform format, validation, and security scanning.
- `modules/ecs-scheduled-job/` -- new reusable module implementing the standard ECS scheduled job pattern.
- `modules/ecs-scheduled-job/examples/basic/` -- module-level example for validation and caller guidance.
- `envs/example/` -- non-production root module showing how an AWS account wires the platform service module.

## Tasks & Acceptance

**Execution:**
- [x] `modules/ecs-scheduled-job/versions.tf` -- add Terraform/provider constraints -- keep the module portable and validateable.
- [x] `modules/ecs-scheduled-job/variables.tf` -- define typed inputs with descriptions and validations for naming, schedule, Fargate sizing, networking, tags, retries, log retention, alarms, and optional task permissions -- prevent unsafe or ambiguous usage.
- [x] `modules/ecs-scheduled-job/main.tf` -- create locals, CloudWatch log group, ECS task definition, execution/task/scheduler IAM roles, EventBridge Scheduler schedule, DLQ, and CloudWatch alarms -- implement the reusable platform service.
- [x] `modules/ecs-scheduled-job/outputs.tf` -- expose task definition, schedule, log group, IAM role, DLQ, and alarm identifiers -- support downstream operations and integration.
- [x] `modules/ecs-scheduled-job/README.md` -- document inputs, IAM model, alarm strategy, runbook, idempotency expectation, and rollback notes -- make the module operable.
- [x] `modules/ecs-scheduled-job/examples/basic/` -- add a minimal module invocation using placeholder variables, not real account values -- provide a validateable usage example.
- [x] `envs/example/` -- add a non-production root module that wires configurable account-local ECS/network inputs into the module -- demonstrate cross-account consumption without hardcoded infrastructure.
- [x] `.github/workflows/terraform.yml` -- add GitHub Actions checks for Terraform fmt, init/validate for the module/example/env, and security scanning with non-failing install assumptions documented in YAML comments where needed -- standardize CI quality gates.
- [x] `README.md` -- update project-level documentation with purpose, affected AWS components, setup, validation commands, rollback guidance, and security notes -- satisfy repository documentation expectations.

**Acceptance Criteria:**
- Given a valid example configuration, when Terraform validation runs for the module example and `envs/example`, then both root modules validate without account-specific committed values.
- Given an ECS scheduled job configured through the module, when Terraform applies it, then core resources and tags use predictable `<environment>-<application>-<service>` naming.
- Given a failed schedule target delivery, when EventBridge Scheduler exhausts configured retries, then the failure can be observed through the DLQ and configured CloudWatch alarms.
- Given a security review, when IAM policies are inspected, then task execution, application task permissions, and scheduler invocation permissions are separated and scoped to configured resources.
- Given an operator responding to a failed job, when they read the README/module runbook, then they can find logs, inspect the schedule, inspect DLQ messages, and roll back by reverting to a previous module or environment version.

## Spec Change Log

## Design Notes

The module should own the standard job envelope, not the application workload itself. Application permissions enter through explicit policy statements or managed policy ARNs on the task role; secrets should be referenced by ARN/name as ECS container secrets, never committed as plaintext values.

Prefer EventBridge Scheduler over legacy EventBridge rules because it provides first-class ECS targets, retry policy, flexible time windows, and DLQ configuration. The example environment is intentionally non-production and should not create VPCs or ECS clusters; those remain account-owned platform primitives supplied by callers.

## Verification

**Commands:**
- `terraform fmt -check` -- expected: all Terraform files are formatted.
- `terraform -chdir=modules/ecs-scheduled-job init -backend=false` -- expected: providers/modules initialize without remote state.
- `terraform -chdir=modules/ecs-scheduled-job validate` -- expected: module validates.
- `terraform -chdir=modules/ecs-scheduled-job/examples/basic init -backend=false` -- expected: example initializes.
- `terraform -chdir=modules/ecs-scheduled-job/examples/basic validate` -- expected: example validates.
- `terraform -chdir=envs/example init -backend=false` -- expected: example environment initializes.
- `terraform -chdir=envs/example validate` -- expected: example environment validates.

**Implementation validation note:** Local `terraform` is unavailable in this environment, so OpenTofu was used for validation. `tofu fmt -check -recursive`, `tofu -chdir=modules/ecs-scheduled-job validate`, and `tofu -chdir=envs/example validate` pass. The nested module example initializes, but local OpenTofu fails before configuration diagnostics with an AWS provider plugin handshake error for that nested root. Review findings were patched for Fargate CPU/memory combinations, immutable image validation, ECR opt-in permissions, ARN-scoped secrets, network ID validation, DLQ bounds, required owner tags, production alarm actions, wildcard task policies, Scheduler metric dimensions, and non-zero task exit alarms.

## Suggested Review Order

**Module Design**

- Start here for naming, required tags, and Fargate sizing invariants.
  [`main.tf:3`](../../modules/ecs-scheduled-job/main.tf#L3)

- Review task definition boundaries, immutable image/ECR guards, and CPU-memory preconditions.
  [`main.tf:214`](../../modules/ecs-scheduled-job/main.tf#L214)

- Check Scheduler wiring, retry/DLQ behavior, and task grouping.
  [`main.tf:380`](../../modules/ecs-scheduled-job/main.tf#L380)

**IAM And Security**

- Review execution-role permissions for logs, opt-in ECR, secrets, and KMS.
  [`main.tf:101`](../../modules/ecs-scheduled-job/main.tf#L101)

- Review scheduler role scoping for RunTask, PassRole, DLQ, and tag-on-create.
  [`main.tf:265`](../../modules/ecs-scheduled-job/main.tf#L265)

- Check caller-facing validation for images, network IDs, secrets, and task policies.
  [`variables.tf:59`](../../modules/ecs-scheduled-job/variables.tf#L59)

**Observability**

- Review ECS task-state capture into logs and metric filter generation.
  [`main.tf:322`](../../modules/ecs-scheduled-job/main.tf#L322)

- Review Scheduler, task-failure, and DLQ CloudWatch alarms.
  [`main.tf:424`](../../modules/ecs-scheduled-job/main.tf#L424)

- Confirm runbook paths cover Scheduler, task exits, DLQ, and rollback.
  [`README.md:84`](../../README.md#L84)

**Consumption And Automation**

- Review account-local environment wiring and private-network defaults.
  [`main.tf:1`](../../envs/example/main.tf#L1)

- Review module-level example and ECR permission opt-in pattern.
  [`main.tf:1`](../../modules/ecs-scheduled-job/examples/basic/main.tf#L1)

- Review CI format, validate, and Trivy scan coverage.
  [`terraform.yml:24`](../../.github/workflows/terraform.yml#L24)
