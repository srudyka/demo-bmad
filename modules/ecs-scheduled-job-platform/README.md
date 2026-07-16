# ECS Scheduled Job Platform Cell Module

This module creates the first account/Region-local Platform Cell foundation and
the narrow, platform-owned canary bootstrap prerequisites:

- a namespace registry for future job reservation authority;
- an encrypted CONFIG candidate inbox; and
- a separate encrypted CONFIG registry plus its SSM discovery contract;
- one best-effort declarative canary reservation and CONFIG-publisher principal;
- a stable Cell-major Process Manager role shell; and
- an encrypted Scheduler source queue, DLQ, and schedule group.

It deliberately does not create a general Registrar, Lambda functions, a
runtime ledger, ECS resources, job schedules, alarms, notification targets, or
runtime consumers. The Cell queues are delivery boundaries only, and the
Process Manager role has no launch authority. Those runtime capabilities are
owned by later stories.

## Required Providers

- Terraform `>= 1.10, < 2.0`
- AWS provider `>= 6.0, < 7.0`

The dated validation seed is Terraform 1.15.8 with AWS provider 6.54.0.

## Example

See [`examples/basic`](examples/basic). Its KMS ARN is an unmistakably
fictitious structural value for `terraform validate`; a consuming root must
supply an approved customer-managed KMS key ARN and environment-specific
non-secret values.

## Ownership And Assumptions

Platform Engineering owns this module, its state, the namespace registry, the
CONFIG inbox/registry, and the Cell Contract. A job root reads the SSM contract
at:

```text
/platform/ecs-scheduled-jobs/<environment>/<region>/contract
```

It must not use `terraform_remote_state` or mutate Cell resources. Later, an
authorized job root publishes a secret-free CONFIG candidate only at:

```text
jobs/<job_id>/config/<config_version>.json
```

The Cell Contract is an RFC 8785/JCS semantic contract. Its `checksum` is the
lowercase SHA-256 of the full contract with `checksum` omitted. The module
restricts contract values to ASCII strings/maps so Terraform's `jsonencode`
has the checked-in JCS-equivalent profile. Consumers validate its JSON Schema,
Cell identity, supported ranges, and checksum before using published ARNs.

## Inputs And Outputs

Required inputs:

- `environment`, `application`, `service`, `owner`, and `cell_id` define the
  Cell identity and protected tags.
- `kms_key_arn` is an approved customer-managed KMS key used by S3, DynamoDB,
  and the SecureString discovery parameter.
- `access_log_bucket_name` is an existing private bucket approved to receive
  CONFIG inbox access logs.
- `metric_namespace` reserves the bounded namespace for later Cell metrics.
- `permissions_boundary_arn` is applied to the Process Manager shell and the
  Cell-owned canary CONFIG publisher role.
- `canary_reservation` is the one platform-controlled, declarative non-production
  bootstrap binding. It supplies the repository/root/apply identity, account,
  Region, owner, generation, and canonical job identity; it is not a public
  general-registration interface.
- `enable_recovery_protection` explicitly enables PITR and deletion protection;
  it is required for `prod`.
- `incomplete_multipart_upload_days` is a bounded 1-365 day cleanup policy for
  incomplete uploads only. CONFIG object versions are retained until a later,
  registry-aware garbage collector proves them unreferenced.

Optional inputs are `contract_version`, `incomplete_multipart_upload_days`, and
non-secret `tags`. Module tags always override consumer collisions for
`Environment`, `Application`, `Service`, `Owner`, and `ManagedBy=Terraform`;
use `CostCenter` and `Repository` when applicable.

Outputs provide Cell identity; table, bucket, queue, schedule group, role, and
parameter identifiers; metric namespace; the bootstrap publisher role; and the
Cell Contract version/checksum. They contain no secret values or Terraform
state.

## Canary Bootstrap Exception

The one canary reservation is declared only by the Cell root. Its authorization
and reservation items use the same `pk`/`sk` shapes as the future Registrar;
Cell identity preconditions, `prevent_destroy`, and a replacement trigger block
ordinary Terraform replacement. This is a best-effort declaration, not an
atomic conditional registration API; the canary fixture never writes the
namespace table.

The Process Manager role uses a stable Cell-major name/path and a supplied
permissions boundary. It is trusted only by `lambda.amazonaws.com` and has no
inline or attached authority in this phase, specifically no `ecs:RunTask`,
`iam:PassRole`, registry, queue-consumption, Lambda, or self-modification
permission. Creating this shell now prevents a later principal replacement
from invalidating canary launch-role trust.

The standard SQS source and DLQ use the Cell KMS key, 14-day retention, and a
redrive count of five. Queue policies allow `scheduler.amazonaws.com` to send
only from the exact Cell account and schedule group. They do not create a
normalizer, canonical ingress, processor, ledger, alert, ECS-event, or log
queue.

AWS provider 6.54.0 cannot add `If-None-Match: *` to `aws_s3_object`. The S3
policy retains that precondition for all ordinary writers and exempts only the
Cell-created canary publisher role. Its trust is the exact registered apply
role, its principal tags bind the job ID, and its policy is limited to the one
canary CONFIG prefix and configured KMS key. This is best-effort
content-addressed publication, not an immutable S3 write; a conditional
publisher is required before that guarantee is claimed.

## Namespace Reservation Contract

The namespace registry uses `pk` and `sk` string keys. The future Registrar
stores these immutable item shapes:

