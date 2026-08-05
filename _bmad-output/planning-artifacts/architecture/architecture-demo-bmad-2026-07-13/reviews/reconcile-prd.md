# PRD-to-Architecture Reconciliation

## Verdict

**CONDITIONAL FAIL - the architecture is not preservation-complete against the finalized PRD package.**

The account-local Cell and Process Manager are a coherent response to the PRD's occurrence-aware completion requirement, and the spine preserves most IAM, CI/CD, private-networking, state-isolation, immutable-supply-chain, and correlated-completion controls. However, the architecture silently changes the scheduled-launch contract, expands MVP from one per-job module into a shared runtime platform, requires SQS DLQs that the PRD explicitly deferred, and still cannot prove every missed per-job occurrence when both paired Scheduler signals are absent. These are product-boundary and acceptance-contract changes, not implementation details.

The architecture should not advance to implementation until REC-01 through REC-05 are resolved by either changing the spine or obtaining an explicit, logged product variance that updates the PRD/addendum and acceptance gates. REC-06 through REC-09 should be closed before pilot design.

## Source Set

- Final PRD: `../../prds/prd-demo-bmad-2026-07-13/prd.md`
- Technical addendum: `../../prds/prd-demo-bmad-2026-07-13/addendum.md`
- Canonical product memory: `../../prds/prd-demo-bmad-2026-07-13/.memlog.md`
- Architecture under review: `../ARCHITECTURE-SPINE.md`

## Critical Finding

### REC-01: Paired Scheduler signals do not satisfy the production missed-occurrence contract

**Severity:** Critical  
**PRD package:** PRD FR-6 (lines 136-144), FR-15 through FR-18 (lines 223-258), FR-28 failure-injection gate (lines 351-359), NFR-8 and NFR-9 (lines 375-376), Risk table (lines 478-480); addendum lines 45-49 and 61-64; memlog decisions lines 36-41.  
**Architecture:** AD-3 (lines 59-64), AD-10 and AD-11 (lines 116-126), Deferred (line 244), Open Assumption A-2 (line 254).

**Finding:** The architecture derives both `EXPECTATION` and `LAUNCH` from EventBridge Scheduler using the same schedule contract and the same AWS scheduling service. This detects one signal missing while the other arrives, but it does not establish an Expected Occurrence when both signals are absent because the schedule is disabled, deleted, misconfigured, not evaluated, or affected by a common Scheduler failure. The Cell canary can report a Cell-wide symptom, but it cannot produce the job/Occurrence-ID record, state, deadline, and alert context required by FR-17 and FR-18. The spine explicitly defers independent cron evaluation and leaves sufficiency as assumption A-2.

This reintroduces the exact false-assurance risk the final PRD was revised to eliminate. FR-17 requires every production Expected Occurrence to reach an occurrence-aware state; FR-28 requires missing-invocation failure injection and detection within five minutes of the observable failure or deadline. A same-service second schedule plus a same-service canary is useful evidence, but it is not independent proof that each job occurrence should have existed.

**Required resolution:** Choose one of these dispositions and record it explicitly:

1. Add an independent schedule-reconciliation source that deterministically enumerates due occurrences from the versioned job schedule contract and creates/repairs missing `EXPECTED` records before their deadlines.
2. Prove through an architecture test and documented AWS failure model that the paired schedule plus canary design satisfies every FR-17/FR-28 case, including both job schedules absent while unrelated Scheduler activity continues. The proof must show per-job occurrence materialization, not only a Cell-health alarm.
3. Obtain a product-level variance that narrows the production missed-run promise and updates the PRD, addendum, risk table, success metrics, and pilot acceptance tests. An open architecture assumption alone is insufficient for a finalized Critical acceptance requirement.

## High Findings

### REC-02: The Scheduler-to-SQS-to-Process-Manager launch path contradicts explicit FR-6 and FR-10 behavior

**Severity:** High  
**PRD package:** PRD FR-6 lines 136-144 and FR-10 lines 175-183; addendum lines 61-68; memlog lines 8, 18-19, and 27-28.  
**Architecture:** Diagram lines 25-43; AD-3 lines 59-64; AD-8 lines 104-108; AD-12 lines 128-132; capability map lines 231-236.

