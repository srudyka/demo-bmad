# Alert Router

The Alert Router consumes `ALERT_OUTBOX` records from the occurrence-ledger
DynamoDB Stream and runs a bounded EventBridge reconciliation query for pending
obligations. Before publishing, it strongly reads the occurrence and CONFIG
registry, suppressing stale obligations and enriching the message only from the
authoritative secret-free CONFIG snapshot.

Each notification has a deterministic identity in the encrypted notification
ledger. Conditional reservation prevents concurrent duplicates; confirmed SNS
responses are recorded as `DELIVERED`, while publication uncertainty is recorded
as `AMBIGUOUS` and is not automatically replayed.

Rollback disables the Stream event source mapping and reconciliation rule while
retaining the outbox, notification ledger, queues, and logs for later recovery.
