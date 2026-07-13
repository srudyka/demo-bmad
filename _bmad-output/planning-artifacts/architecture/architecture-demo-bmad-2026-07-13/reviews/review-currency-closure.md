# Currency and Reality Closure Review

## Verdict

**PASS. No Critical or High current-service, version, or implementation-reality blockers remain.**

## Closure Evidence

- **ECS retry safety:** AD-8 no longer assumes a fixed 24-hour `RunTask` idempotency window. It reserves a deadline no later than one hour after the first request, reconciles by authoritative ECS evidence before retry, and fails closed after that conservative deadline. This is consistent with AWS's documented token TTL of the lower of 24 hours or resource lifetime plus one hour: [ECS idempotency](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_Idempotency.html).
- **Source identity:** AD-9 and AD-27 derive authority from AWS-generated, source-specific metadata and treat payload identifiers only as assertions. SQS exposes an IAM role ID in `SenderId`, while ECS supports lookup by the caller-supplied `startedBy` value; returned task ARNs can then be inspected for registered tags and ledger correlation: [SQS `ReceiveMessage`](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/APIReference/API_ReceiveMessage.html), [ECS `ListTasks`](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_ListTasks.html).

## Gate Decision

The prior AD-8 blocker is closed. No remaining Critical or High currency/reality finding blocks architecture approval.