**Finding:** FR-6 says the Platform Service creates a schedule with target ECS Task configuration. FR-10 then requires Scheduler `ecs:RunTask` access restricted to the task-definition family and ECS Cluster. The spine instead makes Scheduler send messages to SQS, gives Scheduler no ECS launch authority, and lets a shared Process Manager assume a job launch role and invoke `RunTask` later.

The new design may be safer and more capable, but it changes the actor responsible for launch, the invocation IAM model, retry/event-age behavior, the meaning of Scheduler success, task-start latency, manual recovery, and the resources a job depends upon. The spine currently labels this as an assumption while its frontmatter claims it binds all FRs; it does not identify the FR-6/FR-10 variance.

**Required resolution:** Create an explicit architecture decision/variance approved by the Platform Owner and reconcile the product contract. At minimum, revise or supersede the direct-target language; define consumer-visible Scheduler, SQS, Lambda, and `RunTask` retry semantics; map FR-10's Scheduler role requirements to Scheduler delivery, Process Manager, and job launch roles; and update failure-injection evidence for each hop. If the finalized PRD must remain unchanged, restore direct Scheduler-to-ECS launch and use the Process Manager only for evidence processing.

### REC-03: The shared Cell is an unapproved MVP product and ownership expansion

**Severity:** High  
**PRD package:** PRD FR-1 through FR-4 (lines 91-122), MVP scope lines 394-405, non-goals lines 407-419, SM-1 setup-time target (line 436); addendum infrastructure boundary lines 14-23; memlog lines 8, 10, 18, and 33.  
**Architecture:** Design paradigm lines 21-43; AD-1 and AD-2 lines 47-57; structural seed lines 199-216.

**Finding:** The finalized MVP promises one reusable `ecs-scheduled-job` Terraform Module around existing cluster/network/account dependencies. The spine introduces a second `ecs-scheduled-job-platform` module, a separately owned Cell state, SQS ingress and DLQs, DynamoDB ledger, four Lambda functions, metrics, alarms, an alert router, an SSM Cell Contract, and account/Region onboarding before any job module can work.

This changes the product's installation model, ownership boundary, deployment order, failure domain, version-compatibility surface, cost floor, and under-four-hour adoption workflow. The new Cell is not merely internal code inside the promised module: AD-2 explicitly prevents application roots from owning it and requires a separately deployed shared service. The PRD has no Cell readiness, availability, upgrade, compatibility, or tenancy requirements.

**Required resolution:** Obtain product approval for a two-module shared-service MVP and add the Cell to the declarative contract, Existing Infrastructure boundary, core workflow, MVP scope, ownership/RACI, cost counter-metrics, readiness checklist, and support/rollback policy. Define what happens when a target account/Region lacks a compatible Cell. If that expansion is not accepted, collapse required runtime resources into the per-job module or select a mechanism that does not require shared platform provisioning.

### REC-04: Mandatory SQS/DLQ behavior contradicts a recorded MVP deferral

**Severity:** High  
**PRD package:** PRD non-goal line 418; addendum Candidate Future Mechanisms line 53; memlog decision line 33.  
**Architecture:** Diagram line 31; AD-11 lines 122-126; Deferred retention line 248.

**Finding:** The product record explicitly defers SQS dead-letter queue behavior unless it is trivial and does not complicate the module interface. The architecture makes an encrypted SQS ingress queue, a 14-day redrive DLQ, and a shared Scheduler DLQ mandatory correctness components. Their replay behavior, retention, alarms, IAM, cost, and runbooks are central to the Cell and are not trivial optional inputs.

The likely semantic distinction is that the PRD deferred a job-facing Scheduler payload DLQ while the architecture needs internal platform durability. That distinction was never written into the finalized product package, so the spine currently contradicts both the PRD and canonical memlog.

**Required resolution:** Record an approved clarification that internal Cell ingress/redrive DLQs are in scope while consumer-configurable job payload DLQs remain deferred, then add their operational acceptance gates. Otherwise remove mandatory SQS/DLQ behavior from MVP.

### REC-05: Shared Cell failure planes are not reconciled with production observability and acceptance gates

**Severity:** High  
**PRD package:** PRD FR-15 through FR-18 (lines 223-258), FR-27 and FR-28 (lines 343-359), NFR-6 through NFR-9 (lines 373-376), SM-3/SM-6/SM-8 (lines 438, 444, and 446).  
**Architecture:** Diagram lines 31-42; AD-10, AD-11, and AD-14 lines 116-126 and 140-144; Deferred line 244.

