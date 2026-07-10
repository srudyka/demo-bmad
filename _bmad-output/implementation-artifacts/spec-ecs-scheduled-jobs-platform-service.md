---
title: 'ECS Scheduled Jobs Platform Service'
type: 'feature'
created: '2026-07-10'
status: 'done'
review_loop_iteration: 0
baseline_commit: '99637f1d2fe715368412d92228b00b06394cd297'
context:
  - '{project-root}/_bmad-output/project-context.md'
  - '{project-root}/_bmad/custom/standards/aws-terraform-implementation.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The repository does not yet provide a reusable, secure, observable way for teams to deploy ECS Fargate scheduled jobs consistently across AWS accounts. Without a standard module and CI checks, teams are likely to duplicate EventBridge Scheduler, IAM, logging, and alarm patterns with uneven reliability and least-privilege controls.

**Approach:** Add a reusable Terraform module for ECS scheduled jobs, a basic example root, GitHub Actions validation/security scanning, and documentation/runbook notes. The module should manage only the common scheduled-job platform pieces while requiring account-specific inputs from callers.

## Boundaries & Constraints

**Always:** Follow the AWS Terraform implementation standard. Use Terraform only for infrastructure. Place the reusable module under `modules/ecs-scheduled-job` with `main.tf`, `variables.tf`, `outputs.tf`, `versions.tf`, `README.md`, and `examples/basic`. Use AWS provider resources for ECS task definitions, CloudWatch logs/alarms, EventBridge Scheduler, SQS DLQ, and IAM roles/policies. Keep execution role, task role, and scheduler role separate. Scope IAM to configured task definition, cluster, log group, and DLQ resources wherever AWS allows. Require predictable naming, required tags, immutable image references, explicit log retention, bounded scheduler retry behavior, and operationally useful outputs.

**Ask First:** Creating environment roots beyond the module example, adding real account IDs/regions/subnets/security groups, creating production apply workflows, or introducing non-AWS/Terraform tooling not already implied by the repo standards.

**Never:** Commit Terraform state, `.terraform/`, plan files, `.tfvars`, secrets, real account-specific IDs, or long-lived AWS credentials. Do not use public networking defaults, plaintext secret values, mutable `latest` image tags, `null_resource`, provisioners, or broad IAM wildcards unless AWS requires them and the reason is documented.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Standard scheduled job | Caller provides environment, application, service, ECS cluster ARN/name, private subnet IDs, security group IDs, container image, CPU/memory, schedule expression, and required tags | Terraform creates a private Fargate scheduled task definition, Scheduler schedule, CloudWatch log group, DLQ, alarms, and separated IAM roles | Validation catches malformed names, missing tags, invalid schedule/image, and invalid CPU/memory before apply |
| Immutable image enforcement | `container_image` uses `:latest` or no immutable tag/digest | Terraform validation fails | Error explains that immutable tags, digests, SHAs, or release versions are required |
| Optional secret references | Caller passes Secrets Manager or SSM parameter ARNs for container secrets | Task definition references secrets without exposing plaintext in Terraform docs/examples | Validation rejects non-ARN secret values |
| Failed schedule delivery | EventBridge Scheduler cannot invoke ECS task after bounded retries | Failed invocation is sent to SQS DLQ and CloudWatch alarm can notify via optional SNS topic | Outputs expose DLQ URL/ARN and alarm names for runbook use |

</frozen-after-approval>

## Code Map

- `.gitignore` -- Terraform-generated file guardrails; may need active plan-file ignores.
- `.github/workflows/terraform.yml` -- New CI workflow for Terraform fmt, validate, and IaC security scanning.
- `README.md` -- Repository-level usage, validation, rollback, and module entry-point documentation.
- `modules/ecs-scheduled-job/versions.tf` -- Terraform and AWS provider constraints for the reusable module.
- `modules/ecs-scheduled-job/main.tf` -- AWS resources for Scheduler, ECS task definition, IAM, CloudWatch logs/alarms, and DLQ.
- `modules/ecs-scheduled-job/variables.tf` -- Inputs and validation for names, tags, compute, image immutability, schedule, networking, environment, secrets, and alarm behavior.
- `modules/ecs-scheduled-job/outputs.tf` -- Operational outputs for resource identifiers, roles, log group, alarms, and DLQ.
- `modules/ecs-scheduled-job/README.md` -- Module docs, security notes, observability notes, runbook, validation, and rollback.
- `modules/ecs-scheduled-job/examples/basic/*` -- Minimal non-secret example root proving module usage and validation.

## Tasks & Acceptance

**Execution:**
- [x] `.gitignore` -- Ignore Terraform plan output files -- Prevent generated review artifacts from being committed.
- [x] `.github/workflows/terraform.yml` -- Add CI for Terraform fmt checks, validation of module/example roots, and Checkov IaC scan -- Enforce repository quality gates.
- [x] `modules/ecs-scheduled-job/versions.tf` -- Declare Terraform and AWS provider requirements -- Establish reusable module compatibility.
- [x] `modules/ecs-scheduled-job/variables.tf` -- Define validated module interface -- Reject unsafe or incomplete caller inputs early.
- [x] `modules/ecs-scheduled-job/main.tf` -- Implement ECS Fargate scheduled job resources with separated IAM, Scheduler retry/DLQ, CloudWatch logs, and alarms -- Deliver the platform service behavior.
- [x] `modules/ecs-scheduled-job/outputs.tf` -- Export operational identifiers -- Support account integration and runbooks.
- [x] `modules/ecs-scheduled-job/examples/basic` -- Add a basic example with placeholder-safe inputs and provider config -- Give teams a concrete starting point.
- [x] `modules/ecs-scheduled-job/README.md` and `README.md` -- Document usage, assumptions, security, observability, validation, rollback, and failure handling -- Meet repo documentation standards.

