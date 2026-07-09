---
project_name: 'demo-bmad'
user_name: 'Srudyka'
date: '2026-07-09'
### sections_completed: ['technology_stack', 'language_specific_rules']
sections_completed:

* technology_stack
* agent_operating_rules
* aws_rules
* terraform_rules
* cicd_rules
* security_rules
* observability_rules
* reliability_rules
* documentation_rules
* definition_of_done

---

# Project Context for AI Agents

## Purpose

This project follows a DevOps/SRE-first engineering style.

Prioritize:

* Reliability
* Repeatability
* Security
* Observability
* Automation
* Operational simplicity
* Clear rollback paths
* Infrastructure as Code
* Production readiness

Do not optimize for cleverness. Optimize for maintainability, debuggability, and safe delivery.

---

## Agent Operating Rules

AI agents working on this project must follow these rules:

* Treat this file as the source of implementation standards.
* If a story, task, or prompt conflicts with this file, call out the conflict before implementing.
* Before coding, identify the affected areas: AWS, Terraform, CI/CD, networking, IAM, observability, security, or documentation.
* Prefer small, reviewable changes over large rewrites.
* Do not invent cloud resources, naming conventions, secrets, account IDs, regions, or environment names.
* Follow existing repo structure when available.
* If the existing pattern is unsafe or outdated, explain the risk and propose a safer migration path.
* Every infrastructure change must be reproducible through code.
* Every production-impacting change must include rollback considerations.
* Every new service or job must include logs, metrics, alarms, and basic runbook notes.
* Never commit secrets, tokens, credentials, `.env` files, private keys, or generated state files.
* Do not use placeholder security such as `Resource = "*"`, `Principal = "*"`, or `0.0.0.0/0` unless explicitly justified and scoped.

---

## Technology Stack & Preferred Tools

### Cloud

* Primary cloud: AWS
* Preferred compute: ECS Fargate
* Use EC2 only when there is a clear technical reason.
* Use EKS/Kubernetes only when orchestration requirements justify the added operational complexity.
* Prefer managed AWS services when they reduce operational burden.

### Infrastructure as Code

* Terraform is the default IaC tool.
* Use reusable Terraform modules for repeated infrastructure patterns.
* Terraform code must be clear, explicit, and reviewable.

### CI/CD

Preferred tools:

* GitHub Actions
* Bitbucket Pipelines
* Jenkins, only when required by existing project constraints

CI/CD pipelines should support:

* Lint
* Format check
* Validate
* Security scan
* Terraform plan
* Manual approval before production apply
* Controlled rollback or redeploy

### Languages

Preferred automation languages:

* Python
* Bash
* Go, only when a compiled CLI/tool is justified

Python is preferred for AWS automation, Lambda utilities, and operational scripts.

Bash is acceptable for simple glue logic but should not become complex business logic.

---

## AWS Design Rules

### General AWS Rules

* Use least-privilege IAM.
* Use resource tagging consistently.
* Prefer private networking for internal services.
* Prefer VPC endpoints where they reduce NAT dependency and improve private access.
* Avoid public exposure unless explicitly required.
* Use AWS-managed services where they reduce operational complexity.
* Production resources must be monitored.
* Production resources must have clear ownership tags.
* Production changes must include rollback notes.

### Required Tags

All AWS resources should include at least:

* `Environment`
* `Application`
* `Service`
* `Owner`
* `ManagedBy`
* `CostCenter` if applicable
* `Repository` if applicable

Default:

```text
ManagedBy = Terraform
```

### Naming Convention

Use predictable names:

```text
<environment>-<application>-<component>
```

Examples:

```text
prod-billing-worker
dev-platform-ecs-scheduled-task
staging-api-alb
```

Avoid random, vague, or overly abbreviated names.

---

## ECS / Fargate Rules

ECS Fargate is the preferred runtime for containerized services and scheduled jobs.

For every ECS service or task definition:

