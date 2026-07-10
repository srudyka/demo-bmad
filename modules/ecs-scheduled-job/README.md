# ECS Scheduled Job Terraform Module

This module creates the common platform resources for a private ECS Fargate scheduled job:

- ECS task definition with CloudWatch Logs.
- EventBridge Scheduler schedule with bounded retries.
- SQS dead-letter queue for failed scheduler delivery.
- Separate ECS execution, ECS task, and Scheduler invocation IAM roles.
- CloudWatch alarms for ECS task failures, Scheduler target errors, dropped invocations, and DLQ message age.

Callers provide account-specific values such as the ECS cluster, private subnet IDs, security group IDs, and optional SNS alarm topics.

## Usage

```hcl
module "scheduled_job" {
  source = "./modules/ecs-scheduled-job"

  tags = {
    Environment = "dev"
    Application = "platform"
    Service     = "cleanup-job"
    Owner       = "platform-team"
    ManagedBy   = "Terraform"
    Repository  = "demo-bmad"
  }

  cluster_arn        = "arn:aws:ecs:us-east-1:123456789012:cluster/dev-platform-cluster"
  cluster_name       = "dev-platform-cluster"
  subnet_ids         = ["subnet-0123456789abcdef0"]
  security_group_ids = ["sg-0123456789abcdef0"]

  container_image   = "123456789012.dkr.ecr.us-east-1.amazonaws.com/cleanup:v1.2.3"
  container_command = ["./cleanup"]

  ecr_repository_arns = [
    "arn:aws:ecr:us-east-1:123456789012:repository/cleanup"
  ]

  compute = {
    cpu    = 256
    memory = 512
  }

  schedule_expression = "rate(1 hour)"
}
```

See `examples/basic` for a placeholder-safe root module.

## Inputs

Important inputs:

- `tags`: Required `Environment`, `Application`, `Service`, `Owner`, and `ManagedBy = "Terraform"` tags. These drive predictable names.
- `cluster_arn` and `cluster_name`: Existing ECS cluster target.
- `subnet_ids` and `security_group_ids`: Private network placement for the Fargate task.
- `container_image`: Immutable image reference. The module rejects untagged images and `latest`.
- `container_secrets`: Map of environment variable names to Secrets Manager or SSM parameter ARNs.
- `secret_kms_key_arns`: KMS key ARNs needed for CMK-encrypted secrets or parameters.
- `ecr_repository_arns`: Required when using private ECR images so the execution role can pull the image.
- `compute`: Valid ECS Fargate CPU and memory pair.
- `schedule_expression`: `rate(...)`, `cron(...)`, or `at(...)` expression.
- `alarm_sns_topic_arns`: Optional SNS topics for alarm actions.
- `kms_key_arn`: Optional customer-managed KMS key ARN for CloudWatch Logs, the SQS DLQ, and EventBridge Scheduler.

## Outputs

The module exports the schedule name and ARN, task definition ARN, execution/task/scheduler role names and ARNs, container log group, ECS task failure event log group, DLQ URL and ARN, and alarm names and ARNs.

## Security Notes

- The execution role, task role, and Scheduler role are separate.
- The task role has no application permissions by default. Attach least-privilege permissions outside the module using the exported task role name or ARN.
- Scheduler can run only the generated task definition on the configured ECS cluster and can pass only the generated task roles.
- Scheduler failed delivery is captured in an encrypted SQS DLQ.
- Plaintext secret values are not accepted in `container_secrets`; only Secrets Manager and SSM parameter ARNs are valid.
- Add `secret_kms_key_arns` when secrets or parameters use customer-managed KMS keys.
- `ecr:GetAuthorizationToken` uses `Resource = "*"`, only when `ecr_repository_arns` is set, because AWS does not support resource-level permissions for that action.

## Observability

- Container logs go to `/aws/ecs/<environment>-<application>-<service>` with explicit retention.
- ECS task failures are captured from ECS task state change events and counted through a CloudWatch Logs metric filter.
- Scheduler delivery failures are visible through Scheduler CloudWatch metrics and the DLQ.
- Alarms cover ECS task failures, Scheduler target errors, dropped invocations, and DLQ message age.
- Application-level success and failure should be logged by the container. For production-critical jobs, emit a domain-specific success metric from the application so operators can alarm on missed successful completion.

## Runbook

To verify a job:

1. Confirm the schedule is enabled in EventBridge Scheduler.
2. Check ECS task history in the configured cluster.
3. Review container logs in the exported CloudWatch log group.
4. Check the exported alarm names, ECS task failure event log group, and the DLQ URL.

For `task-failures`:

- Open the exported ECS task failure event log group to find the failed task ARN and non-zero container exit code.
- Review the matching container logs in the exported ECS log group.
- Replay only if the job is idempotent.

For `scheduler-target-errors`:

- Confirm the Scheduler role can call `ecs:RunTask` for the task definition and cluster.
- Confirm the Scheduler role can pass the task and execution roles.
- Confirm private subnets and security groups allow required egress to pull images and reach dependencies.

For `scheduler-dropped-invocations`:

- Check whether retry age or retry attempts are too low for the dependency outage pattern.
- Inspect the DLQ for failed events before purging.

For `dlq-oldest-message-age`:

- Read the oldest message, identify the failed schedule invocation, and replay only if the job is idempotent.
- Purge messages only after recording the incident context and confirming replay is not required.

## Rollback

Emergency stop:

```hcl
schedule_enabled = false
```

Image rollback:

```hcl
container_image = "123456789012.dkr.ecr.us-east-1.amazonaws.com/cleanup:v1.2.2"
```

Infrastructure rollback:

1. Revert the caller root module to the last known good module version and immutable image tag.
2. Run `terraform plan` and confirm only the intended schedule/task definition changes are present.
3. Apply through the approved environment pipeline or manual approval process.
4. Verify the schedule, ECS task history, CloudWatch logs, alarms, and DLQ.

Do not destroy the DLQ until failed invocations have been triaged.

## Validation

```bash
terraform fmt -check -recursive
terraform -chdir=modules/ecs-scheduled-job init -backend=false
terraform -chdir=modules/ecs-scheduled-job validate
terraform -chdir=modules/ecs-scheduled-job/examples/basic init -backend=false
terraform -chdir=modules/ecs-scheduled-job/examples/basic validate
uvx --from checkov checkov -d . --framework terraform
```
