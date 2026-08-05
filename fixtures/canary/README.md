# Platform Canary Fixture

This backend-free root is the single platform-owned, disposable
non-production acceptance fixture for the first Cell. It creates a Fargate task
definition, three job roles, bounded KMS-encrypted logs, and an EventBridge
Scheduler schedule that targets the Cell Scheduler queue. The schedule is
disabled by default and can only be enabled with an exact Cell acknowledgement;
one secret-free
`PUBLISHED` CONFIG candidate, and an encrypted SQS notification-evidence sink.

It does not create a Cell, mutate Cell resources, write either DynamoDB
registry, or directly launch an ECS task. The Cell Process Manager can consume its
materialized canonical ingress and launch exactly one task per eligible occurrence
through the assumed launch role after acknowledgement. The
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
role ARNs, immutable Scheduler delivery role ID, exact schedule ARN, Scheduler
generation, completion window, log group, test topic, and
Deployment Identity. It remains `PUBLISHED`; it never writes a configuration
registry, ledger, acknowledgement, materialization, completion, or enabled
state.

## Disabled Schedule And Test Sink

The schedule is declared `DISABLED` unless `enable_schedule=true` and the
acknowledgement exactly matches CONFIG hash, schedule ARN, Scheduler role ID,
owner generation, activation anchor, `MATERIALIZED` state, and a sufficient
horizon. It uses flexible window `OFF`, an explicit IANA time zone and future activation anchor, bounded
retry/age, the Cell DLQ, and a body containing identity assertions plus literal
Scheduler scheduled-time context. Its target is the Cell Scheduler source
queue, never ECS. Scheduler provides the scheduled timestamp but cannot derive
the platform occurrence hash in its target template, so this body omits
`occurrence_id`; Story 1.5's Cell-owned normalizer derives it from the trusted
timestamp and rejects any supplied mismatching assertion. The body is otherwise
untrusted and is accepted only when the source queue, account/Region, exact
schedule/group, generation, CONFIG version, and immutable Scheduler role ID
match its explicit registration. The fixture output exposes the delivery role
ID, schedule ARN, and generation as reviewed wiring evidence, not remote state.

No successful completion is claimed until disposable-account evidence exists in
later stories. Launch evidence is durable in attempt zero; application
code must eventually emit `JOB_COMPLETED_SUCCESSFULLY` with occurrence-aware
metadata; that marker is configured only as a secret-free task environment
contract here.

## Materializer Boundary

The Cell materializer, not this fixture, independently evaluates the disabled
canary CONFIG on a UTC minute tick. It authenticates its evidence through a
dedicated source queue and only materializes expectations after the CONFIG hash,
Cell identity, namespace ownership, exact Scheduler ARN, and immutable delivery
role ID agree with Cell registration. Local tests prove contract behavior only;
they do not establish live EventBridge delivery, queue processing, occurrence
state, ECS launch, or alarm delivery.

## Validation

Run the credential-free repository gate:

```bash
./scripts/validate.sh
```

The fixture lock includes Darwin ARM and Linux AMD64 AWS provider hashes. A
real plan/apply is only permitted in an approved disposable non-production
account with the exact inputs and CI OIDC identity described above.

## Rollback And Teardown

Keep the schedule disabled. If normalizer investigation is needed, disable its
event-source mapping and the materializer EventBridge rule before changing the fixture and retain source, canonical
ingress, quarantine, and DLQ evidence for 14 days. Rollback restores a
compatible fixture/Cell Contract/runtime version; it does not replay arbitrary
quarantine bodies or delete retained evidence. Do not run routine `terraform
destroy` for the Cell or CONFIG candidate: the bootstrap declaration and object
use `prevent_destroy` deliberately. Safe cleanup requires a separately reviewed
incident or pilot-retirement procedure after evidence-retention obligations are
met.