* Define CPU and memory explicitly.
* Configure CloudWatch Logs.
* Use task roles and execution roles separately.
* Use least-privilege task IAM permissions.
* Use Secrets Manager, SSM Parameter Store, or Infisical for secrets.
* Never pass secrets as plain environment variables from Terraform code.
* Configure health checks where applicable.
* Configure deployment circuit breaker where applicable.
* Include rollback instructions.
* Include runbook notes for common failures.

For ECS scheduled tasks:

* Use EventBridge Scheduler or EventBridge rules.
* Include alarm strategy for failed runs.
* Log successful completion clearly.
* Log failed execution clearly.
* Include retry behavior where appropriate.
* Make timeout behavior explicit.
* Make idempotency expectations explicit.

---

## Terraform Rules

### Terraform Structure

Prefer this module structure:

```text
modules/
  <module-name>/
    main.tf
    variables.tf
    outputs.tf
    versions.tf
    README.md
    examples/
```

For environments:

```text
envs/
  dev/
  staging/
  prod/
```

or follow the existing repository convention if one already exists.

### Terraform Style

* Use modules for reusable patterns.
* Keep modules focused and composable.
* Avoid giant modules that manage unrelated concerns.
* Prefer explicit variables over hidden defaults.
* Every variable should have a description.
* Every output should have a description.
* Use validation blocks for important variables.
* Use `locals` for naming, tagging, and derived values.
* Avoid hardcoded account IDs, ARNs, regions, and environment-specific values.
* Do not use provisioners unless there is no better option.
* Do not use `null_resource` for normal infrastructure workflows.
* Do not commit `.terraform/`, `terraform.tfstate`, or plan output files.
* Do not make production-destructive changes without calling them out clearly.

### Terraform Quality Gates

Before considering Terraform work complete:

```bash
terraform fmt -check
```

```bash
terraform validate
```

For modules, include at least one usage example.

For production infrastructure, include expected plan impact in the PR notes.

### Terraform Security

* IAM policies must be scoped to required actions and resources.
* Avoid wildcard permissions.
* If wildcard permissions are unavoidable, explain why.
* S3 buckets must block public access unless explicitly required.
* Encrypt storage by default.
* Use KMS where appropriate.
* Security groups should be minimal and documented.
* Avoid broad ingress like `0.0.0.0/0` except for public HTTP/HTTPS entry points.

---

## CI/CD Rules

Every pipeline should be designed for safe delivery.

### Required Pipeline Stages

For application code:

* Checkout
* Dependency install
* Lint
* Unit tests
* Build
* Security scan
* Artifact publish
* Deploy
* Smoke test where practical

For Terraform:

* Checkout
* Terraform fmt check
* Terraform validate
* Security scan
* Terraform plan
* Manual approval for production
* Terraform apply

### Deployment Rules

* Production deployment must not be fully automatic unless explicitly approved.
* Rollback strategy must be documented.
* Build artifacts should be versioned.
* Docker images should use immutable tags.
* Avoid deploying from `latest`.
* Prefer commit SHA, semantic version, or release tag.
* Pipeline logs should make it clear what version was deployed.

### Secrets in CI/CD

* Use CI/CD secret storage.
* Do not print secrets.
* Do not echo sensitive environment variables.
* Do not commit generated credentials.
* Prefer OIDC-based AWS authentication over long-lived AWS keys.

---

## Security Rules

Security is part of the default implementation, not a separate afterthought.

### Secrets

Use one of:

* AWS Secrets Manager
* AWS SSM Parameter Store
* Infisical
* CI/CD secret manager

Never store secrets in:

* Git
* Terraform variables files committed to repo
* Docker images
* Plaintext config files
* README examples with real values

### IAM

* Use least privilege.
* Separate human roles from workload roles.
* Separate ECS task role from ECS execution role.
* Prefer short-lived credentials.
* Prefer OIDC federation for CI/CD.
* Avoid static AWS access keys where possible.

### Network Security

