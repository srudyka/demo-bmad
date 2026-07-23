# ECS Scheduled Job Module

This module owns one application's scheduled-job declaration and the three
job-owned IAM roles introduced by Story 2.2: launch, ECS execution, and
application task. It validates the Story 2.1 reservation and Cell Contract but
does not create workload execution resources. It creates no resources for task
definitions, schedules, networking, logs, alarms, CONFIG, or Cell ownership.

## Required Providers

- Terraform `>= 1.10, < 2.0`
- AWS provider `>= 6.0, < 7.0`

The dated validation seed is Terraform 1.15.8 with AWS provider 6.54.0. The
constraints remain major-bounded so validation can qualify later compatible
patch releases.

## Example

See [`examples/basic`](examples/basic). It proves declaration and IAM wiring
with synthetic ARNs; it does not contact AWS or contain credentials or secret
values.

## Ownership And Assumptions

The job root owns the three per-job roles and their inline policies. The Cell
root owns the Process Manager, permissions boundary, shared queues/ledgers,
and Cell Contract. This module consumes a published Cell Contract from SSM
and never reads or changes the Cell root's Terraform state.

## Inputs And Outputs

Inputs cover identity, immutable repository ownership, Cell discovery, ECS
dependencies, the Cell permissions boundary and Process Manager role, the
approved ECR repository, secret mode/KMS metadata, schedule, runtime,
networking, notifications, configuration, permissions, governed policy
attachments, and protected tags. Outputs expose the canonical job ID,
validated Cell metadata, Registrar-confirmed reservation, protected tags,
normalized schedule identity, and role ARNs/IDs.

## Security And Observability

The launch role trusts only the exact Cell Process Manager role and can run the
canonical task family on the configured cluster while passing only this job's
execution and task roles to ECS. Execution can pull only from the approved ECR
repository, write only to this job's log-group scope, and read exact
ECS-agent secret references. Task permissions are explicit, statement-ID
preserving declarations. `ecr:GetAuthorizationToken` is isolated at
`Resource = "*"` because AWS requires that scope; it is the sole documented
service-required wildcard.

Execution and task trust policies use `ecs-tasks.amazonaws.com`, the target
account, and AWS's supported regional ECS source ARN pattern. ECS does not
support cluster-specific `aws:SourceArn` narrowing for this trust. Secret
references are locators only. `ecs-agent` mode places secret/KMS access on
execution; `application-pull` places it on task and requires secret-free
private network-path metadata for Story 2.3. No secret values are accepted or
exposed.

No task definition, network, secret injection, log group, metric, alarm,
schedule, CONFIG, or Cell-owned resource is created here. Later stories own
those controls. Customer-managed policy attachments must be same-account,
allowlisted, version-governed, and boundary-compatible; production exceptions
remain owned by Story 3.4.

Denied AssumeRole, PassRole, secret retrieval, and task execution signals are
operational handoffs for later stories; this module creates no alarms or
dashboards.

## Reservation and rollback

The reservation identity is `JOB#<environment>/<application>/<job>` and binds
immutable repository/root/apply identity, account, Region, Environment,
namespace, owner, and generation. An authoritative conditional Registrar must
perform the claim before its receipt is passed as `registrar_receipt`; a
missing, mismatched, or stale receipt fails planning. `RESERVED` does not
grant launch authority, and tombstoned IDs must not be reused automatically.
Rollback restores prior compatible inline policies and preserves all three
roles while future task definitions or CONFIG reference them. Do not delete
roles or enable a schedule as part of rollback.

## Validation

Run `terraform fmt -check`, backend-free Terraform init/validate for this
module and `examples/basic`, Ruff, strict mypy, contract/runtime tests,
IAM positive/negative/effective-policy tests, Checkov, repository hygiene,
and `git diff --check`. These are credential-free checks and do not claim live
IAM enforcement or deployed role qualification. Do not use real credentials or
secret values in examples.
