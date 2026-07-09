# ECS Scheduled Job Module

This module standardizes one ECS Fargate scheduled job. It creates the task
definition, CloudWatch log group, task execution role, task role, EventBridge
Scheduler schedule, scheduler role, and CloudWatch alarms for Scheduler delivery
failures.

Use one module instance per job. That keeps IAM, schedules, alarms, and rollback
scope easy to review.

## Resources

- `aws_ecs_task_definition`
- `aws_scheduler_schedule_group`
- `aws_scheduler_schedule`
- `aws_cloudwatch_log_group`
- `aws_cloudwatch_metric_alarm` for `TargetErrorCount`
- `aws_cloudwatch_metric_alarm` for `InvocationDroppedCount`
- `aws_cloudwatch_event_rule` for ECS stopped tasks with non-zero container
  exit codes
- IAM roles for ECS task execution, ECS task runtime permissions, and Scheduler
  invocation

The Scheduler metrics are scoped to a dedicated schedule group by default. This
avoids alarms on unrelated jobs in the default schedule group. The ECS task
failure rule can route failed task events to the same targets as
`alarm_action_arns`, or to `task_failure_event_target_arns` when those should be
different.

## IAM Model

The module separates three roles:

- Execution role: image pull, log delivery, and optional secret injection.
- Task role: job-specific AWS permissions supplied by `task_policy_statements`.
- Scheduler role: `ecs:RunTask` against this task definition and `iam:PassRole`
  for the two ECS task roles.

Keep `task_policy_statements` narrow. If a job requires wildcard resources for
an AWS API that does not support resource-level permissions, document that in
the caller's review notes.

## Required Inputs

- `name`
- `environment`
- `application`
- `service`
- `owner`
- `cluster_arn`
- `subnet_ids`
- `security_group_ids`
- `container_image`
- `cpu`
- `memory`
- `schedule_expression`

`name` is capped at 53 characters so generated IAM role names stay under AWS
role-name limits after suffixes are added.

`container_image` must not use the mutable `latest` tag. Digest-pinned images
are preferred for production scheduled jobs.

The module does not create VPCs, ECS clusters, security groups, container
registries, or remote state. Those are account/environment concerns.

## Example

```hcl
module "nightly_job" {
  source = "../../modules/ecs-scheduled-job"

  name        = "prod-platform-nightly-job"
  environment = "prod"
  application = "platform"
  service     = "ecs-scheduled-jobs"
  owner       = "platform-engineering"

  cluster_arn        = var.cluster_arn
  subnet_ids         = var.private_subnet_ids
  security_group_ids = var.security_group_ids
  container_image    = var.container_image
  cpu                = 256
  memory             = 512

  schedule_expression = "cron(0 6 * * ? *)"
  alarm_action_arns   = var.alarm_action_arns

  task_policy_statements = [
    {
      sid       = "ReadJobParameters"
      actions   = ["ssm:GetParameter", "ssm:GetParameters"]
      resources = ["arn:aws:ssm:*:*:parameter/prod/platform/nightly-job/*"]
    }
  ]
}
```

## Observability

Every job gets:

- CloudWatch Logs under `/ecs/scheduled/<name>` unless overridden.
- A target error alarm for Scheduler target invocation errors.
- A dropped invocation alarm for Scheduler events that cannot be delivered.

Set `alarm_action_arns` to the owning team's SNS topic or incident-management
integration. Leave it empty only for local examples or pre-production tests
where alarm routing is intentionally deferred.

If `dead_letter_queue_arn` is set, the Scheduler role gets `sqs:SendMessage` to
that queue. If task-failure EventBridge targets are SNS topics, make sure the
topic policy allows EventBridge to publish.

The module also creates an EventBridge rule for ECS task state changes where a
container exits non-zero. This catches the important case where Scheduler
successfully starts a task but the job itself fails.

## Rollback

For a bad schedule or container change:

1. Set `schedule_state = "DISABLED"` and apply to stop new runs.
2. Revert the caller's module input change and apply again.
3. Inspect the log group and Scheduler alarms for failed or partial runs.
4. If the task made external changes, follow the job-specific runbook for data
   reconciliation.

Avoid destroying the module as the first rollback step. Disabling the schedule
preserves logs, IAM roles, and task definition history for investigation.

## Validation

```bash
terraform fmt -check -recursive
terraform -chdir=modules/ecs-scheduled-job init -backend=false
terraform -chdir=modules/ecs-scheduled-job validate
```
