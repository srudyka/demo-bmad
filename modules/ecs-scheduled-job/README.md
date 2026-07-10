# ECS Scheduled Job Module

This module creates one ECS Fargate scheduled job using EventBridge Scheduler. It is account-agnostic: callers provide an existing ECS cluster, private subnets, security groups, and optional notification targets.

## What It Creates

- ECS task definition with explicit CPU, memory, Fargate networking, CloudWatch Logs, and immutable image validation.
- EventBridge Scheduler schedule with bounded retries, optional disable switch, and SQS DLQ for target delivery failures.
- Separate execution, task, and scheduler roles by default, or caller-supplied existing role ARNs.
- CloudWatch alarms for Scheduler DLQ messages and ECS stopped tasks with non-zero container exit codes.
- Operational outputs for runbooks and platform consumers.

## Usage

```hcl
module "daily_report" {
  source = "./modules/ecs-scheduled-job"

  environment = "dev"
  application = "platform"
  service     = "scheduled-jobs"
  job_name    = "daily-report"
  owner       = "platform"

  cluster_arn        = var.cluster_arn
  subnet_ids         = var.private_subnet_ids
  security_group_ids = var.task_security_group_ids

  container_image   = var.container_image
  container_command = ["python", "-m", "jobs.daily_report"]

  ecr_repository_arns = var.ecr_repository_arns

  scheduler_kms_key_arn = var.scheduler_kms_key_arn
  schedule_expression   = "cron(0 6 * * ? *)"
  alarm_actions         = [aws_sns_topic.platform_alerts.arn]
}
```

For a minimal validating root, see `examples/basic`.

## Inputs And Security

Use `container_secrets` for sensitive values. Each entry must reference an SSM Parameter Store or Secrets Manager ARN; do not pass secret values through `environment_variables`, examples, `.tfvars`, or committed files. Obvious secret-like environment variable names are rejected.

If `execution_role_arn` and `task_role_arn` are omitted, the module creates both roles. If your organization manages ECS roles centrally, set both ARNs together and ensure the supplied execution role can write logs, pull the configured image, and read configured secret references. The scheduler role may also be supplied with `scheduler_role_arn`; when supplied, it must allow `ecs:RunTask`, `iam:PassRole` for the task roles, and `sqs:SendMessage` to the module DLQ.

Private ECR pulls require `ecr_repository_arns` when the module creates the execution role. The module scopes repository read actions to those ARNs; `ecr:GetAuthorizationToken` uses `Resource = "*"` because AWS does not support resource-level permissions for that action. `container_image` must use a digest, semantic release tag, or commit SHA tag; floating channel tags are rejected.

`scheduler_kms_key_arn` is required so EventBridge Scheduler encrypts schedule data with a customer managed KMS key. Keep the key ARN in the calling account or environment configuration rather than committing account-specific values to this module.

`platform_version` defaults to the pinned Fargate platform version `1.4.0`. Set `create_schedule_group = true` when the module should create a non-default Scheduler group; otherwise `schedule_group_name` must already exist.

## Observability

Container logs go to `/aws/ecs/<environment>-<application>-<job_name>` with explicit retention. Scheduler delivery failures go to the module DLQ and trigger the DLQ alarm when messages are visible. Runtime task failures are detected from ECS task state change events when a container exits non-zero or the task fails to start.

ECS does not provide a generic wall-clock timeout for one-off Fargate tasks through Scheduler. Jobs should implement their own bounded runtime or timeout behavior in application code, and operators should document expected maximum runtime for each consumer.

Production callers should wire `alarm_actions` to an operational SNS topic or incident-routing integration and set log retention to the environment standard.

## Validation

```bash
terraform fmt -check
terraform -chdir=modules/ecs-scheduled-job init -backend=false
terraform -chdir=modules/ecs-scheduled-job validate
terraform -chdir=modules/ecs-scheduled-job/examples/basic init -backend=false
terraform -chdir=modules/ecs-scheduled-job/examples/basic validate
```

## Rollback

Set `schedule_enabled = false` to stop future invocations without deleting logs or DLQ evidence. To roll back a bad task revision, restore the prior image reference or module version and apply. If Scheduler delivery failures occurred during rollback, inspect and drain the DLQ after confirming no replay is needed.
