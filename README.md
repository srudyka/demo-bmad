# demo-bmad

Internal platform infrastructure patterns for AWS. This repository currently provides a reusable Terraform module for ECS Fargate scheduled jobs with EventBridge Scheduler, CloudWatch observability, retry/DLQ handling, and least-privilege IAM.

## ECS Scheduled Jobs Platform Service

The module at `modules/ecs-scheduled-job` standardizes one scheduled container job across AWS accounts. It creates:

- ECS Fargate task definition with explicit CPU and memory
- CloudWatch Log Group with configured retention
- Separate ECS execution role, ECS task role, and EventBridge Scheduler role
- EventBridge Scheduler schedule with retry policy
- SQS dead-letter queue for failed target delivery
- CloudWatch alarms for Scheduler target errors, non-zero task exits, and DLQ backlog
- Required AWS tags using `<environment>-<application>-<service>` naming

Account-specific infrastructure remains outside the module. Callers provide the ECS cluster ARN, private subnet IDs, security group IDs, image tag, schedule expression, alert destinations, and application-specific task permissions.

## Repository Layout

```text
modules/
  ecs-scheduled-job/
    examples/basic/
envs/
  example/
.github/workflows/
  terraform.yml
```

## Usage

Use the module from an account/environment root module:

```hcl
module "ecs_scheduled_job" {
  source = "../../modules/ecs-scheduled-job"

  environment = "dev"
  application = "platform"
  service     = "daily-report"
  owner       = "platform-team"

  cluster_arn        = var.cluster_arn
  subnet_ids         = var.subnet_ids
  security_group_ids = var.security_group_ids

  container_image     = var.container_image
  container_command   = ["./run-daily-report"]
  schedule_expression = "cron(0 6 * * ? *)"

  alarm_actions = [var.alert_topic_arn]
}
```

Do not commit real account IDs, ARNs, subnet IDs, security group IDs, `.tfvars` files containing environment values, Terraform state, plan files, credentials, or secrets.

## Validation

Run these checks before opening or merging changes:

```bash
terraform fmt -check -recursive
terraform -chdir=modules/ecs-scheduled-job init -backend=false
terraform -chdir=modules/ecs-scheduled-job validate
terraform -chdir=modules/ecs-scheduled-job/examples/basic init -backend=false
terraform -chdir=modules/ecs-scheduled-job/examples/basic validate
terraform -chdir=envs/example init -backend=false
terraform -chdir=envs/example validate
```

GitHub Actions runs the same Terraform format/init/validate checks and a Trivy IaC security scan for pull requests and pushes that touch infrastructure files.

## Security Notes

- Prefer private subnets and keep `assign_public_ip = false`.
- Use immutable image tags; the module rejects `:latest`.
- Pass non-secret settings through `container_environment`.
- Pass secret ARN references through `container_secrets` and grant only the matching `execution_secret_arns` and `kms_key_arns`.
- Set `enable_ecr_pull_permissions = true` and provide `ecr_repository_arns` for private ECR images. Non-ECR jobs do not receive ECR permissions by default.
- Add application permissions through `task_policy_statements` or `task_managed_policy_arns`; the task role starts with no application permissions.
- The execution role uses `Resource = "*"` only for `ecr:GetAuthorizationToken`, which AWS requires. The scheduler role uses `ecs:TagResource` with an `ecs:CreateAction = RunTask` condition for tag propagation.

## Operations Runbook

For a failed or missed scheduled job:

1. Check EventBridge Scheduler for schedule state and recent target delivery errors.
2. Check the `${environment}-${application}-${service}-scheduler-target-errors` alarm.
3. Check the `${environment}-${application}-${service}-task-failures` alarm for non-zero container exits.
4. Inspect the SQS DLQ and confirm whether failed delivery payloads are accumulating.
5. Check ECS stopped task reasons, container exit codes, and image pull errors.
6. Inspect task logs at `/ecs/${environment}-${application}-${service}` and ECS task state events at `/aws/events/${environment}-${application}-${service}-task-state`.
7. Confirm the image tag exists and is immutable.
8. Confirm task IAM permissions still match the job's dependency calls.

Scheduled jobs should be idempotent because Scheduler retries and DLQ replays can repeat the same logical run.

## Rollback

Rollback by reverting the environment or module change to the previous Git revision, running `terraform plan`, and applying after the normal approval process for the target account. For a bad application image, update the caller's `container_image` back to the previous immutable tag. For an unsafe schedule, set `schedule_enabled = false` and apply while the fix is prepared.