* Prefer private subnets for application workloads.
* Public subnets should be limited to load balancers, NAT gateways, and explicitly public components.
* Security groups should describe intent.
* NACLs should remain simple unless there is a strong reason.
* Prefer security groups over NACLs for application-level access control.
* Do not rely on DNS names in security groups because AWS security groups operate on IP/CIDR or referenced security groups, not DNS names.
* For third-party outbound allowlists, document the limitation and prefer stable egress through NAT gateway, proxy, PrivateLink, or vendor-supported static endpoints.

### Compliance Mindset

When handling sensitive systems:

* Assume auditability matters.
* Prefer explicit access control.
* Log administrative actions.
* Document production access paths.
* Document data flow for systems touching sensitive data.

---

## Observability Rules

Every production service must be observable.

### Required Observability

For each service, job, or infrastructure component, define:

* Logs
* Metrics
* Alarms
* Dashboard if production-critical
* Runbook notes
* Known failure modes

### CloudWatch Logs

* ECS tasks must send logs to CloudWatch Logs.
* Log group names should follow project naming convention.
* Retention must be explicitly configured.
* Production logs should not have infinite retention unless required.
* Logs must not contain secrets or sensitive tokens.

### Alarms

Use CloudWatch alarms for production-critical systems.

Common alarms:

* ECS service unhealthy tasks
* ECS task failures
* ALB 5xx errors
* Target response time
* RDS CPU
* RDS storage
* RDS connections
* Lambda errors
* Lambda duration
* SQS queue age
* EventBridge scheduled task failure
* OpenSearch cluster health if applicable

### Dashboards

Dashboards should focus on operational questions:

* Is the service healthy?
* Is traffic normal?
* Are errors increasing?
* Is latency increasing?
* Are dependencies failing?
* Did the last scheduled job succeed?
* What changed recently?

Avoid dashboards that show many metrics but do not answer operational questions.

---

## Reliability / SRE Rules

### Reliability Principles

* Design for failure.
* Prefer simple, observable systems.
* Make failure modes explicit.
* Use retries with backoff where appropriate.
* Avoid infinite retries.
* Use dead-letter queues where appropriate.
* Make jobs idempotent where possible.
* Avoid hidden manual steps.
* Automate repeatable operational tasks.

### Production Readiness

A production-ready service should include:

* Deployment pipeline
* Rollback path
* Logs
* Metrics
* Alarms
* Runbook
* Ownership
* IAM review
* Secret handling
* Cost consideration
* Failure mode notes

### Rollback

Every deployment story should answer:

* How do we roll back?
* What artifact/version do we roll back to?
* Is rollback safe for database/schema changes?
* Are there migrations?
* Are there compatibility concerns?
* What is the expected recovery time?

---

## Database Rules

### General

* Do not make destructive schema changes without explicit migration and rollback notes.
* Prefer backward-compatible migrations.
* Separate schema migration from application deployment when risk is high.
* Include database connection limits in architecture decisions.
* Consider RDS Proxy where connection management is a known risk.
* Add monitoring for CPU, storage, latency, connections, and queue depth.

### RDS / PostgreSQL

For production RDS:

* Enable encryption.
* Configure backups.
* Configure retention intentionally.
* Monitor CPU, connections, latency, storage, and DiskQueueDepth.
* Use Multi-AZ where availability requirements justify it.
* Avoid manual changes outside Terraform unless emergency change is documented afterward.

### DynamoDB

For DynamoDB tables:

* Define partition key and sort key intentionally.
* Document access patterns.
* Use TTL where lifecycle cleanup is needed.
* Use autoscaling or on-demand based on workload profile.
* Monitor throttles and consumed capacity.
* Be careful with GSI design.
* Do not add indexes without explaining query patterns.

---

## Docker Rules

* Use minimal base images where practical.
* Pin base image versions.
* Avoid running containers as root unless required.
* Do not bake secrets into images.
* Use multi-stage builds when helpful.
* Keep image size reasonable.
* Add health checks when appropriate.
* Tag images immutably.
* Prefer commit SHA or release version tags over `latest`.

