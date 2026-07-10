# demo-bmad

## BMAD Customization

Team-level BMAD overrides live in `_bmad/custom/`. The AWS Terraform
implementation contract is captured in
`_bmad/custom/standards/aws-terraform-implementation.md` and is loaded by the
BMAD spec, story creation, implementation, code review, readiness, and
developer-agent workflows.

Use this standard to keep AI-generated Terraform implementations consistent
across branches. If an implementation intentionally deviates from the standard,
document the reason in the story or PR notes.

## ECS Scheduled Jobs

Reusable ECS Fargate scheduled jobs are implemented in
`modules/ecs-scheduled-job`. The module standardizes EventBridge Scheduler,
task definitions, IAM roles, CloudWatch Logs, Scheduler retry behavior, SQS DLQ
failure capture, and CloudWatch alarms without adding account-specific
environment roots.

Start with:

- `modules/ecs-scheduled-job/README.md` for module usage and inputs.
- `modules/ecs-scheduled-job/examples/basic` for a minimal validating example.
- `docs/runbooks/ecs-scheduled-job.md` for operations, troubleshooting, and
  rollback.

Validation:

```bash
terraform fmt -check
terraform -chdir=modules/ecs-scheduled-job init -backend=false
terraform -chdir=modules/ecs-scheduled-job validate
terraform -chdir=modules/ecs-scheduled-job/examples/basic init -backend=false
terraform -chdir=modules/ecs-scheduled-job/examples/basic validate
```

The GitHub Actions workflow in `.github/workflows/terraform.yml` runs Terraform
format, validation, and Checkov IaC scanning on pull requests. It does not apply
infrastructure or require production credentials.
