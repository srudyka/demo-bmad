---
title: 'Standardize ECS Scheduled Jobs Platform Service'
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

**Problem:** Teams need a repeatable, secure way to run ECS Fargate scheduled jobs across AWS accounts without re-solving task definitions, schedules, IAM, observability, retries, and rollback each time.

**Approach:** Add a reusable Terraform module for one ECS scheduled job, a basic example, GitHub Actions validation, and operator documentation that encode the repository's AWS Terraform standard.

## Boundaries & Constraints

**Always:** Use Terraform only; follow `modules/<module-name>/` structure; use EventBridge Scheduler targeting ECS Fargate; create or accept narrowly scoped execution, task, and scheduler roles; configure CloudWatch Logs retention, Scheduler retry behavior, DLQ failure capture, and actionable CloudWatch alarms; enforce immutable container image references; expose useful outputs; document security, observability, validation, and rollback.

**Ask First:** Creating concrete `envs/<environment>` roots, hardcoding account IDs or regions, adding production apply workflows, introducing remote state, choosing organization-specific naming beyond `<environment>-<application>-<component>`, or allowing broad IAM/resources not required by AWS.

**Never:** Commit secrets, `.tfvars`, state, plan files, generated `.terraform/` directories, mutable `latest` image examples, public networking defaults, plaintext secret values in Terraform variables, provisioners, or `null_resource`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Standard private job | Existing ECS cluster, private subnets, security groups, immutable image, schedule expression, container command | Module creates task definition, log group, Scheduler schedule, DLQ, roles/policies, alarms, and outputs identifiers | Terraform validation fails if required IDs, image, CPU/memory, or retention are invalid |
| Existing role integration | Caller supplies execution/task role ARNs instead of creating roles | Module uses supplied roles and skips creating matching IAM resources | Validation rejects partial or malformed role ARN inputs |
| Secret references | Caller passes Secrets Manager or SSM parameter ARNs for container secrets | Task definition uses ECS `secrets` entries, not plaintext environment variables | Documentation warns that secret values must not be committed and variable descriptions distinguish names from values |
| Scheduler delivery failure | EventBridge Scheduler cannot start the ECS task after retries | Event is sent to SQS DLQ and an alarm can notify operators | DLQ ARN, queue name, and alarm names are output for triage |
| Task runtime failure | Task starts but exits non-zero | CloudWatch alarm detects ECS stopped-task failures via metric filter/event metric strategy | Runbook points operators to logs, stopped reason, DLQ, and rollback steps |

</frozen-after-approval>

## Code Map

- `README.md` -- top-level project entry; expand with module overview, validation commands, and production rollout notes.
- `.gitignore` -- Terraform safety guardrails; add active plan-output ignores if missing.
- `.github/workflows/terraform.yml` -- new CI workflow for Terraform format, validation, and Checkov IaC security scanning.
- `modules/ecs-scheduled-job/versions.tf` -- provider and Terraform version constraints for reusable module.
- `modules/ecs-scheduled-job/main.tf` -- ECS task definition, Scheduler schedule, DLQ, IAM roles/policies, logs, alarms, and tagging.
- `modules/ecs-scheduled-job/variables.tf` -- explicit module interface with validations for names, image refs, ARNs, CPU/memory, schedule, retries, logs, tags, network, env vars, and secrets.
- `modules/ecs-scheduled-job/outputs.tf` -- operational identifiers for schedules, task definitions, roles, logs, alarms, and DLQ.
- `modules/ecs-scheduled-job/README.md` -- module usage, assumptions, inputs/outputs, security, observability, rollback, and troubleshooting.
- `modules/ecs-scheduled-job/examples/basic/` -- minimal non-production example that validates without account-specific constants.
- `docs/runbooks/ecs-scheduled-job.md` -- operator runbook for verification, alarms, common failures, rollback, and idempotency expectations.

## Tasks & Acceptance

**Execution:**
- [x] `.gitignore` -- actively ignore Terraform plan output files -- prevents committed generated plan artifacts.
- [x] `.github/workflows/terraform.yml` -- add pull request workflow for `terraform fmt -check`, module/example `terraform validate`, and Checkov IaC security scanning -- establishes CI quality gates without auto-applying production.
- [x] `modules/ecs-scheduled-job/versions.tf` -- declare Terraform and AWS provider constraints -- makes module requirements explicit.
- [x] `modules/ecs-scheduled-job/variables.tf` -- define validated inputs for identity, tags, network, container, schedule, logging, retry, DLQ, alarms, optional existing roles, environment variables, and secret references -- makes the module portable across accounts while rejecting unsafe values.
- [x] `modules/ecs-scheduled-job/main.tf` -- implement the scheduled ECS job resources -- standardizes the runtime, scheduler, least-privilege roles, log group, DLQ, and alarms.
- [x] `modules/ecs-scheduled-job/outputs.tf` -- export operationally useful identifiers -- supports platform consumers and runbooks.
- [x] `modules/ecs-scheduled-job/examples/basic/*` -- add a minimal example wired to caller-supplied cluster/network values -- proves the module interface without inventing account-specific values.
- [x] `modules/ecs-scheduled-job/README.md` and `docs/runbooks/ecs-scheduled-job.md` -- document usage, assumptions, validation, observability, security, failure modes, and rollback -- satisfies production-readiness expectations.
- [x] `README.md` -- link the module, runbook, and validation workflow -- makes the platform service discoverable.

