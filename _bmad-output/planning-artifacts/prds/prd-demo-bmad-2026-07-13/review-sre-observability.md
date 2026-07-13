# SRE and Observability Review

## Overall Verdict

**NOT READY for production acceptance.** The PRD has a strong four-plane failure model, explicitly rejects “invoked means succeeded,” and makes runbooks and alarm tests part of the product. However, two production-critical gaps remain: the proposed log metric-filter design cannot yet prove one successful completion for each expected schedule occurrence, and the requirements do not close the `RunTask` response-failure path where no ECS task exists to emit a task-state event. The MVP can proceed through architecture and non-production prototyping, but the production pilot gate must remain closed until those paths have testable designs and evidence.

## Critical Findings

### C-1: The completion signal is an aggregate count, not a per-run completion contract

**Locations:** FR-14 and FR-17 (`prd.md` lines 206-237); A8 (`prd.md` line 485); Initial Completion Detection Pattern (`addendum.md` lines 43-49)

The proposed mechanism counts a configurable success log pattern and alarms when it is absent from a schedule/runtime window. That does not by itself establish which expected occurrence completed. A late success from the prior occurrence, a duplicate invocation, a retry, or two successes from one occurrence can mask a missing adjacent occurrence. A plain marker such as `JOB_COMPLETED_SUCCESSFULLY` has no schedule occurrence, task ARN, attempt, or Deployment Identity with which to correlate delivery, execution, and business completion.

CloudWatch metric-filter behavior creates another ambiguity: a default value is emitted only for a period in which logs were ingested but no event matched; no logs means no datapoint. Dimensioned metric filters cannot use a default value. An alarm can treat missing datapoints as breaching, but a continuously evaluated fixed-period alarm does not inherently understand a cron due-time plus completion grace period. Treating all between-run missing periods as breaching causes false alarms; treating them as non-breaching can miss the absent run. These are platform semantics, not details each Job Owner should rediscover.

**Required action:**

- Define an expected-occurrence identity and a completion-event schema. At minimum, correlate job/schedule identity, expected occurrence time or occurrence ID, ECS task ARN, invocation attempt, completion time, result, and Deployment Identity.
- Define the authoritative comparison between expected occurrences and observed completions, including retries, duplicates, late log ingestion, adjacent windows, disabled schedules, manual runs, and clock/time-zone behavior.
- If MVP remains metric-filter-only, state the exact supported cadence/window constraints and prove that the generated alarm configuration works for every supported shape. The production claim must not exceed that tested subset.
- Make zero missed failures in the pilot failure matrix a release gate; set a quantitative false-positive threshold rather than “acceptable.”

**Evidence:** AWS documents that metric-filter default values require some log ingestion during the period and are unavailable when dimensions are assigned: [Creating metrics from log events using filters](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/MonitoringLogData.html). CloudWatch alarm missing-data treatment is configurable but does not create schedule-aware evaluation windows: [Configuring how CloudWatch alarms treat missing data](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/alarms-and-missing-data.html).

### C-2: The `RunTask` response-failure path has no required detector

**Locations:** FR-15 and FR-16 (`prd.md` lines 214-228); Risk table (`prd.md` lines 452-456); Research-Backed Architecture Inputs (`addendum.md` lines 59-61)

The addendum correctly states that an accepted Scheduler target request and an ECS task outcome are different planes, but the FRs do not require a mechanism that proves `RunTask` created a task. `RunTask` can return HTTP 200 with a non-empty `failures` array and no task. In that case there may be no task ARN and therefore no ECS task-state event for FR-16 to observe. Scheduler metrics are best-effort and grouped by Schedule Group, so FR-15 cannot simply assume they provide job-level evidence for this path. The current scope also defers SQS DLQ behavior without naming an alternative source of durable evidence.

**Required action:**

- Define how the platform observes and classifies `RunTask.failures`, and require a positive launch correlation from each expected occurrence to a created ECS task ARN.
- State whether Scheduler metrics, a per-job Schedule Group, a Scheduler DLQ, CloudTrail, an invocation intermediary, or another mechanism supplies the evidence. Do not defer the decision to implementation while claiming complete launch-failure detection.
- Add pilot cases for an API-level rejection, HTTP-200 response with a non-empty `failures` array or equivalent placement failure, throttling with exhausted retries, and accepted task that later reaches `TaskFailedToStart`.
- Require monitoring of the detection path itself so an EventBridge rule, metric pipeline, or alert target failure does not silently remove coverage.