**Finding:** The Process Manager path adds shared failures not covered by the PRD's original four planes: SQS backlog/redrive failure, Lambda throttling or poison batches, Process Manager deployment/config failure, DynamoDB throttling/conditional-write exhaustion, log-ingestor/subscription failure, deadline-scanner failure, launch-role assumption failure, alert-router failure, and Cell-contract incompatibility. AD-11 defines one heartbeat canary, but the spine does not require alarms, detection deadlines, ownership, runbook paths, or failure-injection evidence for these components. A heartbeat can succeed while a job-specific event type, launch role, log subscription, deadline bucket, or alert route is broken.

Because a Cell is shared within an account/Region, these are correlated multi-job failures. Claiming FR-15 through FR-18 and FR-28 preservation requires treating Cell health as a first-class failure plane and proving both generic and job-specific paths.

**Required resolution:** Add a Cell SLO/health contract and production gate covering queue age/depth and DLQs, Lambda errors/throttles/concurrency, DynamoDB errors/throttles, event-schema rejection, log-ingestion lag, deadline-scanner freshness, Process Manager launch/assume-role failures, alert-router delivery, Cell-contract compatibility, and canary path completeness. Specify whether failures create one platform incident or per-job alerts, and link each alarm to Platform Owner runbook actions. Extend FR-28-equivalent integration tests across every new hop.

### REC-06: The paired-schedule state machine omits out-of-order and orphan evidence transitions

**Severity:** High  
**PRD package:** FR-7 lines 146-152; FR-17 lines 240-250; NFR-5 and NFR-9 lines 372 and 376; addendum lines 45-49.  
**Architecture:** AD-3 lines 59-64; AD-6 and AD-7 lines 77-102; AD-11 lines 122-126.

**Finding:** `EXPECTATION` and `LAUNCH` are independent at-least-once deliveries through separate schedule groups and a standard SQS queue. Ordering is not guaranteed. The canonical state diagram starts at `EXPECTED` and does not define what the Process Manager does when `LAUNCH`, ECS task evidence, completion evidence, or `DEADLINE_REACHED` arrives before `EXPECTATION`; nor does it define recovery when expectation evidence arrives after a terminal outcome. Rejecting or delaying those signals can create duplicate launches or false misses, while accepting them without a rule can violate the single-writer state contract.

**Required resolution:** Define commutative, idempotent transitions for every evidence type in every relevant current/absent state, including orphan buffering or occurrence synthesis, late expectation, duplicate LAUNCH, replay after DLQ, and concurrent deadline evidence. Add model/contract tests that permute event ordering and duplication and still produce the FR-17 canonical result without a second ECS launch.

## Medium Findings

### REC-07: Deployment Identity does not include the shared runtime that decided and launched the occurrence

**Severity:** Medium  
**PRD package:** Deployment Identity definition and FR-4/FR-24 (PRD lines 72, 116-122, and 311-317).  
**Architecture:** AD-5 lines 71-75; AD-8 lines 104-108; AD-14 line 144; AD-17 lines 158-162.

**Finding:** The architecture version-controls job CONFIG and dependencies but never defines a canonical Deployment Identity record containing Cell module version, Process Manager build/image or Lambda code revision, event schema version, and Cell Contract version. A shared runtime can change launch/completion behavior without changing the job's task definition or source revision, so the original PRD identity is no longer sufficient to answer what code decided and launched a task.

**Required resolution:** Extend the architecture's Deployment Identity and every occurrence record/alert to include immutable job, Cell, Process Manager, workflow, module, provider, and schema/config versions. Define how an operator maps a historical occurrence to those artifacts after a Cell upgrade or rollback.

### REC-08: Manual rerun semantics did not land in the occurrence and launch model

**Severity:** Medium  
**PRD package:** FR-9 lines 163-169 and Runbook FR-27 lines 343-349.  
**Architecture:** AD-4 occurrence identity lines 65-69; AD-8 client token lines 104-108; state machine lines 83-102.

**Finding:** The spine derives `occurrence_id` solely from job ID and scheduled time and uses it as the ECS `clientToken`. It does not define whether a manual rerun is another attempt on the original occurrence, a new synthetic occurrence, or a replay of LAUNCH evidence; how authorization is recorded; when ECS client-token deduplication blocks the rerun; or how multiple successful attempts become `AMBIGUOUS` without making all authorized recovery ambiguous.