**Acceptance Criteria:**
- Given a caller supplies valid private networking, ECS cluster, schedule, immutable image, tags, and compute settings, when Terraform is planned, then the module defines an ECS task definition, EventBridge Scheduler schedule, SQS DLQ, CloudWatch log group, alarms, and least-privilege IAM roles without requiring account-specific values in the module.
- Given `container_image` is `latest`, lacks a tag/digest, or uses `:latest`, when Terraform validates, then validation fails with an immutable-image error.
- Given required tags are missing, when Terraform validates, then validation fails before any apply.
- Given optional secret values are provided, when Terraform validates, then only Secrets Manager or SSM parameter ARNs are accepted.
- Given CI runs on a pull request, when Terraform files change, then format, validation, and security scan jobs execute without requiring long-lived AWS credentials.

## Spec Change Log

## Design Notes

Use EventBridge Scheduler instead of a legacy EventBridge rule because Scheduler directly supports ECS targets, flexible retry policy, and dead-letter configuration. Keep the module account-agnostic: callers provide cluster/network/notification inputs, and the module creates only reusable job-level infrastructure. Some ECS `RunTask` IAM scoping still needs AWS-mandated resource coverage; constrain it with cluster/task-definition ARNs and `iam:PassedToService`/role ARNs where possible.

## Verification

**Commands:**
- `terraform fmt -check` -- expected: all Terraform files are formatted.
- `terraform -chdir=modules/ecs-scheduled-job init -backend=false` -- expected: providers initialize without backend configuration.
- `terraform -chdir=modules/ecs-scheduled-job validate` -- expected: module validates.
- `terraform -chdir=modules/ecs-scheduled-job/examples/basic init -backend=false` -- expected: example initializes.
- `terraform -chdir=modules/ecs-scheduled-job/examples/basic validate` -- expected: example validates.
- `uvx --from checkov checkov -d . --framework terraform` -- expected: no high-severity findings, or documented false positives with rationale.

## Suggested Review Order

**Design Spine**

- Naming, tags, ARNs, and isolation decisions start here.
  [`main.tf:7`](../../modules/ecs-scheduled-job/main.tf#L7)

- Validated inputs enforce the reusable module contract.
  [`variables.tf:1`](../../modules/ecs-scheduled-job/variables.tf#L1)

**ECS Scheduler Path**

- Task definition keeps execution and runtime roles separate.
  [`main.tf:224`](../../modules/ecs-scheduled-job/main.tf#L224)

- Scheduler group isolates metrics and alarms per job by default.
  [`main.tf:362`](../../modules/ecs-scheduled-job/main.tf#L362)

- Scheduler target runs private Fargate tasks with bounded retry and DLQ.
  [`main.tf:368`](../../modules/ecs-scheduled-job/main.tf#L368)

- Scheduler IAM scopes RunTask, PassRole, DLQ, and optional KMS use.
  [`main.tf:299`](../../modules/ecs-scheduled-job/main.tf#L299)

**Security Guards**

- Execution role grants logs, configured secrets, optional KMS, and ECR only.
  [`main.tf:124`](../../modules/ecs-scheduled-job/main.tf#L124)

- Immutable images and private ECR inputs are validated before use.
  [`variables.tf:83`](../../modules/ecs-scheduled-job/variables.tf#L83)

- Network, account, region, and alarm consistency are provider preconditions.
  [`main.tf:415`](../../modules/ecs-scheduled-job/main.tf#L415)

**Failure Visibility**

- ECS task stopped events capture non-zero container exits.
  [`main.tf:433`](../../modules/ecs-scheduled-job/main.tf#L433)

- Log metric filter turns task failure events into alarmable metrics.
  [`main.tf:492`](../../modules/ecs-scheduled-job/main.tf#L492)

- CloudWatch alarms cover task failures, Scheduler failures, and DLQ age.
  [`main.tf:507`](../../modules/ecs-scheduled-job/main.tf#L507)

**Operator Surface**

- Outputs expose roles, schedules, logs, DLQ, and alarm identifiers.
  [`outputs.tf:91`](../../modules/ecs-scheduled-job/outputs.tf#L91)

- Module README contains usage, runbook, security, observability, and rollback.
  [`README.md:81`](../../modules/ecs-scheduled-job/README.md#L81)

- Root README points teams at validation and operational entry points.
  [`README.md:7`](../../README.md#L7)

**CI And Hygiene**

- GitHub Actions enforce Terraform fmt, validation, and Checkov scanning.
  [`terraform.yml:1`](../../.github/workflows/terraform.yml#L1)

- Git ignores Terraform plan artifacts and generated state.
  [`.gitignore:31`](../../.gitignore#L31)