**Evidence:** The ECS API documents `failures` and `tasks` together in a successful HTTP-200 `RunTask` response: [RunTask API](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_RunTask.html). Scheduler CloudWatch metrics are best-effort and use Schedule Group dimensions: [Monitoring EventBridge Scheduler with CloudWatch](https://docs.aws.amazon.com/scheduler/latest/UserGuide/monitoring-cloudwatch.html).

## High Findings

### H-1: Schedule semantics are underspecified for a platform contract

**Locations:** FR-6 through FR-8 (`prd.md` lines 133-155); MVP scope (`prd.md` lines 371-381)

The contract names expression, optional time zone, retries, and enabled state, but does not define supported expression types, flexible time windows, start/end dates, daylight-saving transitions, schedule updates near a due time, or what constitutes the canonical expected occurrence. These directly determine missed-run detection and duplicate/late delivery behavior. A “deployed schedule matches configuration” test is insufficient if the configuration does not define these semantics.

**Required action:** Specify the MVP schedule contract and defaults: supported `rate`/`cron`/one-time shapes, exact versus flexible delivery, time-zone and DST behavior, start/end handling, update behavior, and the timestamp used as the occurrence deadline. Add acceptance cases for boundary behavior relevant to every supported schedule type.

### H-2: Unsafe overlap can be declared but is not prevented or gated

**Locations:** FR-7 and FR-8 (`prd.md` lines 141-155); Non-goals (`prd.md` lines 383-395); NFR-5 (`prd.md` line 350)

Version one detects an overdue task but does not stop it, while Scheduler retries and the next scheduled occurrence can start additional tasks. The PRD requires the owner to document whether overlap is safe, yet it allows a production job marked overlap-unsafe to deploy without evidence of locking or an interval that precludes overlap. Documentation alone does not control a known data-integrity risk.

**Required action:** Add a production gate: an overlap-unsafe job must provide verified application locking/idempotency or satisfy a platform-validated cadence/retry/runtime relationship with explicit safety margin. The Runbook must cover locating and stopping a runaway task, deciding whether the next occurrence should be suppressed, and reconciling partial or duplicate side effects. Test retry/next-window overlap, not only ordinary consecutive windows.

### H-3: Alarm service levels and state behavior are not acceptance criteria

**Locations:** FR-15 through FR-18 (`prd.md` lines 214-245); NFR-6 (`prd.md` line 351); SM-C2 (`prd.md` line 427)

“Actionable” content and alarm testing are necessary, but no requirement defines maximum detection delay, notification delay, paging severity, M-of-N behavior, missing-data policy, repeat notification/escalation for consecutive failed runs, OK/recovery notification, alarm suppression while a schedule is intentionally disabled, or behavior during deployment and maintenance. Tracking noise without a target does not establish an acceptance gate. A CloudWatch alarm that remains in `ALARM` may also not emit a new state-transition action for every subsequent missed run.

**Required action:** Define a per-job alarm policy tied to schedule criticality: latest detection and notification deadlines, severity/routing, evaluation and missing-data settings, dedup/escalation, recovery behavior, and intentional-disable/maintenance handling. Require synthetic end-to-end alert tests through the actual production-equivalent destination and set pilot thresholds for false positives, false negatives, and notification latency.

### H-4: ECS runtime detection is outcome-focused but not sufficiently attributable

**Locations:** FR-4 (`prd.md` lines 113-119); FR-16 (`prd.md` lines 222-228); FR-24 (`prd.md` lines 292-298)

The PRD requires detection of start failures and non-zero essential-container exits but does not require the ECS task-state event matching and attribution contract. Shared clusters can produce unrelated task events, task-definition revisions change, multiple containers can disagree, manually rerun tasks coexist with scheduled tasks, and stop codes such as `TaskFailedToStart` need different response from application exit failures. Without explicit identifiers and matching rules, implementations can either miss tasks or alarm on another job.

**Required action:** Require lifecycle telemetry to preserve task ARN, cluster, task-definition family/revision, launch type, stop code/reason, essential-container name/exit code, initiator or invocation correlation, schedule/job identity, and Deployment Identity. Define classification for pre-start failures, OOM/resource failures, operator stops, zero-exit-without-business-success, and nonessential sidecar failure. Test isolation on a shared cluster and manual reruns. ECS task-state events expose stop codes/reasons and container exit details suitable for this classification: [ECS task state change events](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_task_events.html).

### H-5: Pilot evidence has no quantitative reliability gate or representative cadence matrix

**Locations:** SM-4, SM-6, SM-8, and SM-C2 (`prd.md` lines 418-428); Rollout (`prd.md` lines 431-439); OQ-3 (`prd.md` line 469)

The pilot must demonstrate failure simulations, but “acceptable” false positives/negatives is undefined and one or two low-risk jobs may exercise only one cadence and runtime shape. A one-sprint production target can pressure the team to accept incomplete evidence. Nothing states how many consecutive occurrences must be observed, which schedule/time-zone shapes must be tested, or how detection pipeline outages are simulated.

**Required action:** Define a pre-production conformance suite independent of pilot workload count. It should include supported cadence boundaries, consecutive successes, consecutive misses, late completion, late log delivery, duplicate delivery, Scheduler retry exhaustion, `RunTask` placement failure, `TaskFailedToStart`, non-zero exit, zero-exit without success, timeout with a still-running task, manual rerun, schedule disabled/re-enabled, alarm destination failure, and module rollback. Gate production on zero false negatives, a stated false-positive ceiling, bounded detection/notification latency, and named owner sign-off.

## Medium Findings

### M-1: Recovery objectives cover restoration time but not business catch-up

**Locations:** FR-9 (`prd.md` lines 157-163); FR-27 (`prd.md` lines 322-328); Rollback Principles (`prd.md` lines 441-448)

The Runbook includes reruns and each job declares an RTO, but scheduled-job recovery also needs the latest acceptable business completion time, data-loss/catch-up tolerance, and whether missed windows are skipped, replayed, or backfilled. Infrastructure recovery can meet an RTO while leaving required business work incomplete.

**Required action:** Add job-specific recovery requirements for latest acceptable completion, catch-up/backfill policy, partial-side-effect assessment, evidence of successful recovery, and escalation when the business deadline cannot be met.

### M-2: Rollback principles do not address in-flight and already-delivered work

**Locations:** FR-24 (`prd.md` lines 292-298); Rollback Principles (`prd.md` lines 441-448)

Pinning and restoring known-good infrastructure is sound, but schedule rollback does not retract already delivered retries, stop an in-flight task, or reverse application side effects. Reverting a module version may also have a materially different Terraform plan from restoring an image or task-definition revision.

**Required action:** Require distinct rollback playbooks for schedule configuration, image/task definition, IAM/networking, observability, and module version. Each must state how to handle pending retries and in-flight tasks, expected Terraform replacements/destruction, state compatibility, data compensation, and post-rollback catch-up.

### M-3: The monitoring path has no explicit availability or retention contract

**Locations:** FR-14 through FR-18 (`prd.md` lines 206-245); NFR-16 (`prd.md` lines 364-367)

Log retention is explicit but no minimum is set, and task lifecycle/alarm evidence retention is not defined. There is also no availability objective for the alerting pipeline or required alarm for its own delivery failures. Incident diagnosis may fail after the fact even though the workload logs were retained.

**Required action:** Define guardrailed minimum retention by environment for workload logs, lifecycle events, alarm history, and deployment evidence. Require health signals for EventBridge targets, log metric/filter or evaluator failures, and notification delivery where the chosen integrations support them.

## Positive Controls Worth Preserving

- The four-plane model in §5.4 is the correct top-level operating model.
- FR-7 correctly separates Scheduler delivery retries from application retry behavior and acknowledges at-least-once delivery.
- FR-8 correctly avoids misrepresenting Fargate `stopTimeout` as a maximum runtime.
- FR-18 and FR-27 connect every production alarm to ownership and a Runbook.
- FR-23, FR-24, and the rollback principles preserve reviewed Deployment Identity and known-good revisions.
- SM-C2 recognizes alert noise as a product failure rather than an on-call problem.

## Gate Recommendation

Keep the PRD in draft until C-1 and C-2 are resolved in the requirements or explicitly converted into production-pilot blockers with named owners and objective exit evidence. Resolve H-1 through H-5 before architecture is approved for implementation; medium findings may be incorporated into the Runbook, Production Readiness Checklist, and operational NFRs before the production pilot.
