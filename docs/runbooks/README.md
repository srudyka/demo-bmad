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
