# Final Currency Blocker Review

## Verdict

**Fail. One high-severity current-service behavior issue remains.**

## High Finding

### AD-8 assumes a fixed 24-hour ECS `RunTask` idempotency window

**Architecture text:** AD-8 states that no replay may call `RunTask` "after the 24-hour ECS client-token window," implying that reuse is safe at any point before 24 hours.

**Current AWS behavior:** The `RunTask` client-token TTL is the lower of:

- 24 hours; or
- the launched resource lifetime plus one hour.

A task that starts and stops quickly can therefore expire its token well before 24 hours. AWS documents this in [ECS RunTask idempotency](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_Idempotency.html).

**Impact:** A delayed delivery retry or replay using the same token after the actual resource-lifetime-based TTL has expired can be treated as a new `RunTask` request and launch a second ECS task for the same occurrence. The architecture's reserved fixed token-expiry time does not prevent that duplicate.

**Required closure:** Model the token's effective expiry as `min(first_request + 24h, last_task_stopped + 1h)` when task evidence exists, and fail closed when safe reuse cannot be proven. For ambiguous launch responses, define a conservative retry horizon and a reconciliation path that discovers the original task before any later `RunTask` call. Contract and failure-injection tests must cover a task that stops quickly, a lost `RunTask` response, delayed retry, missing task mapping, and retry after effective TTL.

## Gate Decision

All previously reviewed ordering, GSI, alert-transition, Terraform-floor, and SQS/Lambda runtime blockers remain closed. The gate fails solely on AD-8's incorrect fixed-token-window assumption.
