# Platform Canary Fixture

This backend-free root is the single platform-owned, disposable
non-production acceptance fixture for the first Cell. It creates a Fargate task
definition, three job roles, bounded KMS-encrypted logs, a disabled EventBridge
Scheduler schedule that targets the Cell Scheduler queue, one secret-free
`PUBLISHED` CONFIG candidate, and an encrypted SQS notification-evidence sink.

It does not create a Cell, mutate Cell resources, write either DynamoDB
registry, consume a queue, create an occurrence, or launch an ECS task. The
public `modules/ecs-scheduled-job` module remains resource-free until Epic 2.

## Required Inputs

Every account, Region, Cell identifier, repository/root/apply identity, owner,
job ID, ownership generation, ECS cluster, private subnet, security group,
image digest, KMS key, boundary, scheduler queue/group, and notification
metadata is explicit. There are no provider credentials, account defaults, or
state/backend configuration in this root.

The Cell root supplies the Scheduler queue/group, Process Manager role, CONFIG
inbox, KMS key, and narrowly scoped `cell_config_publisher_role_arn` through
reviewed environment inputs. Do not use `terraform_remote_state`. The CI apply
role must exactly match the role bound in the Cell canary reservation and can
only assume the publisher role for this one canary prefix.

Use an immutable image in the form:

```text
<repository>@sha256:<64 lowercase hexadecimal characters>
```

Private subnets need NAT or approved VPC endpoints for ECR, CloudWatch Logs,
Secrets Manager/SSM when later introduced, and workload dependencies. The task
definition always uses `awsvpc`; runtime configuration records
`assign_public_ip = DISABLED`.

## Bootstrap Reservation And CONFIG Publication

AWS provider 6.54.0 does not expose `If-None-Match` on `aws_s3_object`, and it
does not expose DynamoDB conditional expressions on
`aws_dynamodb_table_item`. The Cell therefore owns a one-canary bootstrap
declaration rather than granting this root direct registry access. The Cell
declaration uses the standard namespace and job keys, validates repository/root,
apply identity, account, Region, environment, owner, and generation, and uses
`prevent_destroy` plus replacement triggers to block ordinary Terraform
replacement. It is a best-effort declaration, not an atomic registration API;
a general transactional Registrar remains a later capability.

The Cell bucket retains `If-None-Match: *` for every general CONFIG writer.
Its only exception is the Cell-created, tag-bound canary publisher role, which
is limited to `jobs/<job_id>/config/*`; the fixture assumes that role solely to
write the canonical content-addressed object. This is a best-effort provider
compatibility exception, not a general allow or an imperative provisioner: it
does not provide S3 conditional-write immutability. The CONFIG key is the
RFC 8785-compatible SHA-256 of its secret-free body and the Terraform object
has `prevent_destroy`.

The CONFIG body includes the task revision, cluster, disabled private network,
role ARNs, Scheduler generation, completion window, log group, test topic, and
Deployment Identity. It remains `PUBLISHED`; it never writes a configuration
registry, ledger, acknowledgement, materialization, completion, or enabled
state.

## Disabled Schedule And Test Sink

The schedule is permanently declared `DISABLED` in this phase, uses flexible
window `OFF`, an explicit IANA time zone and future activation anchor, bounded
retry/age, the Cell DLQ, and a payload containing the literal Scheduler
scheduled-time context. Its target is the Cell Scheduler source queue, never
ECS. The encrypted test SQS queue retains delivery evidence for 14 days and
does not contact production on-call or customer integrations.

No successful completion, occurrence, task launch, or Scheduler delivery is
claimed until disposable-account evidence exists in later stories. Application
code must eventually emit `JOB_COMPLETED_SUCCESSFULLY` with occurrence-aware
metadata; that marker is configured only as a secret-free task environment
contract here.

## Validation

Run the credential-free repository gate:

```bash
./scripts/validate.sh
```

The fixture lock includes Darwin ARM and Linux AMD64 AWS provider hashes. A
real plan/apply is only permitted in an approved disposable non-production
account with the exact inputs and CI OIDC identity described above.

## Rollback And Teardown

Keep the schedule disabled. Rollback restores a compatible fixture definition
and preserves the Cell-owned reservation, CONFIG bucket/object versions, Cell
queues, and investigation evidence. Do not run routine `terraform destroy` for
the Cell or CONFIG candidate: the bootstrap declaration and object use
`prevent_destroy` deliberately. Safe cleanup requires a separately reviewed
incident or pilot-retirement procedure after evidence-retention obligations are
met.
