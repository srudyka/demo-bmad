
## Deferred from: code review of 1-6-materialize-future-expected-occurrences (2026-07-17)
- Define the authoritative Scheduler/materializer conformance input. Reason: Leave it hardcoded to PASS for this story, and defer the real conformance comparison to Story 1.7 or later when the Scheduler is active.

## Deferred from: code review of 1-6-materialize-future-expected-occurrences (2026-07-20)
- Authoritative Scheduler/materializer conformance remains unimplemented; `conformance_result` is hard-coded to `PASS`, so divergent occurrence times or IDs cannot block `MATERIALIZED`. Defer to Story 1.7 or a later story when the Scheduler-side comparison input is available.
