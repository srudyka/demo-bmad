# ECS Scheduled Job Module

This module owns one application's scheduled-job declaration and the three
job-owned IAM roles introduced by Story 2.2: launch, ECS execution, and
application task. Story 2.3 adds fail-closed private-network validation and may
create one job-owned security group with explicit bounded egress. Story 2.4
adds one immutable Fargate task-definition family revision and one encrypted,
retained job log group. Story 2.5 adds one disabled Scheduler schedule,
Scheduler delivery role, and encrypted content-addressed CONFIG publication.
It validates the Story 2.1 reservation and Cell Contract but does not create
routes, NAT gateways, endpoints, subnets, shared security groups, alarms, or
Cell ownership.
It creates no resources for routes, NAT gateways, endpoints, subnets, shared
security groups, or Cell runtime state.

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
attachments, protected tags, immutable image/deployment identity, Fargate
platform/storage settings, command/entrypoint, non-secret configuration, and
log retention. Networking requires a declared VPC, explicit subnets, a
versioned network policy, private-subnet evidence, existing or created
security-group mode, bounded created-group egress, and secret-free dependency
reachability for ECR, S3, CloudWatch Logs, and selected secret providers.
Outputs expose the canonical job ID, validated Cell metadata,
Registrar-confirmed reservation, protected tags, normalized schedule identity,
role ARNs/IDs, task-definition and log-group identity, Deployment Identity,
and non-sensitive network handoff metadata.

Phase one also publishes one disabled EventBridge Scheduler schedule and a
separate Scheduler delivery role targeting the Cell Contract's scheduler
ingress queue and DLQ. It writes one encrypted, content-addressed CONFIG
candidate at `jobs/<job_id>/config/<config_version>.json`, where the lowercase
SHA-256 version is calculated from the exact canonical secret-free document.
The publisher validates the same CONFIG JSON Schema before hashing. Terraform
also rejects JSON escape sequences that would make its `jsonencode` bytes differ
from the publisher's RFC 8785 bytes, so the content hash is computed by one
explicitly compatible canonicalization profile at both boundaries.
CONFIG is published through the dedicated `demo-bmad/cell` provider, which
SigV4-authenticates the Cell publisher API as the caller's IAM role. The Cell
service requires the caller role's exact `PlatformEcsScheduledJobId` tag and
performs the atomic `If-None-Match: *` write. Configure the provider endpoint
from the Cell Contract and grant the caller only this job's create-only policy.
The content-addressed key and create-only provider resource prevent Terraform
replacement. If a deployment must retire
a schedule, first disable and drain it, publish a successor version, and only
then perform an explicitly approved state migration because the schedule and
CONFIG resources use `prevent_destroy`.
The `phase_one` output reports `PUBLISHED` and `launch_authorized = false`.
When phase-two activation is requested, the Cell validator provider requires an
authoritative `MATERIALIZED` snapshot before Terraform can enable Scheduler.

Phase two is opt-in through the `activation` object. Its default keeps the
existing schedule `DISABLED`; setting `activation.enabled = true` requires an
exact non-production `MATERIALIZED` Cell acknowledgement, `PASS` conformance,
matching config/schedule/role/task/owner identity, and at least 24 hours of
expected horizon. The module still targets the Cell scheduler ingress queue;
it never adds a direct Scheduler-to-ECS target. Disablement retains task,
CONFIG, registry, occurrence, log, alarm, and ownership evidence. Production
activation remains blocked until the governed delivery and readiness stories
provide their controls. Platform alarms cover validator errors, throttles,
rejections, conflicts, scheduler queue age/depth, and queue DLQs; operators
must disable launch first, retain evidence, restore a compatible generation,
and repeat validation before rollback.

The `task_definition` and `deployment_identity` outputs are the authoritative
handoff for the later launch/CONFIG story. They include the approved
`platform_version`; the later launch operation must pass that exact value to
ECS and must not substitute `LATEST` for a pinned version.

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

The task definition uses Fargate `awsvpc`, the exact Story 2.2 roles, immutable
image digests, and `awslogs` to the exact encrypted job log group. Secret
references use ECS's locator-only `secrets` contract and never ordinary
environment values. No metric or alarm is created here. Network validation
does not repair non-compliant shared groups
or infer private status from names;
unknown evidence blocks planning. Created groups have no ingress, no implicit
default egress, and only explicitly bounded security-group, prefix-list, or
CIDR egress. Later stories own Cell acknowledgement and schedule activation.
Customer-managed policy attachments must be same-account,
allowlisted, version-governed, and boundary-compatible; production exceptions
remain owned by Story 3.4.

Structured start, success, and failure records are documented evidence for the
later Job Completion Contract. Every record asserts the job, Occurrence ID,
CONFIG version, attempt, timestamp, status, and sanitized error reason; an
isolated success marker or zero exit is not authoritative completion. Denied
AssumeRole, PassRole, secret retrieval, and task execution signals are
operational handoffs for later stories; this module creates no alarms or
dashboards.

Secret delivery is mode-specific: `ecs-agent` uses ECS `secrets` locator
entries, while `application-pull` exposes only `SECRET_MODE`, the JSON list of
non-sensitive `SECRET_REFERENCE_LOCATORS`, and `SECRET_NETWORK_PATH`; it never
renders ECS-agent secret injection for application-pull.

Scheduler delivery uses bounded retry/max-age settings, an explicit IANA time
zone, a future UTC activation anchor, flexible window `OFF`, and a literal
`<aws.scheduler.scheduled-time>` field for later Cell normalization. The
schedule never targets ECS directly and remains disabled during phase one.

The completion contract uses these secret-free shapes:

```json
{"event":"start","job_id":"dev/sample/daily","occurrence_id":"occ-123","config_version":"cfg-7","attempt_no":1,"timestamp":"2026-07-24T12:00:00Z","status":"started"}
```

```json
{"event":"success","job_id":"dev/sample/daily","occurrence_id":"occ-123","config_version":"cfg-7","attempt_no":1,"timestamp":"2026-07-24T12:02:00Z","status":"succeeded","exit_code":0}
```

```json
{"event":"failure","job_id":"dev/sample/daily","occurrence_id":"occ-123","config_version":"cfg-7","attempt_no":1,"timestamp":"2026-07-24T12:02:00Z","status":"failed","exit_code":1,"error_reason":"dependency_unavailable"}
```

Every record requires `job_id`, `occurrence_id`, `config_version`,
`attempt_no`, an RFC 3339 UTC `timestamp`, and `status`; failure records use a
sanitized bounded `error_reason`. A zero exit code or isolated success marker
is not authoritative completion.

The reserved runtime fields `JOB_ID`, `OCCURRENCE_ID`, `CONFIG_VERSION`,
`ATTEMPT_NO`/`attempt_no`, and `TASK_ARN` cannot be overridden by consumer environment
configuration. `DEPLOYMENT_IDENTITY` is bounded, non-secret metadata.

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
not enable a schedule as part of rollback. Task-definition revisions remain
available while referenced by CONFIG, occurrences, investigations, or rollback
windows, and the log group preserves history with `skip_destroy`. A job-created
security group uses
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