---

## Python Rules

Python is preferred for AWS automation, operational tooling, Lambda utilities, and scripts with non-trivial logic.

Rules:

* Use clear function boundaries.
* Use type hints for public functions.
* Use structured logging.
* Handle boto3/API timeouts intentionally.
* Avoid broad `except Exception` without logging and re-raising or clear handling.
* Keep scripts idempotent where possible.
* Use environment variables for runtime config, but not for hardcoded secrets.
* Use `argparse` for CLI scripts.
* Include `requirements.txt`, `pyproject.toml`, or equivalent dependency definition.
* Include basic usage examples in README or script header.

---

## Bash Rules

Bash is acceptable for simple automation only.

Use Bash for:

* Small wrappers
* CI/CD glue
* Local helper commands
* Simple operational checks

Avoid Bash for:

* Complex business logic
* Large AWS workflows
* JSON-heavy transformations
* Long scripts with many branches

Bash scripts should:

* Use `set -euo pipefail`
* Quote variables
* Validate required inputs
* Fail clearly
* Avoid printing secrets

---

## Documentation Rules

Every significant change should include documentation updates.

Required docs when applicable:

* README
* Usage examples
* Inputs and outputs
* Architecture notes
* Runbook
* Troubleshooting
* Rollback steps
* Operational ownership

For Terraform modules, README should include:

* Purpose
* Example usage
* Inputs
* Outputs
* Required providers
* Assumptions
* Security notes
* Observability notes

For production services, runbook should include:

* How to verify health
* Common alerts
* Common failure modes
* How to restart or redeploy
* How to roll back
* Where logs are located
* Where dashboards are located

---

## Code Review Rules

When reviewing code, check for:

* Security risks
* Missing observability
* Missing rollback path
* Missing tests
* Unsafe defaults
* Overly broad IAM
* Hardcoded environment values
* Missing documentation
* Naming inconsistency
* Terraform drift risk
* Production impact
* Cost impact

Do not approve infrastructure changes that are functional but operationally blind.

---

## Definition of Done

A story is done only when the following are true:

* Implementation matches the story requirements.
* Terraform or code is formatted.
* Terraform validates successfully where applicable.
* Tests are added or the reason for no tests is documented.
* Security implications are reviewed.
* IAM permissions are scoped.
* Secrets are handled safely.
* Logs are configured.
* Metrics and alarms are added for production-relevant components.
* Rollback path is documented.
* README or runbook is updated.
* PR notes explain impact and risk.
* No unrelated refactoring is included.
* No secrets or generated state files are committed.

---

## Anti-Patterns to Avoid

Avoid:

* Hardcoded AWS account IDs
* Hardcoded regions
* Hardcoded ARNs
* Long-lived AWS access keys
* Broad IAM permissions
* Public S3 buckets
* Unencrypted storage
* Unmonitored production services
* Deploying Docker image tag `latest`
* Infrastructure changes outside Terraform
* Giant Terraform modules
* Hidden manual deployment steps
* CI/CD pipelines without rollback strategy
* Logs without retention policy
* Alarms without actionable meaning
* Documentation that describes only the happy path
* Rewriting working systems without a migration plan

---

## Preferred Response Style for AI Agents

When implementing or planning, agents should respond with:

1. Summary of intended change
2. Files likely to change
3. Assumptions
4. Risks
5. Implementation steps
6. Validation steps
7. Rollback notes
8. Documentation updates

For code review, agents should group findings by severity:

* Critical
* High
* Medium
* Low
* Suggestions

For architecture, agents should include:

* Recommended design
* Alternatives considered
* Trade-offs
* Security implications
* Operational implications
* Cost considerations
* Failure modes
* Observability plan
* Rollback/migration path

---

## Default Bias

When there are multiple valid options, choose the one that is:

1. Easier to operate
2. Easier to debug
3. More secure by default
4. More observable
5. Easier to roll back
6. Less surprising to future engineers

Production systems should be boring, reliable, and well-documented.