- namespace authorization: `PK=NAMESPACE#<environment>#<application>`,
  `SK=AUTHORIZATION`; it contains `repository_id`, `terraform_root_id`,
  `apply_role_id`, `account_id`, `region`, and approval evidence;
- job reservation: `PK=JOB#<job_id>`, `SK=RESERVATION`; it contains the
  namespace key, the same immutable identity fields, `owner`,
  `owner_generation`, `transfer_state`, transfer approval evidence, and
  `tombstoned`.

The Registrar is not part of this module. Its transaction must first make a
`ConditionCheck` with this DynamoDB `ConditionExpression` against the namespace
item:

```text
attribute_exists(pk) AND repository_id = :repository_id AND
terraform_root_id = :terraform_root_id AND apply_role_id = :apply_role_id AND
account_id = :account_id AND region = :region
```

It then creates the reservation with
`attribute_not_exists(pk) AND attribute_not_exists(sk)`. The first check maps a
foreign namespace to `NAMESPACE_CROSS_NAMESPACE_CLAIM` or an unapproved actor
to `NAMESPACE_UNAUTHORIZED_MUTATION`; the second maps to
`NAMESPACE_DUPLICATE_RESERVATION` unless an identical existing reservation is
confirmed as an idempotent retry. Owner updates require:

```text
owner_generation = :expected_owner_generation AND
apply_role_id = :actor_apply_role_id AND tombstoned = :false
```

Failure maps to `NAMESPACE_STALE_OWNER_GENERATION`,
`NAMESPACE_UNAUTHORIZED_MUTATION`, or `NAMESPACE_TOMBSTONED_JOB_ID` after the
Registrar reads the conflicting immutable item. A transfer additionally
requires `transfer_state = :quiescent`, distinct approval evidence, and writes
`owner_generation = :next_owner_generation`; any failed transfer condition is
reported as `NAMESPACE_TRANSFER_CONDITION_FAILED`. Tombstoned IDs are never
automatically reusable.

The stable conditional failure codes are:

- `NAMESPACE_DUPLICATE_RESERVATION`
- `NAMESPACE_CROSS_NAMESPACE_CLAIM`
- `NAMESPACE_STALE_OWNER_GENERATION`
- `NAMESPACE_UNAUTHORIZED_MUTATION`
- `NAMESPACE_TOMBSTONED_JOB_ID`
- `NAMESPACE_TRANSFER_CONDITION_FAILED`

No application, job, or consumer-workflow principal is created or granted
registry mutation access by this foundation.

The separate configuration registry also uses `pk` and `sk`, with immutable
lookup keys `PK=JOB#<job_id>` and `SK=CONFIG#<config_version>`. It has no TTL
because a referenced CONFIG must outlive validation, replay, investigation, and
rollback windows.

## Security And Observability

Both DynamoDB registries use the supplied KMS key, on-demand billing, and
always-enabled PITR. With `enable_recovery_protection`, they also use deletion
protection. The CONFIG inbox has KMS SSE, bucket keys, versioning,
BucketOwnerEnforced ownership, all public-access blocks, `force_destroy =
false`, access logging to the supplied existing bucket, and an explicit
multipart-upload cleanup rule. Aside from the Cell-owned Scheduler delivery
boundary described above, it creates no EventBridge integration or runtime
consumer.

The bucket policy contains scoped wildcard-principal **deny** statements only:
they require TLS, SSE-KMS with the configured key, canonical CONFIG keys, and a
Registrar-issued `PlatformEcsScheduledJobId` principal tag that matches the job
prefix for object reads, writes, and deletes. General CONFIG versions are
64-character content hashes and publication must use `If-None-Match: *`, which
prevents overwriting a current version. The documented canary publisher is the
only temporary exception because provider 6.54.0 cannot emit that header. The
bucket has no broad allow statement. The later Registrar supplies the
prefix-scoped IAM allow after it verifies ownership; an S3 policy cannot query
DynamoDB dynamically.

CONFIG objects and all their versions are intentionally not expired here. S3
cannot determine whether a candidate is still referenced by validation, replay,
investigation, or rollback. Registry-aware garbage collection is a later Cell
capability.

The Cell Contract uses the SSM Standard tier. Its generated ASCII JSON value is
checked at plan time against the Standard tier's 4 KiB limit; contract growth
beyond that limit requires a reviewed tier/interface change.

This foundation has no runtime behavior to monitor yet. It reserves the metric
namespace and publishes discovery state; later stories add actionable Cell and
job alarms with their producing components.

## Validation

Run the repository gate without AWS credentials:

```bash
./scripts/validate.sh
```

It runs formatting, backend-free locked Terraform initialization/validation for
every module and example, Python tests, Checkov, and repository hygiene. The
Cell Contract tests prove schema, checksum, SSM path, ownership-catalog shape,
and the absence of premature runtime resources.

## Rollback And Recovery

For a failed foundation change, restore the prior compatible module and Cell
Contract after validating that prior contract locally. Retain the S3 bucket,
object versions, namespace registry, and CONFIG registry; routine rollback is
not `terraform destroy` or data cleanup.

DynamoDB PITR restores to a new table. A recovery runbook must validate the
restored data and reapply tags, KMS configuration, PITR, deletion protection,
and policies before a controlled Cell Contract cutover. Do not publish a
contract that points consumers to an unvalidated restore.
