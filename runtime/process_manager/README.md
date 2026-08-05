# Process Manager

The Process Manager is the Cell-owned writer for the occurrence ledger. It accepts
authenticated `occurrence.expected.v1` and Scheduler `occurrence.launch.v1`
evidence plus handler-authorized `command.authorized.v1` non-production reruns.
Launch processing requires a `MATERIALIZED` CONFIG snapshot, reserves
attempt zero transactionally, and derives one deterministic ECS client token.

For a manual rerun, the manager verifies the command, original terminal
occurrence, exact CONFIG/schedule generation/Deployment Identity, owner
generation, non-production scope, and compensation acknowledgement before the
launch adapter runs. It creates one synthetic occurrence retaining the original
link, command, actor, approval, verification plan, and identity. The original
occurrence is never updated, and duplicate or uncertain delivery cannot create
attempt one; unresolved launch uncertainty is recorded as `AMBIGUOUS`.

Duplicate delivery is a no-op when the immutable event digest matches. A conflicting
digest is rejected without overwriting the accepted fact. Deterministic contract
failures are acknowledged record-locally; DynamoDB transport failures are returned in
Lambda's `batchItemFailures` response for SQS retry.

The ledger stores bounded identifiers and operator-safe fields only. Attempt zero
records retain the exact task definition, private network, launch role, token,
Deployment Identity, retry deadline, and ECS task ARN. A task-ARN GSI supports
correlation but is not correctness authority; the base table remains authoritative.
Query output should expose state, scheduled time, deadline, CONFIG version, bounded
evidence IDs, and launch outcome, never secret values or Terraform state.

The launch role is the only role with `ecs:RunTask` and `iam:PassRole`. The Process
Manager assumes only the registered launch role and uses `count=1`, private
`awsvpc`, `assignPublicIp=DISABLED`, exact task revision, `startedBy`, and
platform-owned tags. HTTP 200 `failures[]`, transport uncertainty, multiple task
matches, parameter conflicts, and expired reconciliation windows are durable
failure or `AMBIGUOUS` outcomes; they never create attempt one.

Rollback disables the event-source mapping and canary schedule/launch intake or
restores a compatible immutable Lambda artifact first. Preserve the occurrence and
attempt ledger; do not automatically stop or relaunch an ECS task already accepted
by AWS. Production PITR and deletion protection preserve the audit evidence.
