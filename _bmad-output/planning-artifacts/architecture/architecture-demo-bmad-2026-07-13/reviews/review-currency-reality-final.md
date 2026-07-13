# Final Currency and Reality Review

## Scope

- Artifact: current `ARCHITECTURE-SPINE.md`
- Review date: 2026-07-13
- Rerun focus: prior ordering, DynamoDB GSI, CloudWatch alarm, Terraform floor, and SQS/Lambda runtime findings
- Reporting threshold: critical and high only

## Verdict

**Pass. No remaining critical or high currency/reality findings.**

## Prior Finding Closure

| Prior finding | Status | Current architecture evidence |
| --- | --- | --- |
| Paired Scheduler ordering was unsafe through standard SQS | Closed | AD-3 now materializes `EXPECTED` occurrences independently at least 24 hours ahead and Scheduler emits only `LAUNCH`. AD-7 defines arrival-order-independent, commutative evidence reduction and handles a valid launch with a late/missing expectation as an explicit Cell defect. This no longer relies on ordering that EventBridge Scheduler or standard SQS does not guarantee. |
| One-time deadline GSI query could miss an occurrence | Closed | AD-10 now requires a durable watermark, bounded lookback rescans, base-table verification, and reconciliation of nonterminal occurrences through the maximum lateness horizon. This accounts for DynamoDB GSI eventual consistency. |
| CloudWatch state changes could suppress consecutive occurrence alerts | Closed | AD-14 now emits one idempotent occurrence-alert event from each newly accepted failure state and limits CloudWatch alarms to sustained job/Cell health. Alert delivery no longer depends on an alarm returning to `OK` between failed runs. |
| Terraform `>= 1.5` could not use S3 native lock files | Closed | Stack now requires Terraform `>= 1.10, < 2.0` for all roots and modules using AD-15. S3 native locking was introduced in Terraform 1.10. |
| SQS/Lambda replay behavior lacked safe runtime bounds | Closed | AD-11 now requires `ReportBatchItemFailures`, `maxReceiveCount >= 5`, 14-day DLQ retention, visibility of at least six times function timeout plus batch window, and validated bounds across timeout, batching, concurrency, payload size, and redrive. |

## Currency Confirmation

- Terraform 1.15.8 and AWS provider 6.54.0 remain valid dated test seeds; the spine correctly assigns the ongoing patch matrix to code, workflows, contracts, and lock files.
- Lambda Python 3.14 remains supported, while AD-17 now pins Python dependencies and explicitly treats managed runtime patching as an exception.
- Fargate `LATEST` remains supported and currently resolves to Linux platform 1.4.0; AD-17 now records the resolved platform and gates observed AWS runtime changes rather than claiming full immutability.
- GitHub custom OIDC subject and protected Environment capabilities remain explicitly gated by A-2 before production rather than silently assumed available.

## Gate Decision

The currency/reality reviewer gate passes at the requested critical/high threshold. The five previously blocking findings are closed in the architecture text and backed by explicit compatibility or failure-injection requirements.
