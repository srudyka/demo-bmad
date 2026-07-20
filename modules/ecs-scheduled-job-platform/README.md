# ECS Scheduled Job Platform Cell Module

This module creates the first account/Region-local Platform Cell foundation and
the narrow, platform-owned canary bootstrap prerequisites:

- a namespace registry for future job reservation authority;
- an encrypted CONFIG candidate inbox; and
- a separate encrypted CONFIG registry plus its SSM discovery contract;
- one best-effort declarative canary reservation and CONFIG-publisher principal;
- a stable Cell-major Process Manager role shell; and
- an encrypted Scheduler source queue, DLQ, and schedule group; and
- a Cell-owned Evidence Normalizer with canonical ingress and sanitized quarantine queues.

It deliberately does not create a general Registrar, runtime ledger, ECS
resources, job schedules, alarms, notification targets, or later runtime
consumers. The Process Manager role has no launch authority. Those runtime
capabilities remain owned by later stories.

The module makes no runtime behavior claim for those deferred components.

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
- `canary_normalizer_registration` is the exact, platform-controlled Scheduler
  identity binding for that canary: source queue, schedule/group ARNs, immutable
  Scheduler role ID, account/Region, job/generation, and CONFIG version.
- `normalizer` supplies an externally built immutable Lambda artifact path and
  base64 SHA-256 plus bounded timeout, concurrency, batch, redrive, and log
  retention controls. Terraform never packages source from the checkout. The
  trusted artifact must include the `evidence_normalizer` source, the shared
  `tests.contract.support.contracts` package until it is promoted to a runtime
  package, `contracts/v1` at `/var/task/contracts/v1`, and its pinned Python
  dependencies (`boto3`, `botocore`, `jsonschema`, `referencing`, `rfc8785`,
  `semantic-version`, and `tzdata`).
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

The standard Scheduler source queue and DLQ use the Cell KMS key, 14-day
retention, and a redrive count of five. Queue policies allow
`scheduler.amazonaws.com` to send only from the exact Cell account and schedule
group. The Evidence Normalizer is the sole source consumer in this phase. It
uses a dedicated Lambda-only role, reads only that queue, writes only canonical
evidence ingress and sanitized quarantine, logs to its explicit-retention group,
and publishes bounded Cell metrics. It has no VPC attachment, function URL,
ledger, ECS, STS, or role-pass authority. The canonical ingress and quarantine
each have a separate KMS-encrypted 14-day DLQ; later producer queues are not
created here.

The normalizer log group is KMS-encrypted and retains logs for at least one
year. The Cell's Checkov scan narrowly documents the intentional no-VPC,
source-queue-DLQ, no-X-Ray, and artifact-hash-instead-of-code-signing decisions;
they are not general exemptions for other Lambda functions.

The normalizer compares every available body identity claim to the explicit
registration. EventBridge Scheduler can supply its occurrence timestamp but
cannot calculate the platform occurrence hash in a target template, so the
normalizer derives the occurrence ID from that trusted timestamp; a supplied
`occurrence_id` remains an assertion and must match. It derives authority from
SQS source ARN, Region, Scheduler role ID, and Cell registration. Permanent
invalid input is acknowledged after a secret-free quarantine record, structured
machine-code log, and bounded metric; only queue/metric transport errors are
retried via `ReportBatchItemFailures`. The KMS key policy must permit the AWS
SQS, Lambda, and CloudWatch Logs service use for this account/Region and must
allow the normalizer execution role `kms:Decrypt` and `kms:GenerateDataKey` for
the Cell's source, canonical-ingress, and quarantine queue encryption contexts.
The module grants only those scoped actions; it does not add broad KMS IAM
authority.

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

The normalizer emits structured secret-free records and a bounded rejection
counter (`job_id`, `environment`, `state`). The independent occurrence
materializer runs from a UTC EventBridge minute tick, reads only the registered
immutable CONFIG object, materializes at least 24 hours of
`occurrence.expected.v1` evidence, and conditionally persists a CONFIG
snapshot. Its dedicated source queue is authenticated separately by the
normalizer. It has no ECS, Scheduler create/update, or occurrence-ledger
permission. It does not create alert routing; later stories connect the metric
to the approved production incident path.

### Materializer Artifact And KMS Prerequisites

`materializer.artifact_path` and `materializer.artifact_source_hash` refer to
an externally built immutable deployment artifact. Its package must include the
`occurrence_materializer` runtime source, imported shared contract helpers,
`contracts/v1` at `/var/task/contracts/v1`, and pinned dependencies. Terraform
only consumes the artifact; it must never build a checkout ZIP or retain build
output, state, plans, credentials, or `.terraform/` files.

The supplied Cell KMS key policy must allow the materializer role to decrypt
the exact CONFIG object through S3 with the bucket encryption context, and
allow the SQS/Lambda/CloudWatch Logs service integrations required for the
exact Cell queues and log group. Keep those grants tied to the Cell key, Region,
role, `kms:ViaService`, and queue or bucket encryption context. Do not replace
them with account-wide KMS, S3, DynamoDB, SQS, or IAM permissions.

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

Story 1.7 adds the encrypted occurrence ledger and the Process Manager mapping.
The Process Manager accepts only authenticated materializer `occurrence.expected.v1`
records, reads the exact verified CONFIG snapshot, and writes the processed-event
and occurrence records in one conditional transaction. It has no ECS, Scheduler,
CONFIG mutation, alert, task-attempt, or operator-command permissions. The ledger
uses the canonical `JOB#.../OCCURRENCE#...` and
`EVENT#occurrence-materializer/...` keys and has no secondary indexes in this phase.

For rollback, disable the Process Manager event-source mapping first, then restore a
compatible immutable artifact. Preserve the ledger and its PITR evidence; do not
delete or manually edit occurrence records while investigating duplicates or
conditional-write conflicts.

For a failed materializer or normalizer deployment, first disable the relevant
event-source mapping or the materializer EventBridge rule and keep the canary
schedule disabled. Retain source, canonical ingress, quarantine queues and
DLQs, mappings, snapshots, and logs for the full 14-day investigation window.
Revert only to a compatible Cell Contract and runtime artifact; routine rollback
is not `terraform destroy` or retained-evidence cleanup.

DynamoDB PITR restores to a new table. A recovery runbook must validate the
restored data and reapply tags, KMS configuration, PITR, deletion protection,
and policies before a controlled Cell Contract cutover. Do not publish a
contract that points consumers to an unvalidated restore.