**Acceptance Criteria:**
- Given a caller provides valid ECS cluster, private subnet IDs, security group IDs, immutable image reference, schedule expression, and required tags, when Terraform plans the basic module usage, then it can create an ECS Fargate scheduled job with logs, retry policy, DLQ, alarms, and scoped roles.
- Given a container image is `latest` or lacks an immutable tag/digest-like reference, when Terraform validation runs, then validation fails before planning infrastructure.
- Given secret configuration is needed, when the caller uses the module, then secrets are supplied as ECS secret references from SSM or Secrets Manager ARNs and no plaintext secret examples are committed.
- Given the Scheduler fails to invoke the ECS task after bounded retries, when delivery failure occurs, then the event is captured in SQS DLQ and an actionable CloudWatch alarm is available.
- Given a task exits unsuccessfully, when the alarm evaluation window detects the failure signal, then operators can identify the log group, task definition, schedule, DLQ, and rollback path from outputs and runbook docs.
- Given a pull request changes Terraform, when GitHub Actions runs, then format, validation, and IaC security scan jobs execute without requiring production credentials or apply permissions.

## Spec Change Log

## Design Notes

The module should be account-agnostic. Do not add `envs/prod`, `envs/staging`, remote state, or concrete account wiring until the account model is known. Prefer inputs that let account repositories pass cluster, subnet, security group, and notification details.

Use EventBridge Scheduler because it provides direct scheduling semantics, retry policy, flexible time window controls, and DLQ support for failed target delivery. Use CloudWatch metric filters or EventBridge-derived metrics for stopped task failures, because a Scheduler invocation can succeed even when the ECS task later exits non-zero.

IAM should default to creating separate execution, task, and scheduler roles, with optional caller-supplied role ARNs for organizations that centralize IAM. Scheduler permissions should target the configured cluster/task definition and allow `iam:PassRole` only for the execution/task roles.

## Verification

**Commands:**
- `terraform fmt -check` -- expected: all Terraform files are formatted.
- `terraform -chdir=modules/ecs-scheduled-job init -backend=false` -- expected: provider initialization succeeds without remote state.
- `terraform -chdir=modules/ecs-scheduled-job validate` -- expected: reusable module validates.
- `terraform -chdir=modules/ecs-scheduled-job/examples/basic init -backend=false` -- expected: example initializes without backend configuration.
- `terraform -chdir=modules/ecs-scheduled-job/examples/basic validate` -- expected: example validates.
- GitHub Actions workflow lint by inspection or local syntax check if tooling is available -- expected: workflow has no production apply and uses Checkov/security-scan patterns.

## Suggested Review Order

**Module Design**

- Start with the derived names, role modes, and scheduler ARN contract.
  [`main.tf:7`](../../modules/ecs-scheduled-job/main.tf#L7)

- Review the core ECS task definition and hard validation preconditions.
  [`main.tf:330`](../../modules/ecs-scheduled-job/main.tf#L330)

- Check Scheduler target wiring, retry policy, DLQ, and private networking.
  [`main.tf:381`](../../modules/ecs-scheduled-job/main.tf#L381)

**Security And IAM**

- Confirm execution-role scope for logs, ECR, secrets, and KMS.
  [`main.tf:171`](../../modules/ecs-scheduled-job/main.tf#L171)

- Confirm scheduler role scope and constrained `iam:PassRole`.
  [`main.tf:283`](../../modules/ecs-scheduled-job/main.tf#L283)

- Review secret-reference and environment-variable validation.
  [`variables.tf:142`](../../modules/ecs-scheduled-job/variables.tf#L142)

**Reliability And Observability**

- Review CloudWatch Logs retention and DLQ encryption defaults.
  [`main.tf:77`](../../modules/ecs-scheduled-job/main.tf#L77)

- Check failed-task event matching for non-zero exits and failed starts.
  [`main.tf:422`](../../modules/ecs-scheduled-job/main.tf#L422)

- Confirm alarms for task failures and Scheduler DLQ messages.
  [`main.tf:457`](../../modules/ecs-scheduled-job/main.tf#L457)

**Interface And Examples**

- Review immutable image, platform, schedule, and retry inputs.
  [`variables.tf:116`](../../modules/ecs-scheduled-job/variables.tf#L116)

- Check the minimal example stays account-agnostic and caller-supplied.
  [`main.tf:1`](../../modules/ecs-scheduled-job/examples/basic/main.tf#L1)

**CI And Docs**

- Confirm PR validation runs Terraform checks and Checkov scanning.
  [`terraform.yml:1`](../../.github/workflows/terraform.yml#L1)

- Review module usage, security notes, timeout limits, and rollback.
  [`README.md:41`](../../modules/ecs-scheduled-job/README.md#L41)

- Review operator triage, rollback, and idempotency guidance.
  [`ecs-scheduled-job.md:1`](../../docs/runbooks/ecs-scheduled-job.md#L1)
