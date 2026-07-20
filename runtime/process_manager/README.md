# Process Manager

The Process Manager is the Cell-owned writer for the occurrence ledger. Story 1.7
activates only authenticated `occurrence.expected.v1` evidence from the materializer.
It validates the canonical envelope and strongly consistent CONFIG snapshot, then
atomically records the immutable processed-event fact and the `EXPECTED` occurrence.

Duplicate delivery is a no-op when the immutable event digest matches. A conflicting
digest is rejected without overwriting the accepted fact. Deterministic contract
failures are acknowledged record-locally; DynamoDB transport failures are returned in
Lambda's `batchItemFailures` response for SQS retry.

The ledger stores bounded identifiers and operator-safe fields only. It does not store
raw CONFIG, raw evidence, task attempts, deadlines indexes, alert records, or launch
authority. Query output should expose state, scheduled time, deadline, CONFIG version,
evidence IDs, and last reduction time, never secret values or Terraform state.

Rollback disables the event-source mapping or restores a compatible immutable Lambda
artifact first. Do not destroy or edit the occurrence ledger; production PITR and
deletion protection preserve the audit evidence during recovery.
