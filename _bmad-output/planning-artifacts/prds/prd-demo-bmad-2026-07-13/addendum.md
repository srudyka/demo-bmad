# Technical and Delivery Addendum

This addendum preserves implementation constraints supplied during product discovery. The PRD defines required capabilities and outcomes; architecture work should refine the mechanisms below without weakening them.

## Required Platform Choices

- AWS is the target cloud and ECS Fargate is the preferred compute platform.
- Terraform is the required infrastructure-as-code tool.
- EventBridge Scheduler provides scheduled invocation for MVP; legacy EventBridge scheduled rules are excluded.
- GitHub Actions is the preferred CI/CD platform.
- CloudWatch is the default platform for logs, metrics, alarms, and dashboards.
- GitHub OIDC is preferred for AWS authentication; long-lived CI credentials are prohibited.

## Infrastructure Constraints

- Support separate dev, staging, and production environments across multiple AWS accounts.
- Do not hardcode AWS account IDs, regions, ARNs, or environment names.
- Run tasks in private subnets with minimally scoped security groups.
- Separate ECS task execution roles from application task roles.
- Make task IAM permissions explicit and reviewable; justify any unavoidable wildcard scope.
- Source secrets from AWS Secrets Manager, SSM Parameter Store, or an approved secrets platform such as Infisical. Do not store secrets in Git or pass plaintext secret values from Terraform as ordinary environment variables.
- Apply the repository's standard ownership and resource tags.
- Consumers supply an input such as `production_alarm_notification_target_arn` for the production notification destination.

## Delivery Constraints

- Pull requests run format checks, Terraform validation, security scanning, and Terraform plan.
- Plan and apply are separated, and production apply requires approval.
- Production-impacting changes document expected impact and rollback steps.
- Documentation includes example usage, security guidance, a runbook template, and operational troubleshooting.

## Initial Distribution Pattern

- Publish the Terraform Module from an internal GitHub repository and reusable workflows from a centralized platform repository such as `.github` or `platform-workflows`.
- Consumers pin an immutable release reference rather than a moving branch. A representative source declaration is:

  ```hcl
  source = "git::ssh://git@github.com/org/platform-terraform-modules.git//modules/ecs-scheduled-job?ref=<full-commit-sha>"
  ```

- Associate the immutable commit with a semantic release such as `v1.0.0`, and announce upgrades through GitHub releases, release notes, and the internal engineering communication channel.

## Initial Completion Detection Pattern

- Each expected occurrence receives an architecture-approved unique occurrence ID, such as the combination of job name and canonical scheduled time.
- A completion result carries job name, occurrence ID, start time, completion time, status, exit code, and optional error reason.
- Each job can emit a documented success marker such as `JOB_COMPLETED_SUCCESSFULLY` only after business completion, but the marker must include the matching occurrence ID and is not sufficient proof by itself.
- The implementation may use structured CloudWatch Logs parsing, DynamoDB-backed run tracking, Scheduler-supplied occurrence metadata, ECS task metadata plus a reporter, a lightweight completion API, CloudWatch Embedded Metric Format, or another mechanism that meets the occurrence-level contract.
- ECS task-state and exit-code detection distinguishes launch/runtime failure, while EventBridge signals cover schedule-delivery failure where available. All signals must correlate to the expected occurrence or produce an explicit ambiguous state.

## Candidate Future Mechanisms

These are not version-one commitments: centralized cross-job dashboards, organization-wide aggregated success metrics, external incident integrations, Step Functions, dead-letter queues, retry and backoff templates, cost reporting, migration tooling, policy-as-code, and golden-path templates.

## Research-Backed Architecture Inputs

These findings constrain architecture and acceptance testing but do not prescribe every implementation detail.

### Scheduling and Completion

- AWS recommends EventBridge Scheduler over legacy scheduled rules. Scheduler delivery is at least once, so retries can create duplicates and do not replace application idempotency or locking.
- Scheduler target success indicates only the outcome of the target API request. ECS `RunTask` can report failures separately, and an accepted task can later fail to provision or exit non-zero. Observability must cover schedule delivery, ECS task lifecycle, and application completion separately.
- Native Scheduler CloudWatch metrics are best-effort and grouped by Schedule Group rather than by individual schedule. Reliable per-job missed-run detection requires a separate completion signal and deadline evaluation.
- A Fargate `stopTimeout` defines a termination grace period, not a maximum execution duration. Forced maximum runtime needs application self-termination or an external watchdog; the PRD initially assumes detection and operator response.

### IAM and Networking

- The design needs separate Scheduler execution, ECS task execution, and application task roles. `iam:PassRole` should be scoped to exact roles.
- Private Fargate networking still needs NAT or the required VPC endpoints for ECR, S3, CloudWatch Logs, Secrets Manager, SSM, and workload dependencies.

### Delivery and Version Integrity

- GitHub OIDC trust must restrict the audience and subject claims to the intended repository and deployment context. AWS cannot use GitHub custom OIDC claims to enforce use of a specific reusable workflow.
- Because AWS cannot evaluate GitHub's custom workflow claim, production authorization needs a procedural boundary GitHub can enforce: a dedicated deployment repository or required-workflow rules plus a protected Environment. OIDC trust alone is insufficient.
- GitHub's OIDC subject formats are evolving toward immutable organization and repository IDs. Account onboarding must generate a trust policy for the repository's active subject format instead of assuming a name-only subject.
- A protected production Environment should enforce required reviewers, self-review prevention, restricted refs, and controlled concurrency where the organization's GitHub plan supports those controls.
- Pull-request plans are previews. Production automation should plan the deployment revision, approve, and apply the exact saved plan; saved plans are sensitive artifacts.
- Pin reusable workflows and third-party actions to full commit SHAs. Terraform provider lock files do not pin remote module versions. Production consumers should therefore use an immutable registry version or Git commit instead of a movable Git tag.

## Primary Sources

- [AWS: Schedule Amazon ECS tasks with EventBridge Scheduler](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/tasks-scheduled-eventbridge-scheduler.html)
- [AWS: EventBridge Scheduler overview](https://docs.aws.amazon.com/scheduler/latest/UserGuide/what-is-scheduler.html)
- [AWS: Scheduler CloudWatch metrics](https://docs.aws.amazon.com/scheduler/latest/UserGuide/monitoring-cloudwatch.html)
- [AWS: ECS RunTask API](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_RunTask.html)
- [AWS: ECS task lifecycle events](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-lifecycle-events.html)
- [AWS: ECS task execution IAM role](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html)
- [AWS: Fargate task networking](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-task-networking.html)
- [GitHub: Configuring OpenID Connect in AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws)
- [GitHub: Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
- [GitHub: Reusing workflow configurations](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations)
- [HashiCorp: Standard module structure](https://developer.hashicorp.com/terraform/language/modules/develop/structure)
- [HashiCorp: Terraform validate](https://developer.hashicorp.com/terraform/cli/commands/validate)
- [HashiCorp: Terraform automation guidance](https://developer.hashicorp.com/terraform/tutorials/automation/automate-terraform)
- [HashiCorp: Terraform dependency lock file](https://developer.hashicorp.com/terraform/language/files/dependency-lock)
