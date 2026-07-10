# ECS Scheduled Job Module

This module standardizes one internal ECS Fargate scheduled job. It creates the task definition, CloudWatch Log Group, EventBridge Scheduler schedule, SQS dead-letter queue, CloudWatch alarms, and separate IAM roles for execution, task runtime, and scheduler invocation.

## Resources

- ECS task definition using Fargate and `awsvpc`
- CloudWatch Log Group with explicit retention
- ECS execution role for logs, ECR pull, and configured secret reads
- ECS task role with no application permissions unless provided
- EventBridge Scheduler role scoped to the configured task definition, ECS cluster, task roles, and DLQ
- EventBridge Scheduler schedule with retry policy and DLQ
- SQS DLQ with managed server-side encryption
- CloudWatch alarms for Scheduler target errors, non-zero task exits, and DLQ backlog

## Usage

```hcl
module "scheduled_job" {
  source = "./modules/ecs-scheduled-job"

  environment = "dev"
  application = "platform"
  service     = "daily-report"
  owner       = "platform-team"
  repository  = "github.com/example/platform"
  cost_center = "shared-platform"

  cluster_arn        = var.cluster_arn
  subnet_ids         = var.subnet_ids
  security_group_ids = var.security_group_ids

  container_image              = "123456789012.dkr.ecr.us-east-1.amazonaws.com/daily-report:2026-07-10-abc123"
  container_command            = ["./run-daily-report"]
  schedule_expression          = "cron(0 6 * * ? *)"
  enable_ecr_pull_permissions = true

  ecr_repository_arns = [
    "arn:aws:ecr:us-east-1:123456789012:repository/daily-report"
  ]

  alarm_actions = [var.alert_topic_arn]
}
```

Account-specific values belong in environment variables, CI secrets, Terraform Cloud variables, or uncommitted local variable files. Do not commit real account IDs, ARNs, subnet IDs, security group IDs, or secrets into this repository.

## IAM Model

The module separates roles by responsibility:

- Execution role: lets ECS pull the image, write task logs, and read explicitly configured container secrets.
- Task role: starts with no application permissions. Add only the permissions the job code needs through `task_policy_statements` or `task_managed_policy_arns`.
- Scheduler role: can call `ecs:RunTask` for this task definition on the configured cluster, pass only this task's roles to ECS, and send failed deliveries to this job's DLQ.

Two AWS APIs require narrow wildcard usage:

- `ecr:GetAuthorizationToken` requires `Resource = "*"`.
- `ecs:TagResource` is used with `ecs:CreateAction = RunTask` so tags can propagate to tasks created by `RunTask`.

Do not add broader wildcard permissions without an explicit security review.

## Secrets

Use `container_secrets` for ECS secret ARN references. Add the matching ARNs to `execution_secret_arns`, and add `kms_key_arns` when the secret uses a customer-managed KMS key. Do not pass secrets through `container_environment`.

## Alarms

The module always creates:

- `${environment}-${application}-${service}-scheduler-target-errors`
- `${environment}-${application}-${service}-task-failures`
- `${environment}-${application}-${service}-dlq-visible-messages`

Set `alarm_actions` to notify SNS topics or incident-management integrations. Without actions, alarms still exist for dashboards and manual inspection.

## Runbook

1. Check the Scheduler schedule state and recent invocations in EventBridge Scheduler.
2. Check `${environment}-${application}-${service}-scheduler-target-errors` for target delivery failures.
3. Check `${environment}-${application}-${service}-task-failures` for non-zero container exits.
4. Inspect the DLQ for failed delivery payloads.
5. Inspect ECS task stop reasons and container exit codes for recent task runs.
6. Inspect CloudWatch Logs at `/ecs/${environment}-${application}-${service}` and task state events at `/aws/events/${environment}-${application}-${service}-task-state`.
7. Confirm the container image tag is immutable and exists in the target registry.
8. Confirm task role permissions match the job's current dependency calls.

Jobs should be idempotent. Scheduler retries and operator replays from the DLQ can cause repeated attempts for the same logical run.

## Rollback

Rollback is a Terraform revert to the previous module or environment version, followed by `terraform plan` and an approved `terraform apply` in the target account. If a bad image tag was deployed, prefer updating the caller's `container_image` back to the previous immutable tag. If the schedule itself is unsafe, set `schedule_enabled = false` and apply while the application fix is prepared.
