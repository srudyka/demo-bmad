# Operator Runbooks

This is the stable location for platform and job operator Runbooks. Story 1.3
introduces the Cell foundation recovery boundary: retain CONFIG and namespace
evidence during rollback, validate a restored DynamoDB table before a Cell
Contract cutover, and never use routine destructive cleanup as recovery.

Runtime, alarm, rerun, and incident procedures are introduced with the
capabilities they operate.

## Occurrence Materializer Investigation

The materializer is an independent UTC minute trigger, not the job scheduler.
It reads the registered immutable CONFIG version, produces only
`occurrence.expected.v1`, and sends it through the materializer source queue
for normalizer authentication. A `MATERIALIZER_CONFIG_*` or
`MATERIALIZER_SCHEDULE_INVALID` failure means the candidate was not eligible
for expectation generation; do not inspect or log its raw CONFIG body. Check
the materializer log group, the source queue/DLQ, and immutable configuration
snapshot watermark. Local validation proves neither live EventBridge delivery
nor an ECS launch, occurrence state, or alert.

For `MATERIALIZER_CONFIG_SCHEDULE_ARN_MISMATCH` or
`MATERIALIZER_CONFIG_SCHEDULER_ROLE_MISMATCH`, compare the Cell-controlled
registration with the immutable CONFIG's exact Scheduler ARN and role ID; do
not edit an existing CONFIG version. A valid snapshot progresses from
`VALIDATED` to `MATERIALIZED` only after source-queue sends complete. Query the
bounded materializer result metric by account, Region, environment, job, and
state; never add an occurrence ID, CONFIG hash, schedule ARN, role ID, or raw
error text as a metric dimension. A stalled `VALIDATED` snapshot or a horizon
near the configured 24-hour watermark requires investigation before later
enablement.

To contain a materializer fault, disable the exact EventBridge materializer
rule and its normalizer source mapping, keep the Scheduler canary disabled, and
retain CONFIG snapshots, queues, DLQs, and logs for at least 14 days. Revert
only to a compatible Cell Contract and runtime artifact. Do not delete evidence
or enable a Scheduler schedule as a recovery action.

## Process Manager Investigation

The Process Manager consumes only canonical ingress records authenticated as
materializer `occurrence.expected.v1` evidence. It strongly reads the immutable
CONFIG snapshot and atomically writes one processed-event record plus one
`EXPECTED` occurrence. Query the occurrence ledger for state, scheduled time,
deadline, CONFIG version, bounded evidence IDs, and last reduction time; raw
CONFIG and evidence are intentionally unavailable from this operational view.

Same-digest delivery is a no-op. A changed body with the same producer event ID
is a stable conflict and must not overwrite state. Deterministic contract
failures are record-local; only storage/transport failures appear in
`batchItemFailures`. For rollback, disable the Process Manager mapping first,
restore a compatible artifact, and preserve the encrypted ledger/PITR evidence.

## Canary Launch Investigation

The canary schedule remains disabled unless the reviewed acknowledgement matches
the exact CONFIG hash, schedule ARN, Scheduler delivery role ID, owner generation,
activation anchor, `MATERIALIZED` state, and horizon watermark. The Scheduler target
is always the Cell queue; it never calls ECS directly.

For an eligible `EXPECTED` occurrence, inspect the attempt-zero item at
`PK=JOB#<job_id>;SK=ATTEMPT#<occurrence_id>#0`. `PENDING` means the request is
reserved but not authoritatively mapped. `STARTED` includes the ECS task ARN;
`FAILED` means ECS returned a sanitized launch failure; `AMBIGUOUS` means the
system could not prove exactly one task. Use the exact cluster, `startedBy`, Cell
tags, and task definition revision for reconciliation. Never infer identity from
application output and never create an automatic attempt one.

If the Process Manager crashes after ECS accepts `RunTask`, retry with the same
client token and reconcile before any further launch. Zero matches may retry only
before the safe deadline. Multiple matches, token/parameter conflicts, or expiry
must stop `RunTask` and require a separately authorized synthetic rerun.

To roll back, disable the canary schedule and Process Manager event-source mapping,
preserve the encrypted ledger, task-ARN index, queues, and logs, and restore a
compatible immutable artifact. Do not routinely stop an accepted ECS task or
delete launch evidence.

## Evidence Normalizer Investigation

The Cell Evidence Normalizer consumes the Scheduler and materializer source
queues through distinct registrations. A
permanent malformed or forged record is acknowledged after a sanitized
quarantine record containing only the stable rejection code, source queue ARN,
hashed source message ID, and receipt timestamp. Do not retrieve or log raw
untrusted bodies during routine triage. Query the normalizer log group for
`normalizer_record code=<NORMALIZER_...>` and correlate the stable code to the
quarantine record; inspect the bounded `EvidenceNormalizerRejected` metric
using only `job_id`, `environment`, and `state` dimensions.

For an immediate rollback, disable the normalizer event-source mapping while
keeping the canary schedule disabled. Do not delete scheduler source, canonical
ingress, quarantine, DLQ, mapping, or log evidence during the 14-day retention
period. Replaying quarantine data is not an MVP operation: correct the
registration/configuration, deploy a compatible runtime and Cell Contract, and
perform any replay through a separately reviewed procedure.

## Canary Bootstrap Recovery

The platform-owned canary fixture is a non-production, disabled Scheduler
acceptance path. It must not be enabled, manually invoked, or used to claim an
ECS launch, completion, or alert until the later Cell processors are deployed
and disposable-account evidence is recorded. Its encrypted SQS test queue has
no production subscriptions or customer integrations.

For a failed canary definition change, retain the Cell reservation, CONFIG
object versions, Scheduler queues, log group, and test-notification evidence;
restore the last compatible fixture definition and keep the schedule disabled.
Do not use routine destructive cleanup. The Terraform reservation and CONFIG
object intentionally use `prevent_destroy`; pilot retirement or evidence
deletion needs a separately reviewed procedure after investigation and rollback
requirements have elapsed.

## ECS And Completion Evidence Investigation

ECS task-state capture is restricted to the Cell account, Region, and exact
registered cluster. The normalizer resolves the AWS task ARN through the
occurrence task-ARN index; an absent mapping is retried as bounded orphan work.
Do not use application assertions to identify a job or occurrence.

Completion records arrive through the exact canary log-group subscription and
retain AWS log-group/log-stream metadata. Malformed, secret-bearing, wrong-task,
or unsupported records are acknowledged only after a stable sanitized rejection
path. A success requires authoritative `RUNNING`, one accepted success marker,
and essential-container exit code zero. A stopped task or non-zero essential exit
is terminal failure, and a later marker cannot overwrite it.

For rollback, disable the exact ECS EventBridge rule and completion Lambda source
mapping/subscription, then preserve encrypted queues, DLQs, task-index evidence,
and logs for their retention window. Do not stop tasks, relaunch attempts, or
delete orphan/conflict evidence as a rollback action. Local validation proves
neither live AWS delivery timing nor IAM behavior.