**Required resolution:** Add a manual-rerun command/event contract with actor, reason, original occurrence, attempt identity, authorization, duplicate-effects acknowledgement, and deterministic state transitions. Preserve the reviewed task/config identity and make the runbook procedure executable without editing schedules.

### REC-09: Several conditional product capabilities are absent from the spine

**Severity:** Medium  
**PRD package:** FR-3 protected tag behavior lines 107-114; FR-13 optional security-group creation lines 202-209; FR-19 optional dashboard lines 260-266; NFR-17 line 390.  
**Architecture:** AD-13 lines 134-138; AD-14 lines 140-144; capability map lines 227-239; Deferred line 248.

**Finding:** The spine does not state how required/protected tags apply to shared Cell resources, omits the optional module-created security-group path, and provides no owner/resource path for the optional per-job operational view. It also introduces Cell-wide retention defaults without linking them to the PRD's cost guardrail or configurable platform bounds.

**Required resolution:** Map these capabilities explicitly or mark them as approved deferrals: protected tag merge rules for both modules, optional dedicated task security group with bounded egress, optional per-job CloudWatch dashboard/view, and documented/configurable retention and cost limits.

## Assumption and Gate Reconciliation

| Product assumption or gate | Architecture treatment | Reconciliation status |
|---|---|---|
| A1: Confirm EventBridge Scheduler at architecture kickoff | The entire spine adopts Scheduler and excludes alternatives, while still labeling related decisions assumptions | **Decision not logged back to product memory.** Record adoption or keep architecture conditional. |
| A2: Exact production notification target before production pilot | Consumer target retained; Alert Router added | Preserved as deferred, but Cell-level platform incident routing also needs an owner and destination. |
| A3: Current and previous major support | Cell/job modules and event/config schemas add independent version axes | Preserved incompletely; define compatibility and support across both modules and queued schema versions. |
| A4: Tested Terraform/provider/Fargate matrix before pilot | Spine lists Terraform 1.15.8, AWS provider 6.54.0, Python 3.14, Fargate `LATEST` | **Do not treat seeds as supported versions.** Keep them explicitly provisional until the PRD gate is satisfied. |
| A7: Named pilot jobs/owners before execution | Deferred | Preserved. |
| A8: Publishing repositories/access/channel before release | Module/workflow distribution assumed | Preserved as a release blocker; add the new Cell module/runtime artifact repositories. |
| A9: GitHub controls before production | Architecture requires custom `sub`, immutable repository IDs, protected Environment, no bypass | Preserved but narrowed to a stronger assumption. Validate organization capability; if unavailable, the spine currently has no implemented fallback. |
| A10: Accounts/Region/scale before MVP environment testing | One Cell per account/Region assumed | Preserved; capacity, quotas, and correlated failure testing for one to five jobs still need explicit evidence. |
| A11: Staged non-production gates | Not contradicted | Preserved. |

## Preserved Areas

The following product requirements are materially represented in the spine and do not need product reconciliation before architecture refinement:

- Account/Region locality and no cross-repository Terraform-state coupling: AD-1, AD-15.
- Separate IAM roles, scoped `iam:PassRole`, bounded apply authority, and no self-modifying authorization: AD-8, AD-12, AD-16.
- Private ECS networking and secret references rather than values: AD-13 and consistency conventions.
- Occurrence ID, single-writer conditional state, correlated success plus zero exit, deadline-only maximum runtime: AD-4, AD-6 through AD-10.
- Credential-free untrusted PRs, exact saved-plan apply, immutable GitHub/module/action/provider/image dependencies: AD-16, AD-17.
- Two-phase schedule changes and rollback awareness: AD-18.

## Required Disposition Before Implementation

1. Resolve REC-01 with independent per-job occurrence reconciliation or an explicit product-scope change.
2. Approve and document the direct-launch variance in REC-02.
3. Approve the shared Cell/two-module MVP boundary and internal DLQs in REC-03 and REC-04.
4. Add Cell observability/failure-injection gates and order-independent state transitions for REC-05 and REC-06.
5. Update the architecture's decision log and product memlog with every accepted variance; do not leave finalized PRD contradictions as architecture assumptions.
6. Close REC-07 through REC-09 before the pilot architecture is declared implementation-ready.

