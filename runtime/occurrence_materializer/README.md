# Occurrence Materializer

This runtime validates an immutable CONFIG document and materializes the next
24 hours of `occurrence.expected.v1` evidence. It verifies the registered
Cell/account/Region, namespace generation, CONFIG hash, exact Scheduler ARN,
and immutable Scheduler delivery role ID before it emits evidence. The AWS
adapter first conditionally stores a `VALIDATED` immutable snapshot, sends the
deterministic envelopes to its dedicated source queue, then conditionally marks
that same snapshot `MATERIALIZED`.

It does not write occurrence ledger records, launch ECS tasks, mutate
Scheduler, consume canonical ingress, or publish alerts. An adapter retry may
redeliver source messages after a partial send; the producer event ID is stable
for the logical occurrence and the later reducer owns deduplication.
