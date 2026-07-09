# demo-bmad

Internal platform baseline for standardizing ECS scheduled jobs across AWS
accounts.

## What This Provides

- A reusable Terraform module for one ECS Fargate scheduled job.
- EventBridge Scheduler configuration with retry behavior.
- Separate IAM roles for task execution, task runtime permissions, and Scheduler
  invocation.
- CloudWatch Logs and Scheduler failure alarms.
- EventBridge task-failure routing for ECS tasks that stop with non-zero
  container exit codes.
- A cross-account example environment using an aliased AWS provider.
- GitHub Actions checks for Terraform formatting, validation, and basic static
  repository guards.

## Repository Layout

```text
modules/
  ecs-scheduled-job/   Reusable scheduled job module
envs/
  example/             Non-production account/provider wiring example
.github/workflows/
  terraform.yml        Terraform validation workflow
```

## Quick Start

Inspect the example first:

```bash
terraform -chdir=envs/example init -backend=false
terraform -chdir=envs/example validate
```

Use `modules/ecs-scheduled-job` once per scheduled job. Keep real account IDs,
role ARNs, subnet IDs, security group IDs, and image URIs in your secure
environment inputs, not in committed tfvars files.

## Security Boundaries

- No public networking defaults.
- No hardcoded account IDs or credentials.
- Task execution, task runtime, and Scheduler permissions are separate.
- Job-specific AWS permissions belong in `task_policy_statements`.
- Task policy statements support optional IAM conditions for scoped access.
- Secrets must come from Secrets Manager or SSM Parameter Store ARNs, not plain
  Terraform environment variable values.
- Container images must not use the mutable `latest` tag.

## Rollback Pattern

For production-impacting changes, prefer disabling the schedule before
destroying resources:

```hcl
schedule_state = "DISABLED"
```

Apply that change, inspect logs and alarms, then revert or repair the bad job
configuration. This preserves evidence needed for investigation.

## Validation

```bash
terraform fmt -check -recursive
terraform -chdir=modules/ecs-scheduled-job init -backend=false
terraform -chdir=modules/ecs-scheduled-job validate
terraform -chdir=envs/example init -backend=false
terraform -chdir=envs/example validate
```
