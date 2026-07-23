# ECS Scheduled Job Module

This module owns one application's scheduled-job declaration and the three
job-owned IAM roles introduced by Story 2.2: launch, ECS execution, and
application task. Story 2.3 adds fail-closed private-network validation and may
create one job-owned security group with explicit bounded egress. It validates
the Story 2.1 reservation and Cell Contract but does not create task
definitions, schedules, routes, NAT gateways, endpoints, subnets, shared
security groups, logs, alarms, CONFIG, or Cell ownership.
It creates no resources for routes, NAT gateways, endpoints, subnets, or shared
security groups.

## Required Providers

- Terraform `>= 1.10, < 2.0`
- AWS provider `>= 6.0, < 7.0`

The dated validation seed is Terraform 1.15.8 with AWS provider 6.54.0. The
constraints remain major-bounded so validation can qualify later compatible
patch releases.

## Example

See [`examples/basic`](examples/basic). It proves declaration, IAM wiring, and
the private-network evidence shape with synthetic IDs; it does not contain
credentials or secret values. A real plan must use trusted AWS evidence for
the declared VPC, subnets, and existing security groups.

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
attachments, and protected tags. Networking requires a declared VPC, explicit
subnets, a versioned network policy, private-subnet evidence, existing or
created security-group mode, bounded created-group egress, and secret-free
dependency reachability for ECR, S3, CloudWatch Logs, and selected secret
providers. Outputs expose the canonical job ID, validated Cell metadata,
Registrar-confirmed reservation, protected tags, normalized schedule identity,
role ARNs/IDs, and non-sensitive network handoff metadata.

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
schedule, CONFIG, or Cell-owned resource is created here. Network validation
does not repair non-compliant shared groups or infer private status from names;
unknown evidence blocks planning. Created groups have no ingress, no implicit
default egress, and only explicitly bounded security-group, prefix-list, or
CIDR egress. Later stories own task definition, logs, schedule, and CONFIG.
Customer-managed policy attachments must be same-account,
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
Rollback restores the prior network policy version, declaration, and evidence,
keeps task generation disabled until revalidation, and preserves all three
roles while future task definitions or CONFIG reference them. Do not delete or
mutate shared subnets, routes, gateways, endpoints, or security groups, and do
not enable a schedule as part of rollback. A job-created security group uses
`prevent_destroy`; migrate references in a separate apply before explicit
retirement, then remove it only after the task is quiesced and the replacement
group is verified.

## Validation

Run `terraform fmt -check`, backend-free Terraform init/validate for this
module and `examples/basic`, Ruff, strict mypy, contract/runtime tests,
IAM positive/negative/effective-policy tests, Checkov, repository hygiene,
network-policy positive/negative tests, and `git diff --check`. These are
credential-free checks and do not claim live IAM or route/endpoint enforcement;
trusted AWS qualification is separate. Do not use real credentials or secret
values in examples.
