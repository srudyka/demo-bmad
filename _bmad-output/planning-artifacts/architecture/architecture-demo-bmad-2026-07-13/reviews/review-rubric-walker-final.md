# Final Architecture Spine Rubric Review - ECS Scheduled Jobs Platform Service

## Verdict

**CONDITIONAL FAIL - one high-severity launch-idempotency gap remains.** The revised spine closes the prior state-reducer, occurrence-alerting, configuration lifecycle, paradigm-ratification, Terraform-floor, and network-egress findings. It is otherwise complete at initiative/platform altitude, covers the declared capabilities, and defines a strong operational and environmental envelope. Build handoff should wait until replay behavior is bounded by the actual ECS idempotency window.

The deterministic spine linter passes with zero findings.

## Prior Finding Closure

| Prior finding | Status | Closure evidence |
| --- | --- | --- |
| C-1 - retry/attempt reducer contradiction | Closed, except for the replay TTL issue below | AD-7 fixes one platform attempt per occurrence; AD-8 transactionally reserves deterministic attempt zero and reuses it for delivery retries; AD-9 defines terminal truth; AD-21 moves application retries inside that one task and makes manual reruns separate synthetic occurrences. |
| H-1 - alarm transitions lose occurrence notifications | Closed | AD-14 adds an idempotent occurrence-alert queue emitted directly by the Process Manager and retains CloudWatch alarms only for sustained job/Cell health. |
| H-2 - CONFIG retention and shared contract lifecycle | Closed | AD-5 introduces content-addressed inbox/registry publication; AD-23 makes schemas and fixtures normative; AD-24 defines expand/migrate/contract compatibility and append-only CONFIG/task-definition retention with controlled garbage collection. |
| H-3 - brokered launch remained unratified | Closed | AD-1 through AD-3 are now marked adopted, and the superseding paradigm assumption was removed. |
| H-4 - Terraform floor incompatible with S3 lockfile | Closed | The Stack now requires Terraform `>= 1.10, < 2.0`; Terraform 1.10 introduced S3 native state locking. |
| H-5 - deferred security-group egress | Closed | The Task network convention prohibits ingress, requires explicit egress destinations, and treats unrestricted Internet egress as a blocking production exception. Deferred now points to that minimum contract. |

## Remaining High Finding

### H-1: Fourteen-day replay can outlive the 24-hour ECS `RunTask` idempotency token

**Locations:** AD-8 (lines 113-117), AD-11 (lines 131-135), AD-21 (lines 191-195), AD-24 (lines 209-213)

**Problem:** AD-8 claims crash-window idempotency because every delivery retry reuses the deterministic `clientToken`, and AD-21 states that Scheduler/SQS retries never create a second ECS task. AD-11, however, retains failed evidence for replay from a 14-day DLQ. AWS retains `RunTask` client-token idempotency for at most 24 hours, or task lifetime plus one hour when shorter. Replaying a launch event after that TTL can call `RunTask` again with the same expired token and create a second task for the same occurrence.

The durable attempt reservation does not by itself close this uncertainty: after a crash following a successful `RunTask` but before recording its response, the ledger can remain launch-pending. If ECS task-state/completion evidence was also delayed or lost during the outage, a late replay cannot prove whether the original task existed. Separate implementations could relaunch, mark failed, or require operator reconciliation while all claiming to reuse the token.

**Required closure:** Add a fail-closed launch-reconciliation rule. Automatic `RunTask` retry must stop before the ECS client-token TTL expires. After that boundary, a launch-pending attempt must never call `RunTask` automatically; it must reconcile durable task evidence using the reserved task tags/`startedBy`, ECS/CloudTrail evidence where retained, and the ledger. If existence cannot be proven, transition to `AMBIGUOUS` and require an authorized synthetic manual rerun rather than reuse the original occurrence. Put the TTL, reconciliation states, and pre/post-expiry crash fixtures in the Compatibility Package.

AWS documents a maximum 24-hour `RunTask` client-token TTL: [Amazon ECS idempotency](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_Idempotency.html).

## Final Gate

No critical findings remain. Close H-1 before build handoff; after that change, the Good-spine checklist has no remaining critical/high blocker from this review.
