# demo-bmad

## Terraform Modules

### ECS Scheduled Job

`modules/ecs-scheduled-job` provides a reusable Terraform module for private ECS Fargate scheduled jobs using EventBridge Scheduler. It creates:

- ECS task definition and CloudWatch log group.
- Separate execution, task, and Scheduler IAM roles.
- EventBridge Scheduler schedule with bounded retries.
- SQS dead-letter queue for failed scheduler delivery.
- CloudWatch alarms for ECS task failures, Scheduler target errors, dropped invocations, and DLQ message age.

The module is account-agnostic. Callers provide the ECS cluster ARN/name, private subnet IDs, security group IDs, immutable container image, required tags, and optional SNS alarm topics from their own environment root modules.

Start with `modules/ecs-scheduled-job/examples/basic` for a placeholder-safe example.

Validation:

```bash
terraform fmt -check -recursive
terraform -chdir=modules/ecs-scheduled-job init -backend=false
terraform -chdir=modules/ecs-scheduled-job validate
terraform -chdir=modules/ecs-scheduled-job/examples/basic init -backend=false
terraform -chdir=modules/ecs-scheduled-job/examples/basic validate
uvx --from checkov checkov -d . --framework terraform
```

Operational notes:

- Use private subnets and security groups with only required egress.
- Use Secrets Manager or SSM Parameter Store ARNs for secrets; do not pass plaintext secrets.
- Add secret KMS key ARNs when referenced secrets or parameters use customer-managed keys.
- Provide ECR repository ARNs when using private ECR images.
- Use immutable image tags or digests. `latest` is rejected by module validation.
- For emergency stop or rollback, set `schedule_enabled = false` in the caller root, or revert `container_image` to the previous immutable tag and apply through the approved environment process.
- Inspect the module outputs for the container log group, ECS task failure event log group, DLQ, and alarm names during incident triage.

## BMAD Customization

Team-level BMAD overrides live in `_bmad/custom/`. The AWS Terraform
implementation contract is captured in
`_bmad/custom/standards/aws-terraform-implementation.md` and is loaded by the
BMAD spec, story creation, implementation, code review, readiness, and
developer-agent workflows.

Use this standard to keep AI-generated Terraform implementations consistent
across branches. If an implementation intentionally deviates from the standard,
document the reason in the story or PR notes.
