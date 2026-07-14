---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-demo-bmad-2026-07-13/prd.md
  - _bmad-output/planning-artifacts/prds/prd-demo-bmad-2026-07-13/addendum.md
  - _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/solution-design-review.md
  - _bmad-output/planning-artifacts/implementation-readiness-report-2026-07-13.md
---

# demo-bmad - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for demo-bmad, decomposing the requirements from the PRD, architecture, and implementation-readiness correction contract into implementable stories. No UX design contract is in scope for this infrastructure platform service.

## Requirements Inventory

### Functional Requirements

FR1: An Application Engineer can declare a Scheduled Job through documented and validated inputs for identity, image, schedule, compute, command, configuration, secret references, permissions, runtime expectations, tags, and ownership without modifying module source.

FR2: A consumer can supply existing account, Region, Environment, ECS cluster, VPC, private subnets, security groups, image, notification target, CI identity, and secret references; missing or invalid dependencies fail validation or planning without the platform duplicating them.

FR3: The Platform Service applies predictable resource names and protected standard tags for Environment, Application, Service, Owner, ManagedBy, and applicable CostCenter and Repository metadata, with missing production ownership metadata blocked.

FR4: The Terraform module exposes documented operational identifiers for the schedule, task definition, log group, IAM roles, alarms, and Deployment Identity so operators do not need direct Terraform-state inspection.

FR5: The Platform Service provisions an ECS Fargate task definition with valid CPU and memory, `awsvpc` networking, platform compatibility, immutable production image identity, logging, command and environment configuration, and separate execution and task roles.

FR6: The Platform Service provisions the reviewed schedule contract, including expression, time zone, enabled state, retry behavior, flexible-window policy, daylight-saving semantics, canonical expected occurrence, completion deadline, and a unique Occurrence ID available to the job and observability path. The architecture-controlled delivery path in AR1 supersedes the PRD's direct ECS target wording.

FR7: A consumer can configure supported delivery retry attempts and event age, and the platform documents at-least-once delivery, distinguishes schedule-delivery retries from task or application retries, and requires a production idempotency or duplicate-handling declaration.

FR8: Every production job declares expected maximum runtime and overlap safety; maximum runtime is a detection deadline rather than forced cancellation, and overlap-unsafe jobs require tested application locking or idempotency.

FR9: The platform documents and authorizes a repeatable manual rerun that preserves Deployment Identity, uses the reviewed task definition without editing the schedule, verifies the result, and accounts for duplicate effects and compensation.

FR10: The Platform Service separates schedule delivery, job launch, ECS task execution, and application task responsibilities into least-privilege roles, with exact trust, `RunTask`, and `PassRole` scope as revised by the architecture's brokered launch model.

FR11: An Application Engineer can declare reviewable application IAM statements or approved, governed policy attachments; production analysis blocks unjustified wildcard, privilege-escalation, or cross-account authority.

FR12: A consumer can provide approved secret references without secret values entering Git, ordinary Terraform inputs, plans, logs, or documentation, and secret access is scoped to exact resources where supported.

FR13: Production tasks run in supplied private subnets with public IP assignment disabled and minimally scoped security groups; optional module-created security groups have no ingress and explicit egress, and required NAT or endpoint reachability is documented.

FR14: The Platform Service creates a discoverable per-job CloudWatch log group with explicit retention, and the job emits structured start, success, and failure signals containing its supplied Occurrence ID without exposing secrets.

FR15: The Platform Service detects EventBridge Scheduler target errors, throttling, dropped invocations, and supported delivery failures, routes a test failure, and identifies the affected context and Runbook.

FR16: The Platform Service detects task launch failures, including HTTP 200 `RunTask` responses with non-empty `failures[]`, task start failures, unexpected stops, and non-zero essential-container exits without alarming on a valid zero-exit completion.

FR17: Production missed-run detection is occurrence-aware: every expected occurrence is correlated with its start and exactly one completion result; absent, late, duplicate, conflicting, or wrong-occurrence evidence produces the appropriate expected, started, succeeded, failed, overdue/missed, or ambiguous state and a production alert by the configured deadline. Clearly labeled non-production jobs may use best-effort detection during MVP.

FR18: A consumer supplies an existing production notification target, and every actionable alert includes job, Occurrence ID when applicable, Environment, account, Region, failure plane, occurrence state, detection time, Deployment Identity, and Runbook; production is blocked without a target.

FR19: A consumer can optionally enable a bounded-cost CloudWatch dashboard or equivalent view that separates delivery, task, and completion status without disabling required alarms when omitted.

FR20: Pull requests run format, backend-free initialization, validation, module and example tests, security and policy scanning, and an advisory plan in a trusted context; untrusted code receives neither AWS credentials nor protected state access.

FR21: Production policy gates block missing tags, unjustified IAM wildcard or escalation, public networking, missing logs or alarms, mutable images, plaintext secrets, missing ownership, or overprivileged CI; each policy has positive and negative fixtures and governed exceptions.

FR22: CI uses short-lived GitHub OIDC credentials with exact repository, immutable workflow, deployment Environment, account, Region, and role binding; plan and apply use separate constrained roles, and production is unauthorized without enforceable protected deployment controls.

FR23: Production creates a fresh plan from the deployment revision, obtains Platform and Job Owner approval plus Security approval when required, and applies that exact sensitive, short-lived plan under controlled concurrency and isolated encrypted state.

FR24: Every deployment records image digest, task-definition revision, source revision, module and workflow version, target, workflow run, and other Deployment Identity, with reviewed rollback or forward-fix instructions and post-change verification.

FR25: The Platform Owner publishes immutable module and reusable-workflow releases under semantic versioning, supports the current and previous major through the defined compatibility horizon, documents deprecations and migrations, and commits and verifies provider lock files.

FR26: The service ships a README, input/output reference, security and architecture guidance, tested compatibility matrix, and working non-production and production examples that pass the standard validation and scanning gates.

FR27: The service ships a job Runbook template covering ownership, schedule, runtime, occurrence-aware success contract, alarms, queries, common failures, authorized reruns, escalation, rollback or compensation, and dependencies; each production pilot completes and reviews it.

FR28: A blocking Production Readiness Checklist covers IAM, secrets, networking, immutable images, logs and retention, all failure planes, ownership, approvals, rollback, Runbook, validation evidence, representative plan impact, limitations, and failure-injection acceptance within five minutes with zero false alerts across at least 20 accelerated successful windows.

### NonFunctional Requirements

NFR1: Production resources use least-privilege IAM, separate roles, restricted trust policies, mandatory permissions boundaries, and no unjustified wildcard actions or resources.

NFR2: Secrets never appear in source control, ordinary Terraform variable values, unrestricted logs, PR comments, plans exposed to unauthorized readers, messages, occurrence records, CONFIG, or documentation.

NFR3: Production ECS tasks use private networking with public IP assignment disabled.

NFR4: CI uses short-lived OIDC credentials and minimal `GITHUB_TOKEN` and AWS permissions.

NFR5: Delivery is explicitly at least once, and every job handles duplicate effects through idempotency, locking, or another reviewed mechanism.

NFR6: Alarms are actionable, tested, and identify the failure plane, owner, Environment, occurrence context, and Runbook.

NFR7: Platform changes have reproducible deployments and documented rollback or forward-fix procedures.

NFR8: Logs or successful schedule invocation alone never qualify a production job as observable or successfully completed.

NFR9: Occurrence state is durable and queryable for the operational investigation window, and transitions are idempotent so duplicate or reordered signals cannot silently overwrite terminal outcomes.

NFR10: Terraform interfaces are explicit, documented, validated, and backward-compatible within a major version.

NFR11: Terraform modules follow the repository's standard structure and include executable examples and focused automated tests.

NFR12: Architecture validation supersedes the PRD's provisional compatibility assumption: all roots and modules require Terraform `>= 1.10, < 2.0`; Terraform 1.15.8, AWS provider 6.54.0, Python 3.14, and ECS Fargate platform `LATEST` are the dated validation seed rather than permanent patch constraints.

NFR13: The Platform Service avoids account-, Region-, repository-, and Environment-specific hardcoding.

NFR14: MVP validates one to five jobs across one non-production and one production account in the primary Region without preventing later expansion to dozens of jobs and additional account-Region Cells.

NFR15: The repository never commits Terraform state, saved plans, `.terraform/`, credentials, generated secret material, or committed `.tfvars`, and normal infrastructure workflows do not use provisioners or `null_resource`.

NFR16: Production plans, approvals, exceptions, applies, Deployment Identity, operator actions, and rollback evidence are attributable and retained under organizational policy.

NFR17: Optional views, telemetry dimensions, queues, and retention defaults have documented, configurable cost bounds within platform guardrails.

### Additional Requirements

AR1: Reconcile implementation to the adopted account-local Cell architecture: EventBridge Scheduler sends launch evidence to a policy-isolated queue, the Process Manager assumes a job-scoped launch role and calls ECS, and internal durability and DLQ queues are mandatory while consumer payload DLQs remain deferred.

AR2: Each AWS account-Region pair has one independently deployable shared Platform Cell; Cell and per-job modules and states are separate, and consumers discover a versioned SSM Cell Contract rather than reading platform Terraform state.

AR3: An independent EventBridge-rule-driven Occurrence Materializer creates `EXPECTED` occurrences at least 24 hours ahead from immutable normalized schedule generations; the supported recurring schedule subset requires conformance fixtures and one-time schedules are excluded.

AR4: `occurrence/v1` is a SHA-256 identity over exact canonical UTF-8 bytes containing job ID, schedule generation, and Unix epoch minute; Scheduler and materializer must match published test vectors and the Process Manager recomputes identity.

AR5: All evidence, CONFIG, state, commands, and alerts use checked-in versioned schemas and canonical encodings; source-specific normalizers derive authority from authenticated AWS metadata and reject caller-stamped identity.

AR6: Secret-free, content-addressed CONFIG is written to a job-scoped encrypted and versioned S3 inbox, validated and copied by the Cell to a separate immutable registry, and hash-verified before launch; job apply roles cannot write registry or ledger tables.

AR7: One Process Manager is the only runtime-ledger writer and uses a deterministic commutative reducer; checked-in transition fixtures prove bounded permutations of deduplicated evidence converge.

AR8: MVP permits exactly one platform ECS attempt per occurrence. Attempt zero, exact CONFIG, stable client token, first-request time, and a conservative retry deadline are reserved transactionally; unresolved launch uncertainty becomes `AMBIGUOUS` rather than another `RunTask` call.

AR9: Authoritative task and log correlation derives from AWS task events, task-ARN ledger mappings, and AWS-generated log subscription metadata. Application IDs are assertions, and early events remain orphan evidence until mapped.

AR10: A durable deadline scanner uses a watermark, bounded lookback, base-table verification, and repeated reconciliation so eventual GSI propagation cannot permanently skip a deadline.

AR11: SQS/Lambda integrations use partial-batch responses, `maxReceiveCount >= 5`, validated visibility-timeout relationships, 14-day retention, encryption, DLQs, quarantine behavior, bounded retries, and a processed canary heartbeat.

AR12: Scheduler delivery, materializer, normalizer, Process Manager, command handler, job launch, ECS execution, application task, plan, apply, operator, and break-glass roles remain separate with exact trust and authority; source-account/source-ARN confused-deputy protections have named positive and negative fixtures.

AR13: Platform Lambdas remain outside consumer VPCs and have no inbound public interface. ECS task security groups have no ingress and only approved SG, prefix-list, or CIDR egress; unrestricted Internet egress is a blocking production exception.

AR14: Occurrence ID is never a metric dimension. Bounded dimensions are used, terminal state and alert outbox are committed transactionally, and Alert Router delivery is reconciled and deduplicated in a separate notification ledger.

AR15: The JSON-Schema-validated Cell Contract publishes Cell/account/Region identity, semantic version, integration ARNs, supported ranges, metric namespace, encryption reference, and checksum; consumers validate identity and compatibility.

AR16: GitHub OIDC uses an immutable custom subject with repository IDs, deployment Environment, and full-SHA workflow reference, exact audience, separate plan/apply subjects, protected Environments, required reviewers, self-review prevention, restricted refs, and no administrator bypass.

AR17: Module, workflow, Actions, provider, runtime, image, and dependency inputs use immutable versions or digests. Managed-runtime exceptions are explicit, tested, and recorded in Deployment Identity.

AR18: Schedule expression or time-zone changes use two production applies: disable and drain the old generation, then publish a future-anchored generation, verify its horizon, and enable the same generation.

AR19: Initial creation and launch-relevant changes follow the `RESERVED`, `PUBLISHED`, `VALIDATED`, `MATERIALIZED`, `ENABLED`, and `REJECTED` handshake; phase two enables only the exact acknowledged generation.

AR20: A Platform namespace registry reserves canonical job IDs and binds namespace ownership to immutable repository, root, apply role, account, Region, owner, IAM Role ID, and schedule ARN; unauthorized claims and transfers fail.

AR21: Canonical identity and protected tags follow architecture rules; all persisted operational data is encrypted; default retention is 90-day production logs/occurrences, 30-day non-production logs, 35-day ledger PITR, and 14-day queues pending reviewer confirmation.

AR22: Every integration edge has one Terraform owner and is documented in `contracts/`, including schemas, identity vectors, state permutations, IAM edges, queue/Lambda bounds, metrics/alerts, OIDC rendering, and compatibility matrices.

AR23: Cell/module/runtime evolution follows expand-migrate-contract; current and previous majors interoperate through the longest queue, replay, runtime, retention, and rollback horizon, with a stable Process Manager principal within a major.

AR24: Only a lifecycle principal may garbage-collect CONFIG, task-definition, schema, or runtime versions after proving they are unreferenced across active, replayable, and rollback horizons.

AR25: Production DynamoDB uses PITR. Cell recovery restores to new tables, switches versioned aliases and contract pointers, replays evidence, rebuilds expectations, reconciles nonterminal occurrences, and verifies alerts before launch resumes; measured RPO/RTO are pilot gates.

AR26: Manual reruns, replay, disablement, and recovery use authenticated commands. Synthetic reruns use `occurrence/manual/v1` and retain actor, approval, reason, Deployment Identity, verification, and compensation evidence; users cannot supply occurrence IDs or arbitrary evidence.

AR27: Cell health covers horizon freshness, evaluator conformance, queues/DLQs, Lambda health, deadline lag, log subscriptions, canary, and outbox reconciliation; Cell incidents notify Platform once while distinct occurrence failures notify Job Owners.

AR28: Terraform state uses encrypted, versioned, public-blocked S3 backends with native lock files and path-scoped IAM. Production verifies committed provider locks read-only and applies the exact approved saved plan.

AR29: Production acceptance includes IAM-negative, schedule-conformance, state-permutation, crash-idempotency, task-correlation, namespace, evidence-forgery, failure-injection, alert-delivery, rollback, and Cell-recovery tests.

AR30: The greenfield structural seed includes `modules/ecs-scheduled-job-platform/`, `modules/ecs-scheduled-job/`, module-local `examples/basic/`, runtime packages, `contracts/`, integration and failure tests, and operator Runbooks.

AR31: Rollback disables launch first, retires the affected generation, drains or quarantines evidence, restores a compatible known-good Deployment Identity, safely replays evidence, verifies all operational planes, and completes required application compensation before cleanup.

AR32: Before canonical contract work begins, a bootstrap story creates the structural seed, pinned Python/runtime dependencies, Terraform module skeletons, local format/test/validate commands, dependency locks, and credential-free baseline CI. Privileged planning and deployment remain later work.

AR33: Before Cell launch and alert stories require deployed job artifacts, an explicit Cell fixture/canary story supplies the minimum registered job, CONFIG, task definition, launch role, notification sink, schedule, and heartbeat needed for independent Epic 1 acceptance.

AR34: The consumer-module epic delivers a fully working non-production job. Production activation depends explicitly on the later protected delivery, completed Runbook, readiness gate, and approvals; no Epic 2 acceptance criterion may require a future epic to pass.

AR35: Alert-outbox and notification-ledger resources are created with the first alert-routing story, and other queues, tables, or indexes are created when their access patterns are first exercised unless an explicit stable-ARN contract justifies earlier ownership.

AR36: Job-side phase-one resource and CONFIG publication work is separate from Cell-side registration, validation, acknowledgement, and rejection behavior, while preserving the exact two-phase handshake.

AR37: Release construction/publication, compatibility migration, and deprecation/retirement are independently implementable stories; operator access, Cell recovery, and lifecycle cleanup are also separate stories.

AR38: Failure qualification is split by schedule delivery, ECS launch/runtime, completion/durability, and security/recovery domains so each story is independently testable and reviewable.

AR39: Pilot automation and evidence collection are separate from externally owned launch decisions and elapsed observation. Named jobs/owners, account/Region, notification target, GitHub controls, RPO/RTO, baseline, observation window, and approvers live in an owned launch checklist with blocking resolution gates.

AR40: Terraform controls explicitly prevent committed `.tfvars`, require stable resource addresses or declared `moved`/migration guidance, validate every changed root and module-local example, and document every wildcard or standards deviation.

AR41: Private-subnet classification, qualifying IAM/networking change, pilot observation window, and similar policy terms bind to a versioned policy catalog or an explicit prerequisite with an owner and blocking resolution point.

AR42: The backlog includes concise FR, NFR, architecture, and AWS-standard traceability for load-bearing security, reliability, compatibility, recovery, and Terraform controls; FR18 includes both alert routing and consumer notification-input ownership.

### UX Design Requirements

No UX design contract was provided or required for MVP. This is an infrastructure module, runtime service, reusable workflow, and documentation product; consumer experience requirements are captured by explicit module inputs and outputs, actionable validation, executable examples, operational commands, and Runbooks.

### FR Coverage Map

FR1: Epic 2 - Declare a complete Scheduled Job through the supported module interface.

FR2: Epic 2 - Consume existing account, Region, cluster, network, notification, CI, image, and secret dependencies without duplicating them.

FR3: Epic 2 - Apply predictable resource identity and protected standard tags.

FR4: Epic 2 - Expose operational identifiers and Deployment Identity without requiring Terraform-state inspection.

FR5: Epic 2 - Provision a validated ECS Fargate task definition with immutable image identity.

FR6: Epic 2 - Provision the reviewed recurring schedule and occurrence contract through the brokered Cell delivery path.

FR7: Epic 2 - Configure and document delivery retries, at-least-once behavior, and duplicate handling.

FR8: Epic 2 - Declare completion deadlines, overlap safety, and application idempotency or locking.

FR9: Epic 2 - Perform controlled and attributable manual reruns without schedule edits.

FR10: Epic 2 - Separate schedule delivery, job launch, task execution, and application IAM authority.

FR11: Epic 2 - Declare and review least-privilege application permissions and governed attachments.

FR12: Epic 2 - Use exact approved secret references without exposing secret values.

FR13: Epic 2 - Run tasks in private subnets with bounded network access and no public IP.

FR14: Epic 2 - Retain structured occurrence-aware job logs with explicit retention.

FR15: Epic 1 - Detect and diagnose Scheduler delivery failures using the independent expectation path and Cell canary.

FR16: Epic 1 - Detect ECS launch failures, including `RunTask` response failures, start failures, unexpected stops, and non-zero exits.

FR17: Epic 1 - Correlate every expected occurrence with one authoritative completion outcome and deadline state.

FR18: Epics 1 and 2 - Route enriched occurrence alerts reliably, and supply the job-specific owner, Runbook, and notification metadata consumed by that route.

FR19: Epic 2 - Enable bounded-cost operational views without weakening required logs or alarms.

FR20: Epic 3 - Validate pull requests and trusted plans while isolating untrusted code from credentials and protected state.

FR21: Epic 3 - Enforce tested production policy gates, negative authorization checks, and governed exceptions.

FR22: Epic 3 - Authenticate trusted delivery paths using exact short-lived GitHub OIDC identities and protected targets.

FR23: Epic 3 - Separate fresh plan, approval, and exact-plan apply under controlled concurrency.

FR24: Epic 3 - Record Deployment Identity, rollback or forward-fix evidence, and post-change verification.

FR25: Epic 3 - Publish immutable releases and independently manage compatibility migration, deprecation, and retirement.

FR26: Epic 4 - Provide adoption guidance, complete interface references, security guidance, compatibility data, and executable examples.

FR27: Epic 4 - Provide and complete an actionable production Job Runbook tied to alarms and recovery controls.

FR28: Epic 4 - Enforce production readiness, failure qualification, recovery evidence, and controlled pilot launch gates.

### Story Traceability Matrix

This matrix identifies each story's primary functional coverage and its load-bearing non-functional, architecture, and AWS/Terraform controls. Acceptance criteria remain the authoritative implementation contract.

| Story | Primary FRs | Load-bearing NFRs | Architecture and AWS/Terraform controls |
|---|---|---|---|
| 1.1 | FR20, FR25, FR26 | NFR11, NFR12, NFR15 | AR30, AR32, AR40 |
| 1.2 | FR17, FR24, FR25, FR26 | NFR9, NFR10, NFR12, NFR13 | AR4, AR5, AR15, AR17, AR22, AR23, AR42 |
| 1.3 | FR6, FR17 | NFR2, NFR9, NFR13, NFR17 | AR2, AR6, AR20, AR21, AR22, AR28, AR35 |
| 1.4 | FR15, FR16, FR17, FR18 | NFR1, NFR3, NFR5, NFR6, NFR13, NFR14, NFR17 | AR12, AR13, AR21, AR27, AR33, AR35 |
| 1.5 | FR15, FR17 | NFR1, NFR2, NFR9 | AR1, AR4, AR5, AR9, AR11, AR12, AR22, AR29 |
| 1.6 | FR6, FR15, FR17 | NFR5, NFR8, NFR9, NFR17 | AR3, AR4, AR27, AR29, AR35 |
| 1.7 | FR17 | NFR1, NFR9, NFR17 | AR5, AR7, AR11, AR12, AR21, AR29, AR35 |
| 1.8 | FR16, FR17 | NFR1, NFR5, NFR9 | AR1, AR7, AR8, AR12, AR17, AR29 |
| 1.9 | FR14, FR16, FR17 | NFR2, NFR8, NFR9 | AR5, AR7, AR9, AR11, AR22, AR29, AR35 |
| 1.10 | FR15, FR16, FR17 | NFR6, NFR8, NFR9, NFR17 | AR3, AR7, AR10, AR11, AR14, AR29, AR35 |
| 1.11 | FR15, FR16, FR17, FR18 | NFR2, NFR6, NFR9, NFR16, NFR17 | AR7, AR11, AR14, AR27, AR29, AR35 |
| 1.12 | FR15, FR16, FR17, FR18 | NFR6, NFR8, NFR17 | AR11, AR14, AR27, AR29 |
| 1.13 | FR9, FR17 | NFR1, NFR2, NFR16 | AR12, AR26, AR29, AR31, AR37 |
| 1.14 | FR17, FR24, FR28 | NFR7, NFR9, NFR16 | AR23, AR25, AR26, AR29, AR31, AR37 |
| 1.15 | FR25 | NFR7, NFR10, NFR16, NFR17 | AR21, AR23, AR24, AR31, AR37 |
| 2.1 | FR1, FR2, FR3, FR7, FR8, FR18 | NFR5, NFR10, NFR13, NFR15 | AR15, AR18, AR19, AR20, AR21, AR36, AR40, AR41 |
| 2.2 | FR10, FR11, FR12 | NFR1, NFR2 | AR6, AR12, AR20, AR29, AR40, AR41 |
| 2.3 | FR2, FR13 | NFR3, NFR13, NFR17 | AR13, AR21, AR22, AR40, AR41 |
| 2.4 | FR4, FR5, FR12, FR14 | NFR2, NFR8, NFR10, NFR11, NFR17 | AR9, AR14, AR17, AR21, AR30, AR40 |
| 2.5 | FR6, FR10 | NFR1, NFR2, NFR7, NFR9, NFR13 | AR1, AR6, AR18, AR19, AR20, AR22, AR36 |
| 2.6 | FR6, FR7, FR8 | NFR5, NFR9, NFR10, NFR13 | AR3, AR4, AR6, AR15, AR18, AR19, AR20, AR22, AR36, AR41 |
| 2.7 | FR6, FR7, FR8, FR14 | NFR5, NFR7, NFR8, NFR9, NFR16 | AR3, AR18, AR19, AR26, AR31, AR34 |
| 2.8 | FR14, FR17, FR18 | NFR2, NFR6, NFR8, NFR9, NFR17 | AR5, AR9, AR14, AR15, AR27, AR34 |
| 2.9 | FR4, FR19 | NFR6, NFR9, NFR17 | AR14, AR15, AR17, AR27, AR34 |
| 2.10 | FR9 | NFR5, NFR7, NFR9, NFR16 | AR8, AR26, AR31, AR34 |
| 3.1 | FR20, FR21, FR25, FR26 | NFR2, NFR4, NFR11, NFR12, NFR15 | AR17, AR22, AR28, AR30, AR32, AR40, AR42 |
| 3.2 | FR22 | NFR1, NFR4, NFR13, NFR16 | AR12, AR16, AR17, AR28, AR41 |
| 3.3 | FR20, FR22, FR23 | NFR2, NFR4, NFR7, NFR15, NFR16 | AR16, AR17, AR28, AR40 |
| 3.4 | FR21 | NFR1, NFR2, NFR3, NFR4, NFR6, NFR16 | AR12, AR13, AR16, AR17, AR28, AR29, AR40, AR41 |
| 3.5 | FR23 | NFR4, NFR7, NFR16 | AR16, AR18, AR19, AR28, AR31, AR39, AR41 |
| 3.6 | FR24 | NFR7, NFR16 | AR17, AR18, AR19, AR23, AR28, AR31 |
| 3.7 | FR25 | NFR7, NFR10, NFR11, NFR12, NFR16 | AR17, AR22, AR23, AR29, AR37 |
| 3.8 | FR25 | NFR7, NFR10, NFR16 | AR18, AR23, AR25, AR31, AR37, AR40 |
| 3.9 | FR25 | NFR7, NFR10, NFR16, NFR17 | AR23, AR24, AR37, AR40 |
| 4.1 | FR26 | NFR1, NFR2, NFR10, NFR11, NFR12, NFR13, NFR15, NFR17 | AR15, AR17, AR21, AR22, AR26, AR28, AR30, AR40, AR42 |
| 4.2 | FR27 | NFR2, NFR6, NFR7, NFR16 | AR26, AR27, AR31, AR39, AR41 |
| 4.3 | FR28 | NFR1, NFR2, NFR3, NFR4, NFR6, NFR7, NFR8, NFR16 | AR16, AR17, AR19, AR21, AR22, AR28, AR29, AR39, AR40, AR41, AR42 |
| 4.4 | FR15, FR17, FR28 | NFR5, NFR6, NFR8, NFR9, NFR14, NFR17 | AR3, AR4, AR10, AR11, AR18, AR27, AR29, AR38 |
| 4.5 | FR16, FR17, FR28 | NFR5, NFR6, NFR8, NFR9, NFR14, NFR17 | AR7, AR8, AR9, AR10, AR11, AR29, AR38 |
| 4.6 | FR15, FR16, FR17, FR18, FR28 | NFR5, NFR6, NFR8, NFR9, NFR14, NFR17 | AR7, AR9, AR10, AR11, AR14, AR27, AR29, AR35, AR38 |
| 4.7 | FR10, FR11, FR12, FR13, FR20, FR21, FR22, FR23, FR28 | NFR1, NFR2, NFR3, NFR4, NFR13, NFR15, NFR16 | AR5, AR6, AR12, AR13, AR16, AR20, AR28, AR29, AR38, AR40, AR41 |
| 4.8 | FR9, FR17, FR24, FR28 | NFR7, NFR9, NFR16 | AR23, AR25, AR26, AR29, AR31, AR38, AR39 |
| 4.9 | FR28 | NFR6, NFR7, NFR14, NFR16, NFR17 | AR29, AR39, AR41, AR42 |
| 4.10 | FR28 | NFR6, NFR7, NFR14, NFR16 | AR16, AR29, AR31, AR39, AR41, AR42 |

## Epic List

### Epic 1: Prove a Trusted Regional Job Platform

Platform Engineering and on-call engineers can bootstrap, deploy, exercise, observe, and recover an account-Region Platform Cell using a platform-owned canary that proves occurrence tracking and failure delivery end to end.

**FRs covered:** FR15, FR16, FR17, FR18

**Implementation notes:** This epic owns the greenfield structural seed, credential-free baseline validation, Compatibility Package, minimum registered canary job and notification fixtures, Cell runtime, occurrence ledger, alert path, operator controls, recovery, and version lifecycle. Cell resources are created with the first story that exercises their access pattern unless a stable contract requires earlier ownership. No Epic 2 job artifact is required to accept this epic.

### Epic 2: Run a Secure Scheduled Job in Non-Production

Application teams can declare, deploy, observe, disable, and safely rerun a private ECS Fargate scheduled job through the standard module in non-production.

**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8, FR9, FR10, FR11, FR12, FR13, FR14, FR18, FR19

**Implementation notes:** This epic owns the consumer module, job identity, IAM, task definition, networking, logs, schedule, CONFIG publication and acknowledgement, occurrence correlation, outputs, dashboards, and non-production rerun path. Job-side phase-one publication and Cell-side registration/validation are separate implementation units. The epic does not claim production readiness or depend on production workflows, protected approvals, or a completed production Runbook.

### Epic 3: Deliver and Evolve Jobs Through Governed Automation

Platform reviewers and deployers can validate changes, bind trusted targets, enforce policy, create and approve exact plans, apply through protected controls, record Deployment Identity, and publish compatible immutable releases.

**FRs covered:** FR20, FR21, FR22, FR23, FR24, FR25

**Implementation notes:** This epic uses the working Cell and non-production job fixtures from Epics 1 and 2 to prove credential-free validation, trusted planning, exact OIDC binding, protected apply, state isolation, policy enforcement, Deployment Identity, and rollback. Release construction/publication, compatibility migration, and deprecation/retirement are separate units. Production activation remains fail-closed until the Epic 4 Runbook and readiness evidence exist.

### Epic 4: Qualify and Adopt the Production Standard

Job Owners, Platform Engineering, Security, and operations can document, qualify, approve, and evaluate real production jobs using complete Runbooks, readiness evidence, failure qualification, rollback rehearsal, and a controlled pilot launch package.

**FRs covered:** FR26, FR27, FR28

**Implementation notes:** This epic completes adoption documentation, module-local examples, Runbooks, machine-verifiable readiness, split failure-domain qualification, recovery evidence, and pilot measurement automation. Named jobs and owners, account and Region, notification target, GitHub controls, recovery objectives, baseline, observation window, and stakeholder approvals remain explicit launch-checklist gates with owners and resolution points rather than hidden development acceptance criteria.

## Epic 1: Prove a Trusted Regional Job Platform

Platform Engineering and on-call engineers can bootstrap, deploy, exercise, observe, and recover an account-Region Platform Cell using a platform-owned canary that proves occurrence tracking and failure delivery end to end.

### Story 1.1: Bootstrap the Greenfield Platform Repository

As a Platform Engineering contributor,
I want a reproducible repository seed with credential-free validation,
So that every later platform story starts from the same reviewable structure and toolchain.

**Acceptance Criteria:**

**Given** the repository has no established platform implementation structure
**When** the bootstrap is created
**Then** it contains `modules/ecs-scheduled-job-platform/`, `modules/ecs-scheduled-job/`, module-local `examples/basic/`, `runtime/`, `contracts/`, `tests/contract/`, `tests/integration/`, and operator Runbook locations consistent with the architecture seed
**And** each Terraform module contains documented `main.tf`, `variables.tf`, `outputs.tf`, and `versions.tf` skeletons that validate without creating production resources.

**Given** Terraform is the required infrastructure tool
**When** module and example version constraints are inspected
**Then** they require Terraform `>= 1.10, < 2.0`, declare the approved AWS provider constraint, and distinguish the dated validation seed from permanent patch constraints
**And** backend-free initialization and validation can run independently for every module and module-local example.

**Given** Python is used for Cell runtime components and validation tooling
**When** runtime packaging is initialized
**Then** the repository declares Python 3.14 compatibility, pinned direct dependencies, a reproducible dependency lock, typed package boundaries, and test discovery for each runtime package
**And** no runtime package contains account-, Region-, Environment-, credential-, or secret-specific defaults.

**Given** a contributor needs one repeatable local validation entry point
**When** the documented command is run from a clean checkout
**Then** it executes formatting checks, Terraform initialization without backends, validation for each changed module and example, contract tests, runtime tests, and repository hygiene checks
**And** failures identify the exact module, example, package, or policy that needs correction.

**Given** a pull request changes bootstrap-controlled files
**When** baseline GitHub Actions validation runs
**Then** it executes the same credential-free checks with minimal read-only `GITHUB_TOKEN` permissions and no AWS credentials, protected state, deployment Environment, or production secret access
**And** forked or otherwise untrusted pull requests cannot pass data or executable artifacts into a privileged job.

**Given** prohibited repository artifacts are introduced
**When** hygiene validation runs
**Then** committed `.tfvars`, Terraform state, saved plans, `.terraform/`, credentials, private keys, generated secret material, and unapproved local configuration are rejected
**And** `.gitignore`, scanning fixtures, and contributor documentation identify the prohibited patterns without containing real secrets.

**Given** later Terraform work changes resource addresses or module structure
**When** contributors follow the bootstrap contribution contract
**Then** stable Terraform addresses are required and address changes must include reviewed `moved` blocks or explicit migration guidance
**And** routine provisioners, `null_resource`, mutable production references, and undocumented standards deviations are prohibited.

**Given** the bootstrap checks run successfully
**When** their output is reviewed
**Then** the repository reports the tested Terraform, provider, and Python toolchain versions and produces no state, saved plan, credential, or deployment artifact
**And** the documented rollback is removal or reversion of the seed files because this story creates no AWS resources.

### Story 1.2: Publish Canonical Compatibility Contracts

As a Platform Engineering contributor,
I want a versioned Compatibility Package for every Cell integration boundary,
So that independently implemented Terraform and runtime components cannot disagree on identity, schemas, state, IAM, or compatibility.

**Acceptance Criteria:**

**Given** the repository seed from Story 1.1
**When** the Compatibility Package is published
**Then** `contracts/` contains versioned JSON Schemas for the Cell Contract, CONFIG, authenticated evidence envelope, occurrence and task-attempt records, completion signal, command, alert, and deployment identity
**And** schemas reject missing required fields, unsupported majors, malformed identifiers, noncanonical timestamps, and fields capable of carrying secret values.

**Given** the `occurrence/v1` identity contract
**When** identity vectors are evaluated
**Then** fixtures define the exact UTF-8 bytes and lowercase SHA-256 result for canonical job ID, schedule generation, and Unix epoch minute
**And** they cover valid adjacent occurrences, invalid job IDs, byte-normalization differences, daylight-saving boundaries, and mismatched hashes.

**Given** evidence can arrive duplicated, delayed, or out of order
**When** reducer fixtures execute
**Then** every bounded permutation of the same immutable deduplicated evidence converges on the documented `EXPECTED`, `STARTED`, `SUCCEEDED`, `FAILED`, `OVERDUE`, `MISSED`, or `AMBIGUOUS` result
**And** no late, duplicate, wrong-occurrence, or conflicting signal silently overwrites a terminal result.

**Given** the materializer and EventBridge Scheduler must interpret one recurring schedule contract
**When** schedule fixtures are evaluated
**Then** they define the supported cron/rate grammar, IANA time zones, explicit start anchors, activation windows, disabled flexible windows, daylight-saving behavior, generation hashing, and consecutive-window expectations
**And** one-time schedules, unsupported syntax, ambiguous anchors, and divergent occurrence calculations fail deterministically.

**Given** Cell and job roots have separate owners and IAM boundaries
**When** the integration and IAM catalogs are reviewed
**Then** every cross-root ARN, resource-policy principal, evidence type, role assumption, `RunTask`, `PassRole`, queue, CONFIG, metric, alert, and lifecycle handoff has one owner and explicit allowed authority
**And** named positive and negative fixtures cover source-account/source-ARN confused-deputy conditions, cross-producer forgery, cross-job access, stale roles, boundary removal, and unrelated role passing.

**Given** SQS and Lambda integrations must remain safe under retry
**When** runtime constraint fixtures are evaluated
**Then** they validate message size, batch size, function timeout, batch window, queue visibility, concurrency, `maxReceiveCount >= 5`, 14-day retention, partial-batch failure behavior, DLQ handling, and bounded retry rules
**And** invalid combinations fail before deployment.

**Given** Cell and consumer versions evolve independently
**When** compatibility validation runs
**Then** the package declares supported Cell, module, CONFIG, evidence, runtime, workflow, and Terraform ranges for the current and previous major through the required replay and rollback horizon
**And** unsupported or unknown major combinations fail with an actionable migration reference.

**Given** a contract, catalog, or fixture changes
**When** credential-free repository validation runs
**Then** schema tests, identity vectors, schedule fixtures, reducer permutations, IAM cases, queue constraints, ownership checks, and compatibility matrices execute from the same package
**And** breaking changes require a major-version classification and migration note without network access, AWS credentials, account-specific values, or plaintext secrets.

### Story 1.3: Deploy Cell Registration and Discovery Foundations

As a Platform Engineer,
I want an encrypted account-Region foundation for job ownership, immutable configuration, and Cell discovery,
So that jobs can register safely without accessing platform Terraform state or premature runtime resources.

**Acceptance Criteria:**

**Given** an approved AWS account, Region, Environment, encryption configuration, retention policy, and standard tags
**When** the Platform Cell module is planned
**Then** it creates only account- and Region-local registration, CONFIG, and discovery resources with predictable names and protected tags
**And** account IDs, Regions, Environment names, ARNs, notification targets, and KMS keys are supplied or derived rather than hardcoded.

**Given** repositories must not claim arbitrary job identities
**When** the namespace registry is created
**Then** its keys and conditional-write contract support canonical Environment/Application namespace ownership, full job reservation, immutable repository/root/apply-role binding, owner generation, transfer state, and tombstones
**And** duplicate, cross-namespace, stale-generation, and unauthorized ownership mutations are representable as deterministic conditional failures.

**Given** job roots publish secret-free CONFIG candidates
**When** the CONFIG inbox is created
**Then** it is an encrypted, versioned, public-blocked S3 bucket with job-scoped content-addressed prefixes and lifecycle rules compatible with validation, replay, investigation, and rollback horizons
**And** bucket policy denies insecure transport, unencrypted writes, noncanonical keys, cross-prefix writes, and access not derived from a registered ownership record.

**Given** validated CONFIG must be isolated from job Terraform authority
**When** the configuration registry is created
**Then** it is physically separate from namespace ownership and future occurrence state, encrypted at rest, protected by production PITR where applicable, and keyed for immutable job/config-version lookup
**And** no job, consumer workflow, or application principal can write, overwrite, or delete registry records directly.

**Given** operational metadata has bounded retention and cost requirements
**When** default lifecycle settings are applied
**Then** production and non-production retention values match the approved architecture defaults or explicit policy inputs, and destructive expiration cannot remove referenced CONFIG
**And** invalid, unbounded, or policy-incompatible values fail planning with an actionable message.

**Given** consumers must discover the Cell without cross-repository state coupling
**When** the foundation is applied
**Then** it publishes a JSON-Schema-valid SSM Cell Contract at the canonical Environment/Region path with Cell, account, Region, semantic version, available resource identifiers, supported contract ranges, metric namespace reservation, encryption reference, and checksum
**And** consumers can validate identity and compatibility without `terraform_remote_state` or direct platform-state access.

**Given** later stories add runtime integrations to the Cell
**When** the Cell Contract evolves
**Then** additions preserve its stable address, schema versioning, checksum rules, and backward-compatible discovery behavior
**And** any Terraform resource-address change includes a reviewed `moved` block or explicit migration procedure.

**Given** this foundation is changed
**When** repository validation runs
**Then** the Cell module and `modules/ecs-scheduled-job-platform/examples/basic` pass formatting, backend-free initialization, validation, contract tests, and security scans covering encryption, public access, tags, PITR, retention, policy scope, and state separation
**And** tests confirm that runtime ledger, alert outbox, notification ledger, and unused producer queues are not created by this story.

**Given** a foundation deployment must be rolled back
**When** the documented rollback is followed
**Then** the previous compatible module version and Cell Contract can be restored without deleting ownership or CONFIG evidence
**And** production data resources use deletion protection or equivalent safeguards so rollback does not become destructive cleanup.

### Story 1.4: Register a Platform-Owned Canary Job

As a Platform On-call Engineer,
I want a low-risk platform-owned canary registered with the Cell before runtime processing is built,
So that every later delivery, launch, completion, alert, and recovery capability has a concrete end-to-end acceptance fixture.

**Acceptance Criteria:**

**Given** a disposable non-production account-Region Cell and approved existing ECS cluster, private subnets, security groups, and immutable canary image digest
**When** the canary fixture root is planned
**Then** it creates only canary-owned task, IAM, logging, schedule, CONFIG, and test-notification resources outside customer workloads
**And** account, Region, cluster, network, image, and ownership values are explicit inputs rather than repository defaults.

**Given** the canary needs a canonical identity
**When** its reservation is submitted through the platform-owned registration path
**Then** the namespace registry binds the canary job ID to its fixture repository/root, apply identity, account, Region, Environment, owner, and ownership generation
**And** duplicate, cross-namespace, stale-generation, and substituted-root reservations fail while an identical retry is idempotent.

**Given** later launch-role trust requires a stable Process Manager identity
**When** the canary foundation is applied
**Then** the Cell creates the boundary-constrained stable Process Manager role shell for the Cell major with no ECS launch authority yet
**And** creating this identity early is documented as the stable-principal exception required to bind the canary launch-role trust without later replacement.

**Given** the canary task resources are created
**When** IAM and task-definition configuration are inspected
**Then** job-launch, ECS execution, and application task roles are separate; the image is immutable; CPU and memory are explicit; logs have bounded retention; and application permissions are empty by default
**And** trust policies use exact service principals, source-account/source-resource conditions where supported, permissions boundaries, and no unjustified wildcard authority.

**Given** Scheduler launch evidence needs its first concrete destination
**When** the canary schedule is created
**Then** the Cell owns an encrypted Scheduler source queue and DLQ, while the canary root owns a disabled recurring schedule and a delivery role scoped to those exact queues with source-account and schedule-group protections
**And** retry attempts, maximum event age, disabled flexible window, time zone, future activation anchor, and canonical scheduled-time payload are explicit.

**Given** all canary launch inputs are known
**When** the fixture publishes CONFIG
**Then** it writes one secret-free, content-addressed candidate to the canary's exact S3 inbox prefix containing task revision, cluster, private networking, roles, schedule generation, runtime deadline, log group, test notification metadata, and Deployment Identity
**And** the lifecycle remains `PUBLISHED` with launch disabled until later Cell validation and materialization succeed.

**Given** the canary needs a safe alert destination
**When** fixture notification resources are created
**Then** they use a non-production test sink that records delivery evidence without contacting production on-call or customer integrations
**And** the sink ARN is registered as canary metadata without granting arbitrary publish access.

**Given** the canary schedule remains disabled
**When** the fixture is applied and validated
**Then** no ECS task launches and no occurrence is falsely reported as successful
**And** outputs expose the canary job ID, ownership generation, task revision, role identities, log group, schedule ARN, CONFIG hash, source queue, notification sink, and current lifecycle state without secret values.

**Given** canary fixture security tests run
**When** unauthorized repository, stale role, wrong account, public subnet, public IP, mutable image, cross-prefix CONFIG write, broad `PassRole`, or direct ledger write is attempted
**Then** every attempt fails before launch
**And** the compliant fixture passes module validation and can be destroyed without deleting shared Cell registration or CONFIG evidence required by investigation.

### Story 1.5: Authenticate and Normalize Platform Evidence

As a Platform Security Engineer,
I want Scheduler evidence authenticated and normalized before it reaches occurrence processing,
So that an event body cannot forge producer, job, generation, or authorization identity.

**Acceptance Criteria:**

**Given** the canary Scheduler source queue from Story 1.4
**When** the normalizer integration is deployed
**Then** it creates an encrypted canonical ingress queue, ingress DLQ, and bounded quarantine path that satisfy the Compatibility Package's retention, visibility, batch, retry, and payload constraints
**And** materializer, ECS, completion-log, and command source queues are not created until their producer stories use them.

**Given** Scheduler sends launch evidence through its dedicated delivery role
**When** the normalizer receives the SQS record
**Then** producer authority is derived from queue ARN, SQS sender identity or IAM Role ID, registered schedule ARN, account, Region, job ownership generation, and permitted evidence type
**And** job ID, producer ID, source ARN, generation, and authorization fields in the message body are treated only as assertions to compare.

**Given** source identity and payload assertions agree with the registry and schema
**When** normalization succeeds
**Then** the normalizer emits one versioned canonical envelope containing Cell-stamped producer identity, producer event ID, event type, job, CONFIG version, generation, scheduled time, recomputed Occurrence ID, emitted time, payload hash, and trace context
**And** the envelope is secret-free and conforms to the Story 1.2 schema before entering canonical ingress.

**Given** a message contains a forged job, producer, evidence type, schedule ARN, scheduled time, generation, Occurrence ID, stale Role ID, or cross-account sender
**When** the normalizer evaluates it
**Then** it is rejected without writing platform state, invoking ECS, or forwarding canonical evidence
**And** a sanitized rejection record and bounded security metric are retained without secret values or unbounded metric dimensions.

**Given** a batch contains valid, transiently failing, and invalid messages
**When** processing completes
**Then** Lambda partial-batch responses acknowledge successful records, retry only transient failures, and route poison records through the configured redrive or quarantine path
**And** one malformed record cannot block unrelated Scheduler evidence.

**Given** the normalizer role is analyzed
**When** IAM-positive and IAM-negative tests run
**Then** it can read only the registered Scheduler source queue and write only canonical ingress, its own logs, and approved bounded metrics
**And** it cannot write namespace, CONFIG, occurrence, or alert data; assume job launch roles; call ECS; pass roles; change queue policies; or read another source queue.

**Given** the shared normalizer runtime is deployed
**When** networking and logging controls are inspected
**Then** it remains outside consumer VPCs, has no inbound public interface, uses regional AWS APIs, and writes structured secret-free logs with explicit retention
**And** timeouts, reserved concurrency, event-source batch settings, and queue visibility satisfy the published constraints.

**Given** the normalizer code, schema, or integration changes
**When** repository and disposable-Cell tests run
**Then** they cover valid launch evidence, duplicate delivery, malformed schema, forged fields, stale registration, source-account/source-ARN mismatch, partial batches, poison records, and replay
**And** identical valid source events normalize deterministically while unsupported schema majors fail before side effects.

### Story 1.6: Materialize Future Expected Occurrences

As an On-call Engineer,
I want expected canary occurrences generated independently before Scheduler delivery,
So that a missing Scheduler invocation remains observable as a specific occurrence failure.

**Acceptance Criteria:**

**Given** the canary has a `PUBLISHED` CONFIG candidate
**When** the materializer validates it
**Then** schema, canonical content hash, Cell identity, namespace ownership, bound Role ID and schedule ARN, task revision, cluster, private networking, log group, notification metadata, runtime deadline, and supported contract ranges are verified
**And** invalid, stale, substituted, secret-bearing, or incompatible candidates become `REJECTED` with a sanitized reason while launch remains disabled.

**Given** a CONFIG candidate passes validation
**When** the materializer records it
**Then** an immutable snapshot is copied into the separate configuration registry and lifecycle state becomes `VALIDATED`
**And** the canonical body hash equals `config_version`, prior versions are not overwritten, and the job root receives no registry-write authority.

**Given** materializer evidence is produced for the first time
**When** Cell resources are planned
**Then** an encrypted materializer source queue and DLQ are created with the published retention, visibility, retry, partial-batch, and quarantine constraints
**And** the normalizer gains only the source-specific read and identity-mapping rules needed to convert materializer evidence into canonical ingress.

**Given** a validated recurring schedule generation
**When** the materializer evaluates it
**Then** expression, IANA time zone, start anchor, activation window, disabled flexible window, schedule generation, and daylight-saving behavior match the Compatibility Package
**And** unsupported syntax, one-time schedules, ambiguous anchors, divergent fixture results, or occurrences outside the activation window are rejected.

**Given** the account-local EventBridge rule invokes the materializer
**When** the expectation horizon is advanced
**Then** deterministic `EXPECTED` evidence is emitted for every canary occurrence at least 24 hours ahead with the exact canonical scheduled time and `occurrence/v1` identity
**And** repeated or overlapping invocations reuse deterministic producer event IDs so duplicate delivery represents one logical occurrence.

**Given** Scheduler and the materializer evaluate the same canary generation
**When** the conformance suite compares their outputs
**Then** occurrence times and IDs agree for supported cron/rate schedules, time zones, daylight-saving boundaries, activation anchors, and consecutive windows
**And** any divergence blocks the canary from reaching `MATERIALIZED`.

**Given** a complete future horizon exists in emitted and acknowledged evidence
**When** materialization status is recorded
**Then** the registry stores the generation, horizon watermark, conformance result, CONFIG hash, validation timestamp, and lifecycle state `MATERIALIZED`
**And** this state does not enable the Scheduler or claim that occurrence state has been written before Story 1.7.

**Given** the horizon stops advancing or approaches exhaustion
**When** materializer health is evaluated
**Then** bounded freshness and conformance metrics identify the Cell, Environment, account, Region, and failure plane without Occurrence ID dimensions
**And** the signals are available to the Cell alarm story before the verified horizon can expire.

**Given** materializer IAM is analyzed
**When** positive and negative tests run
**Then** it can read canary inbox candidates and active registry CONFIG, write only verified registry records, and send only materializer evidence to its exact source queue
**And** it cannot write occurrence state, consume canonical ingress, assume launch roles, call ECS, change schedules, publish alerts, or read another job's prefix.

**Given** materialization is tested in a disposable Cell
**When** valid, duplicate, partial-failure, stale-generation, hash-mismatch, unsupported-schedule, DST, stopped-horizon, and incompatible-version cases execute
**Then** valid expectations reach canonical ingress deterministically and invalid candidates cause no launch or occurrence mutation
**And** the canary remains disabled until a later story records and validates occurrence state.

### Story 1.7: Record Deterministic Occurrence State

As an On-call Engineer,
I want one authoritative processor to record expected occurrences deterministically,
So that retries and reordered evidence cannot corrupt or duplicate the Cell's operational truth.

**Acceptance Criteria:**

**Given** canonical ingress contains valid `EXPECTED` evidence
**When** the Process Manager consumes it
**Then** it verifies the envelope schema and supported major, recomputes Occurrence ID, resolves the exact immutable CONFIG, and verifies its canonical hash
**And** unknown jobs, unsupported versions, inactive generations, mismatched CONFIG, or identity disagreement cause no ledger mutation.

**Given** occurrence state is written for the first time
**When** Cell resources are planned
**Then** an encrypted occurrence ledger is created with production PITR, protected retention, canonical occurrence and processed-event keys, and only the access patterns required by this story
**And** task-ARN indexes, deadline indexes, alert-outbox items, and notification-ledger resources are not created until their first consuming stories.

**Given** one valid expected event is accepted
**When** the Process Manager commits it
**Then** one conditional DynamoDB transaction records the immutable processed event and creates or reduces the canonical occurrence to `EXPECTED` with job, generation, CONFIG, scheduled time, deadline, and evidence provenance
**And** the same producer event ID cannot be accepted twice.

**Given** the same logical expectation arrives more than once or in a different delivery order
**When** the reducer evaluates all accepted evidence
**Then** the occurrence remains one logical record with the same state and audit history
**And** no duplicate delivery creates another occurrence, changes its immutable coordinates, or extends its deadline.

**Given** evidence permitted by the Compatibility Package arrives before its live producer integration exists
**When** reducer unit tests execute
**Then** all published state-permutation fixtures converge on their documented state without arrival-order dependence
**And** runtime wiring accepts only producer types registered by completed stories, so fixture coverage does not grant premature live authority.

**Given** malformed, unauthorized, poison, or transiently failing canonical records are processed in one batch
**When** the invocation completes
**Then** partial-batch handling retries only transient failures, rejects deterministic contract failures, and redrives poison records without blocking valid expectations
**And** unsupported or quarantined evidence is retained with a stable machine code and secret-free operator message.

**Given** the Process Manager role shell from Story 1.4 is activated
**When** its effective authority is analyzed
**Then** it can consume canonical ingress, read verified CONFIG, conditionally write only occurrence and processed-event records, publish bounded metrics, and write its own retained logs
**And** it still cannot call ECS, assume job launch roles, create task attempts, change CONFIG or schedules, write alert records, pass roles, or alter its authorization path.

**Given** an operator queries a canary occurrence
**When** supported operational output or diagnostic tooling is used
**Then** the operator can retrieve state, scheduled time, completion deadline, CONFIG version, evidence provenance, and last reduction time without direct Terraform-state access
**And** secret values, raw CONFIG bodies, and unrestricted evidence payloads are excluded.

**Given** ledger or Process Manager changes are validated
**When** contract, unit, IAM-negative, retry, and disposable-Cell tests run
**Then** they cover first expectation, duplicates, reordered delivery, wrong identity, stale CONFIG, unsupported schema, conditional conflicts, partial batches, and restart after transaction commit
**And** the canary's materialized expectations become queryable while Scheduler remains disabled and no ECS task launches.

### Story 1.8: Launch Exactly One Canary Task per Occurrence

As a Job Owner,
I want each valid canary occurrence to launch no more than one ECS task,
So that Scheduler retries or Process Manager crashes cannot create duplicate workload effects.

**Acceptance Criteria:**

**Given** the canary generation is `MATERIALIZED` and its expected occurrences are queryable
**When** controlled non-production activation is planned
**Then** preconditions require the exact acknowledged CONFIG hash, schedule ARN, Role ID, ownership generation, activation anchor, and horizon watermark
**And** changed, stale, rejected, incompatible, or insufficient-horizon acknowledgements keep the schedule disabled.

**Given** activation preconditions pass
**When** the canary schedule is enabled at its reviewed anchor
**Then** Scheduler sends `LAUNCH` evidence through the existing authenticated source path rather than invoking ECS directly
**And** the same canonical scheduled time reduces to the same Occurrence ID already created by the materializer.

**Given** canonical `EXPECTED` and `LAUNCH` evidence exist for an eligible occurrence
**When** the Process Manager prepares launch
**Then** it revalidates the exact immutable CONFIG and transactionally reserves task attempt zero, deterministic client token, first-request time, conservative retry deadline, and launch-pending state
**And** concurrent, duplicate, or reordered launch evidence cannot reserve another task attempt.

**Given** attempt zero is reserved
**When** the Process Manager invokes ECS
**Then** it assumes only the canary's bound launch role and calls `RunTask` with the exact task revision, cluster, private subnets, security groups, public-IP-disabled configuration, capacity settings, and runtime deadline from verified CONFIG
**And** it supplies reserved job, occurrence, CONFIG, attempt, and Deployment Identity values through platform-owned task tags and container overrides.

**Given** ECS accepts the task
**When** the response is recorded
**Then** the task ARN is conditionally indexed to the reserved occurrence and attempt, and the ledger retains launch timing, task revision, client token, role identity, and Deployment Identity
**And** the task-ARN access pattern is introduced with this story without accepting identity from application output.

**Given** ECS returns an HTTP error or HTTP 200 with a non-empty `failures[]` and no task
**When** the response is processed
**Then** the occurrence reduces to `FAILED` with a stable sanitized launch-failure code and reason
**And** failure evidence is durable even though no ECS task exists to emit a lifecycle event.

**Given** the Process Manager crashes after ECS accepts launch but before task mapping commits
**When** canonical ingress retries the same evidence
**Then** the same client token is reused and the original task is reconciled by cluster, Cell tags, and `startedBy=occurrence_id`
**And** exactly one matching task repairs the mapping without another logical launch.

**Given** launch outcome remains unresolved or conflicts
**When** the conservative safe-retry deadline passes, multiple task ARNs are found, parameters differ, or the token conflicts
**Then** the Process Manager makes no further `RunTask` call and reduces the occurrence to `AMBIGUOUS`
**And** recovery requires a separately authorized synthetic rerun rather than an automatic attempt one.

**Given** Process Manager and canary launch-role permissions are analyzed
**When** positive and negative IAM tests run
**Then** the Process Manager may assume only the registered canary launch role, while that role may `RunTask` only the canary task family on the exact cluster and `PassRole` only its execution and task roles
**And** direct ECS access, unrelated task families, clusters, roles, boundary removal, trust mutation, or authorization-path changes are denied.

**Given** launch behavior is tested in a disposable Cell
**When** duplicate delivery, concurrent delivery, `RunTask` errors, HTTP-200 failures, crash windows, delayed reconciliation, multiple-task conflict, stale CONFIG, and safe-retry expiry are exercised
**Then** no scheduled occurrence creates more than one ECS task
**And** each outcome reaches the documented durable state with attributable logs and bounded metrics.

### Story 1.9: Correlate ECS State and Completion Evidence

As an On-call Engineer,
I want ECS lifecycle events and structured completion records correlated to the authoritative canary occurrence,
So that successful, failed, delayed, duplicate, and conflicting outcomes are distinguished correctly.

**Acceptance Criteria:**

**Given** ECS task-state evidence is consumed for the first time
**When** Cell integrations are planned
**Then** an encrypted ECS-event source queue and DLQ are created, and an account-local EventBridge rule captures only relevant cluster task-state events
**And** the normalizer derives task authority from the AWS event resource/detail fields, source account, Region, cluster, and task ARN rather than body-supplied job identity.

**Given** completion-log evidence is consumed for the first time
**When** the canary completion path is deployed
**Then** an encrypted completion source queue and DLQ plus the log ingestor and exact canary log-subscription permission are created
**And** authoritative log identity derives from the AWS-generated log group and stream envelope mapped to the registered task and job.

**Given** an ECS event arrives after task mapping exists
**When** it is normalized
**Then** the task ARN resolves through the Story 1.8 ledger index to one occurrence and attempt, producing canonical task-state evidence
**And** asserted job, occurrence, CONFIG, attempt, or task values are compared but cannot redirect the event.

**Given** an ECS or completion event arrives before task mapping is committed
**When** correlation cannot yet resolve the task ARN
**Then** it is retained as orphan evidence and retried or reconciled within a bounded window
**And** it is neither discarded, applied to another occurrence, nor treated as an immediate successful completion.

**Given** the mapped canary task reaches `RUNNING`
**When** task-state evidence is reduced
**Then** the occurrence records authoritative `started_at` and transitions idempotently to `STARTED`
**And** duplicate, delayed, or reordered start events do not change the task attempt or immutable occurrence coordinates.

**Given** the canary emits a structured completion record
**When** the log ingestor parses it
**Then** job, Occurrence ID, CONFIG, attempt, timestamp, status, exit code when available, and sanitized error reason assertions conform to the completion schema
**And** malformed, secret-bearing, wrong-job, wrong-task, or unsupported-version records are rejected without declaring success.

**Given** attempt zero has exactly one accepted success record and the essential container exits with code zero
**When** the Process Manager reduces both evidence records
**Then** the occurrence transitions exactly once to `SUCCEEDED` with authoritative task and completion timing
**And** neither Scheduler delivery, a log marker, log-window count, nor zero exit alone establishes success.

**Given** the task fails to start, stops unexpectedly, or an essential container exits non-zero
**When** task-state evidence is reduced
**Then** the occurrence transitions to `FAILED` with stable sanitized stop and exit details
**And** a later success marker cannot overwrite that terminal result.

**Given** completion evidence is duplicated, delayed, conflicting, associated with another occurrence, or tied to multiple task ARNs
**When** all immutable evidence is reduced
**Then** the published commutative fixtures determine the final state independent of arrival order
**And** wrong-window evidence cannot satisfy the canary occurrence and conflicts become `AMBIGUOUS`.

**Given** ECS capture, log ingestion, and normalization roles are analyzed
**When** IAM-positive and IAM-negative tests run
**Then** each producer can publish only its permitted event types to its exact source queue and read only required AWS metadata
**And** cross-producer forgery, cross-job log delivery, direct ledger writes, ECS launch, role passing, and queue-policy mutation are denied.

**Given** correlation is tested in a disposable Cell
**When** success, start failure, non-zero exit, missing marker, marker without zero exit, wrong Occurrence ID, delayed prior completion, duplicates, conflicts, early events, log-delivery failure, and consecutive windows are exercised
**Then** every occurrence reaches the state defined by the Compatibility Package
**And** valid successful canary runs produce no failure state or unbounded metric dimensions.

### Story 1.10: Detect Missed and Overdue Occurrences

As an On-call Engineer,
I want every due canary occurrence reconciled against launch and completion deadlines,
So that a missing invocation or unfinished task cannot disappear because of delayed evidence or index propagation.

**Acceptance Criteria:**

**Given** deadline evaluation is introduced for the first time
**When** Cell resources are planned
**Then** the occurrence ledger gains the contract-defined deadline access pattern and an encrypted scanner checkpoint stores the durable watermark and bounded reconciliation position
**And** no alert-outbox or notification resource is created by this story.

**Given** deadline evidence needs an authenticated producer path
**When** the scanner integration is deployed
**Then** an encrypted deadline source queue and DLQ are created with published retention, visibility, retry, partial-batch, and quarantine settings
**And** the normalizer derives authority from the scanner role, queue ARN, ledger deadline key, Cell identity, and registered event type rather than caller-supplied coordinates.

**Given** a due occurrence is queried
**When** the scanner evaluates candidates
**Then** it advances a durable watermark, scans a bounded lookback, paginates safely, and verifies every candidate against the authoritative base-table item
**And** an eventually consistent index result is never treated as conclusive absence.

**Given** an `EXPECTED` occurrence reaches its launch deadline without valid launch evidence
**When** canonical `DEADLINE_REACHED` evidence is reduced
**Then** the Process Manager sets the occurrence to `MISSED` with schedule-delivery failure context
**And** immutable job, generation, CONFIG, scheduled time, deadline, and evidence provenance remain queryable.

**Given** a launched or `STARTED` occurrence reaches its completion deadline without one valid completion result
**When** deadline evidence is reduced
**Then** the Process Manager sets the occurrence to `OVERDUE`
**And** the Cell does not stop the task, claim enforced cancellation, or extend the deadline because evidence arrived late.

**Given** a due record is temporarily absent from the deadline index
**When** later scans execute within the maximum lateness horizon
**Then** bounded lookback and base-table verification rediscover and process it
**And** no occurrence deadline can be permanently skipped because of GSI propagation delay.

**Given** the scanner crashes after reading candidates or emitting only part of a batch
**When** the next invocation resumes
**Then** uncommitted candidates are rediscovered and deterministic producer event IDs make re-emission idempotent
**And** the scanner never writes occurrence state directly.

**Given** valid, duplicate, late, or conflicting evidence arrives before or after deadline evidence
**When** the Process Manager reduces the complete immutable evidence set
**Then** the Compatibility Package determines the same result independent of arrival order
**And** late evidence cannot silently overwrite `MISSED`, `OVERDUE`, `FAILED`, or `AMBIGUOUS`.

**Given** scanner authority is analyzed
**When** IAM-positive and IAM-negative tests run
**Then** it can read only required deadline and CONFIG projections, update only its checkpoint, and send deadline evidence only to its source queue
**And** it cannot mutate occurrence items, launch or stop ECS tasks, assume job roles, change schedules, write alerts, or forge another producer.

**Given** deadline behavior is tested in a disposable Cell
**When** no-launch, no-completion, zero-exit-without-marker, delayed index visibility, duplicate scans, pagination boundaries, restart, late evidence, and sustained scanner lag are exercised
**Then** required occurrences become `MISSED` or `OVERDUE` within five minutes of the declared deadline
**And** healthy completed canary occurrences produce no false deadline state.

### Story 1.11: Deliver Occurrence Alerts Reliably

As an On-call Engineer,
I want each terminal canary failure delivered with complete occurrence context,
So that I can begin the correct response without reconstructing the run manually.

**Acceptance Criteria:**

**Given** an occurrence newly reduces to `FAILED`, `MISSED`, `OVERDUE`, or `AMBIGUOUS`
**When** the Process Manager commits the terminal result
**Then** the same DynamoDB transaction creates one unique alert-outbox item for the occurrence, state, failure plane, and alert policy
**And** terminal state cannot commit without its corresponding outbox record.

**Given** terminal canary failures existed before alert routing was deployed
**When** the bounded outbox reconciliation process first runs
**Then** it creates only missing deterministic outbox items after verifying current authoritative state
**And** it does not duplicate an existing alert identity, alter occurrence state, or notify for `SUCCEEDED` occurrences.

**Given** alert routing is introduced for the first time
**When** Cell resources are planned
**Then** the occurrence outbox stream integration, reconciliation access pattern, Alert Router, and a separate encrypted notification-deduplication ledger are created with explicit retention and recovery settings
**And** notification delivery records remain separate from authoritative occurrence state.

**Given** a pending outbox item is dispatched
**When** the Alert Router resolves its registered CONFIG
**Then** it publishes to the canary's exact test notification sink with job, Occurrence ID, state, failure plane, account, Region, Environment, detection time, Deployment Identity, owner, sanitized reason, and Runbook reference
**And** secret values, raw CONFIG, unrestricted log text, credentials, and sensitive Terraform content are excluded.

**Given** DynamoDB Streams or the router delivers the same outbox item more than once
**When** notification is attempted
**Then** a conditional notification-ledger record deduplicates the alert identity across the configured retry horizon
**And** duplicate processing does not silently produce duplicate notifications.

**Given** two consecutive canary occurrences fail
**When** each terminal transaction commits
**Then** each occurrence produces a distinct notification with its own Occurrence ID
**And** an aggregate alarm already in `ALARM` cannot suppress the later occurrence notification.

**Given** Stream processing is delayed or unavailable
**When** the reconciliation scan runs
**Then** every pending, unconfirmed, or retryable outbox item is rediscovered and dispatched within bounded limits
**And** no committed terminal failure remains permanently stranded without delivery evidence.

**Given** publication succeeds but the router crashes before recording completion
**When** processing resumes
**Then** the notification ledger and target-delivery semantics either suppress the retry or record an explicit ambiguous-delivery outcome
**And** attempts, timestamps, target identity, response, and final status remain attributable.

**Given** Alert Router authority is analyzed
**When** IAM-positive and IAM-negative tests run
**Then** it can read required outbox and CONFIG metadata, update only notification-delivery records, and publish only to the registered canary sink
**And** it cannot mutate occurrence state, CONFIG, schedules, workload roles, arbitrary notification targets, or its own authorization path.

**Given** alert delivery is failure-tested
**When** tests simulate crash before publish, crash after publish, duplicate Stream events, Stream delay, reconciliation, target denial, missing target, malformed payload, and consecutive failures
**Then** every required canary failure is delivered or surfaced as an actionable routing failure within five minutes
**And** at least 20 accelerated successful canary occurrences produce zero false failure notifications.

### Story 1.12: Monitor Cell Health with the Canary

As a Platform On-call Engineer,
I want bounded health signals and tested alarms for every shared Cell failure plane,
So that platform degradation is detected before scheduled-job failures are misdiagnosed or missed.

**Acceptance Criteria:**

**Given** the complete canary path is deployed
**When** the Cell observability catalog is applied
**Then** metrics and alarms cover expectation-horizon freshness, schedule conformance, Scheduler attempts and delivery failures, source and ingress queue age/depth, every DLQ, Lambda errors/throttles/duration/concurrency, DynamoDB throttles and conditional failures, deadline lag, log-subscription delivery, outbox reconciliation, notification delivery, and processed-canary freshness
**And** each signal has explicit thresholds, evaluation periods, missing-data behavior, owner, severity, and Runbook reference.

**Given** occurrence and runtime components publish metrics
**When** metric dimensions are inspected
**Then** they use only bounded Cell, job, Environment, state, and failure-plane values defined by the Compatibility Package
**And** Occurrence ID, task ARN, log stream, error text, source ARN, and other unbounded values are excluded from dimensions.

**Given** one canary occurrence completes successfully through Scheduler, normalization, Process Manager launch, ECS events, completion logs, and ledger reduction
**When** terminal success is accepted
**Then** the platform emits a processed-heartbeat timestamp for the exact Cell canary path
**And** a fresh heartbeat proves end-to-end processing without treating it as proof for any non-canary job.

**Given** Scheduler cannot deliver launch evidence
**When** target errors, throttling, dropped delivery, retry exhaustion, or Scheduler DLQ depth breach thresholds
**Then** one actionable delivery-path incident reaches the Platform test destination with Cell, account, Region, Environment, failure plane, and Runbook context
**And** independent expected occurrences still become per-job `MISSED` results at their deadlines.

**Given** a component stops processing without a direct error
**When** horizon, queue-age, scanner-watermark, outbox, or canary-heartbeat freshness becomes stale
**Then** the appropriate Cell-health incident fires before the platform's required detection window is breached
**And** stale-heartbeat logic alarms within five minutes without relying solely on Lambda error metrics.

**Given** one shared Cell fault affects multiple components or jobs
**When** alarm state changes are routed
**Then** aggregate alarm events pass through the Alert Router and notification ledger to produce one deduplicated Cell incident per policy window
**And** distinct occurrence failures continue to notify their Job Owners separately.

**Given** the Cell returns to healthy operation
**When** recovery thresholds are met
**Then** aggregate alarms recover without deleting unresolved occurrence failures or prior delivery evidence
**And** alarm history, state changes, receipts, and recovery timestamps remain attributable for the configured retention period.

**Given** production and non-production Cells have different noise policies
**When** alarm routing is configured
**Then** production health alarms and destinations are mandatory while approved non-production routes may use the test or low-noise destination
**And** disabling optional non-production notifications cannot disable metric collection, DLQ retention, or canary evaluation.

**Given** observability cost guardrails are evaluated
**When** metric, alarm, log, and retention resources are planned
**Then** cardinality, alarm count, log retention, query frequency, and expected fixed Cell cost are documented and bounded
**And** invalid unbounded dimensions or unsupported retention values fail validation.

**Given** Cell health qualification runs
**When** tests inject Scheduler delivery denial, horizon staleness, queue backlog, DLQ messages, Lambda failures, DynamoDB throttling, scanner lag, log-subscription failure, stale canary, stranded outbox, and target denial
**Then** each required failure reaches the test destination within five minutes of becoming observable
**And** at least 20 accelerated healthy canary windows produce zero false Cell or occurrence alerts.

### Story 1.13: Authorize Operator Access and Commands

As a Platform On-call Engineer,
I want short-lived, attributable access to submit bounded platform commands,
So that I can diagnose and contain incidents without assuming workload roles or mutating authoritative data directly.

**Acceptance Criteria:**

**Given** a responder needs production Cell access
**When** operator IAM is planned
**Then** a separate permissions-boundary-constrained operator role trusts only the approved short-lived human identity path with session limits, actor attribution, and required approval context
**And** it cannot assume workload roles, call `RunTask`, pass roles, write DynamoDB or S3 data directly, change schedules directly, alter trust, or access another Cell.

**Given** a responder submits an operational request
**When** the command handler entry point is invoked
**Then** it authenticates the AWS caller and validates command type, Cell or registered-job scope, reason, approval reference, reviewed Deployment Identity, and any required duplicate-effect or compensation acknowledgement
**And** the entry point uses authenticated regional AWS APIs with no public inbound endpoint or static credential.

**Given** command evidence is produced for the first time
**When** Cell resources are planned
**Then** an encrypted command source queue and DLQ are created with the published retry, visibility, retention, partial-batch, and quarantine settings
**And** only the command handler may send permitted command types while the normalizer derives command authority from handler role and registry metadata.

**Given** a command request is valid
**When** the command handler accepts it
**Then** it creates a UUIDv7 `command_id`, records actor, session, approval, reason, scope, timestamp, Deployment Identity, and required acknowledgements, then emits Cell-stamped canonical command evidence
**And** the user cannot supply producer identity, canonical event identity, arbitrary evidence, task ARN, role ARN, or a new Occurrence ID.

**Given** an authorized synthetic rerun is requested
**When** the command identity is generated
**Then** `occurrence/manual/v1` hashes the exact canonical job, original occurrence, CONFIG version, and command ID bytes and records `replay_of_occurrence_id`
**And** the original occurrence remains immutable and the accepted command does not bypass attempt-zero or overlap protections.

**Given** replay, rerun, schedule-disablement, or recovery command intake is requested
**When** validation succeeds
**Then** the command is recorded and delivered through the authenticated evidence path for the appropriate existing or later command executor
**And** acceptance alone does not claim that Cell recovery, direct state mutation, or an unsafe replay has completed.

**Given** break-glass access is required
**When** the documented emergency path is invoked
**Then** access is time-bound, independently approved, immediately alerted, CloudTrail-attributable, and limited to the exact Cell and emergency action set
**And** expiry is enforced automatically and the session requires post-incident review.

**Given** a command is malformed, stale, unauthorized, cross-job, cross-Cell, missing approval, or requests prohibited authority
**When** the handler evaluates it
**Then** it fails closed with a stable sanitized reason and no canonical command is emitted
**And** the denial is attributable without exposing secret, credential, or unrestricted operational data.

**Given** operator and handler permissions are analyzed
**When** positive and negative IAM tests run
**Then** approved diagnosis and command submission succeed through the intended roles
**And** direct ledger/CONFIG writes, arbitrary queue sends, workload-role assumption, direct ECS launch, schedule mutation, cross-account access, approval self-forgery, and authorization-path changes are denied.

**Given** operator controls are exercised
**When** tests cover approved commands, duplicate requests, stale approvals, wrong Cell, wrong job, caller-supplied identity, concurrent reruns, nonterminal originals, break-glass expiry, and audit review
**Then** identical command delivery produces one logical command and no premature workload side effect
**And** the Runbook records access prerequisites, safe command usage, verification, escalation, and rollback boundaries.

### Story 1.14: Recover Cell State Safely

As a Platform On-call Engineer,
I want an approved, rehearsable Cell recovery workflow,
So that corrupted control data can be restored without launching against a partial or inconsistent platform.

**Acceptance Criteria:**

**Given** an incident requires Cell data recovery
**When** the recovery command is authorized
**Then** the workflow records actor, independent approval, reason, affected Cell, restore point, expected RPO/RTO, current Deployment Identity, and recovery generation
**And** missing approval, unsupported source version, or an unverified restore point prevents recovery from starting.

**Given** recovery begins
**When** containment executes
**Then** launch is disabled before state changes, schedule generations are quiesced, processors that mutate or consume affected state are paused, and in-flight evidence is drained or quarantined without deletion
**And** the original tables, queues, CONFIG, logs, and deployment evidence remain intact for investigation and rollback.

**Given** production DynamoDB PITR is available
**When** data is restored
**Then** affected namespace, CONFIG, occurrence, checkpoint, outbox, and notification data are restored to new encrypted tables at the approved point rather than overwriting source tables
**And** restored resources use protected tags, deletion safeguards, exact schema/index definitions, and a distinct attributable recovery identity.

**Given** restored tables are available
**When** integrity validation runs
**Then** schemas, keys, CONFIG hashes, ownership generations, occurrence/task mappings, processed-event deduplication, deadline indexes, outbox references, notification records, and Deployment Identity are checked against the Compatibility Package
**And** any incompatible, incomplete, or internally inconsistent result blocks cutover.

**Given** integrity checks pass
**When** the Cell is moved to the recovery generation
**Then** versioned Lambda aliases and Cell Contract pointers switch through a reviewed, atomic or fail-closed procedure to the compatible restored resources
**And** consumers never receive a contract that mixes old and new table identities or unsupported schema versions.

**Given** retained evidence exists after the restore point
**When** replay begins
**Then** queues are replayed through the same authenticated normalizer and Process Manager paths with original producer identity, event deduplication, and safe-retry limits
**And** unresolved launch evidence past its conservative retry deadline cannot call `RunTask` and instead becomes `AMBIGUOUS`.

**Given** replay and cutover complete
**When** reconciliation runs
**Then** the materializer rebuilds the expectation horizon, the scanner reconciles every nonterminal occurrence, task and completion evidence are remapped, and pending outbox records are delivered or surfaced
**And** no terminal result is silently overwritten and no referenced CONFIG or task revision is removed.

**Given** the recovered Cell appears consistent
**When** pre-resume verification runs
**Then** canary scheduling, exactly-one launch, ECS state, completion correlation, deadlines, queue health, logs, metrics, occurrence alerts, aggregate alarms, and notification delivery pass
**And** launch remains disabled until all blocking checks and required approvals succeed.

**Given** recovery verification fails or the new generation regresses
**When** rollback is invoked
**Then** launch remains disabled and aliases plus the Cell Contract return to the prior known-good compatible generation without deleting recovery evidence
**And** the failure, actions, resulting state, and next recovery decision remain attributable.

**Given** recovery authority is analyzed
**When** IAM-positive and IAM-negative tests run
**Then** only the approved recovery role can create restored resources and switch versioned recovery references within the exact Cell
**And** it cannot alter its own trust, bypass approval, assume workload roles, mutate source tables, delete evidence, or operate in another account-Region Cell.

**Given** a disposable-Cell recovery exercise completes
**When** measured results are published
**Then** actual data loss, restore duration, replay duration, reconciliation time, alert-verification time, and total RPO/RTO are recorded with known limitations
**And** the evidence is suitable for the later pilot gate without claiming automatic cross-Region failover.

### Story 1.15: Garbage-Collect Unreferenced Platform Versions

As a Platform Owner,
I want obsolete Cell and canary artifacts removed only after their references and recovery horizons expire,
So that lifecycle cleanup controls cost without breaking replay, investigation, upgrade, or rollback.

**Acceptance Criteria:**

**Given** CONFIG, task-definition, schema, runtime, or contract versions accumulate
**When** lifecycle inventory runs
**Then** it enumerates references from active and retired schedule generations, CONFIG registry, occurrences, task attempts, source queues and DLQs, replay windows, log and investigation retention, deployment evidence, recovery generations, supported majors, and rollback policy
**And** unavailable, eventually inconsistent, or contradictory reference data makes eligibility fail closed.

**Given** one artifact appears unreferenced
**When** eligibility is calculated
**Then** the candidate must be older than every applicable runtime, retry, replay, retention, support, recovery, and rollback horizon and have no active or pending reference
**And** eligibility is recorded with artifact identity, checks performed, evidence checksums, policy version, decision time, and earliest deletion time.

**Given** a lifecycle action is proposed
**When** the dry-run plan is generated
**Then** it lists exact candidates, reasons, dependencies, expected cost effect, irreversible effects, preservation evidence, verification steps, and rollback limitations
**And** wildcard resource selection, tag-only discovery, mutable aliases, or unbounded batch deletion is prohibited.

**Given** a production deletion is eligible
**When** approval is requested
**Then** Platform approval and any policy-required Job Owner or Security approval are bound to the exact candidate set and evidence checksums
**And** changed references, expired approval, broadened scope, or a newer deployment invalidates the action.

**Given** an approved cleanup executes
**When** the lifecycle principal removes or deregisters artifacts
**Then** it operates in bounded batches, preserves required tombstones and manifests, verifies each result, and stops on the first unexplained discrepancy
**And** namespace ownership, occurrence evidence, alert evidence, Deployment Identity, and current/previous-major compatibility are not deleted.

**Given** a CONFIG or task-definition version is still referenced by an occurrence, queue, DLQ, investigation, synthetic rerun, active generation, or known-good rollback identity
**When** deletion is attempted
**Then** the action is denied with the blocking reference and policy horizon
**And** failed proof leaves the artifact intact.

**Given** schema, Lambda version, or Cell Contract cleanup is requested
**When** compatibility checks run
**Then** the stable Process Manager principal and every supported consumer major remain valid through expand-migrate-contract horizons
**And** no alias, contract pointer, recovery generation, or queued event can resolve to a removed version.

**Given** lifecycle authority is provisioned
**When** IAM-positive and IAM-negative tests run
**Then** only the dedicated lifecycle principal may act on exact platform-owned candidates under required tags, paths, boundaries, and approved manifests
**And** operators, runtime roles, consumer applies, job roles, and the lifecycle principal itself cannot broaden scope, alter approval evidence, or change its authorization path.

**Given** cleanup succeeds or fails
**When** results are recorded
**Then** actor, role session, approval, candidate manifest, actions, AWS responses, retained tombstones, verification, cost estimate, and failures remain attributable
**And** alarms surface partial cleanup or attempts to remove protected artifacts.

**Given** lifecycle behavior is tested
**When** fixtures cover active references, delayed queue messages, expired and unexpired horizons, stale approvals, changed aliases, unavailable indexes, partial deletion, and fully unreferenced candidates
**Then** protected artifacts are never removed and eligible test artifacts are removed predictably
**And** the canary still completes end to end after cleanup verification.

## Epic 2: Run a Secure Scheduled Job in Non-Production

Application teams can declare, deploy, observe, disable, and safely rerun a private ECS Fargate scheduled job through the standard module in non-production.

### Story 2.1: Declare and Reserve a Scheduled Job

As an Application Engineer,
I want to validate and reserve a scheduled-job declaration against a target Platform Cell,
So that my repository has an authorized, collision-free identity before workload resources are created.

**Acceptance Criteria:**

**Given** a consumer root declares a scheduled job
**When** module validation runs
**Then** required inputs cover Environment, Application, job name, owner, immutable repository identity, account, Region, ECS cluster, image, recurring schedule, compute, command, non-secret configuration, secret references, permissions, runtime, overlap policy, networking, notification metadata, and tags
**And** every input has a description, explicit type, meaningful validation, and an example that contains no real account, ARN, credential, or secret value.

**Given** the target Cell Contract exists in SSM
**When** the module resolves it
**Then** JSON schema, checksum, Cell identity, account, Region, Environment, semantic version, integration ARNs, encryption reference, and supported CONFIG/evidence ranges are validated
**And** missing, malformed, mismatched, stale, or incompatible contracts fail planning without reading platform Terraform state.

**Given** valid Environment, Application, and job-name inputs
**When** canonical identity is derived
**Then** the job ID follows the lowercase segment grammar, length limits, reserved-prefix rules, and predictable AWS naming transformations from the Compatibility Package
**And** invalid characters, empty segments, collisions, or names that cannot produce stable resource identifiers fail before apply.

**Given** an authorized repository requests the canonical job ID
**When** the Registrar evaluates the reservation
**Then** it conditionally binds the job to immutable repository identity, root path, apply identity, account, Region, Environment, Application, owner, and ownership generation
**And** the lifecycle becomes `RESERVED` without granting launch authority or creating workload resources.

**Given** the same owner retries an identical reservation
**When** the request is processed
**Then** the existing reservation is returned idempotently
**And** another repository, root, apply role, account, Region, namespace, or owner cannot claim or overwrite it.

**Given** ownership must transfer
**When** a transfer request is evaluated
**Then** the current owner, receiving owner, and independent Platform approver must authorize quiescence and a new ownership generation
**And** stale roles, active generations, unresolved occurrences, unapproved namespace movement, and automatic tombstone reuse block transfer.

**Given** standard metadata and consumer tags are supplied
**When** names and tags are calculated
**Then** nonempty Environment, Application, Service, Owner, ManagedBy, Repository, and applicable CostCenter values are applied predictably
**And** consumer values cannot remove, empty, or conflict with protected platform tags.

**Given** the module is used for this epic's supported outcome
**When** Environment policy is evaluated
**Then** a non-production declaration can proceed to later Epic 2 resources using the approved advisory/blocking policy catalog
**And** production launch remains fail-closed until protected delivery, completed Runbook, readiness evidence, and required approvals from later epics are supplied.

**Given** a declaration is valid and reserved
**When** outputs are inspected
**Then** they expose canonical job ID, Cell identity, compatibility result, reservation generation, normalized schedule identity, and protected metadata without secret values
**And** they do not claim task, schedule, CONFIG, or activation resources exist yet.

**Given** the module interface changes
**When** `modules/ecs-scheduled-job` and `modules/ecs-scheduled-job/examples/basic` validation runs
**Then** formatting, backend-free initialization, variable tests, contract tests, reservation fixtures, and secret/hardcoding scans pass
**And** committed `.tfvars`, mutable references, provisioners, `null_resource`, unstable address changes without migration, and undocumented standards deviations fail.

### Story 2.2: Create Least-Privilege Job IAM Roles

As a Security Reviewer,
I want each scheduled job to use separate, reviewable roles with bounded authority,
So that launch, ECS execution, and application access cannot combine into an escalation path.

**Acceptance Criteria:**

**Given** a reserved job identity and approved permissions boundary
**When** IAM resources are planned
**Then** the module creates distinct job-launch, ECS task-execution, and application-task roles under the platform-managed role path
**And** every role has protected ownership tags, the mandatory boundary, predictable naming, and no permissions beyond its responsibility.

**Given** the Process Manager must assume the job-launch role
**When** launch-role trust is rendered
**Then** only the exact stable Process Manager principal for the target Cell major is trusted with the narrowest supported source-account and Cell conditions
**And** GitHub, humans, Scheduler, ECS tasks, unrelated Lambdas, cross-account principals, and stale Cell roles cannot assume it.

**Given** the launch role will invoke ECS
**When** its policy is evaluated
**Then** `ecs:RunTask` is restricted to the intended task-definition family and exact ECS cluster, and `iam:PassRole` is restricted to the job's execution and application roles with `iam:PassedToService = ecs-tasks.amazonaws.com`
**And** any family-revision wildcard required by ECS is isolated, documented, and denied outside the canonical job family.

**Given** ECS must pull an image, write logs, and inject agent-managed secrets
**When** the execution policy is rendered
**Then** it grants only required ECR actions, the derived exact job log-group scope, exact approved Secrets Manager or SSM references, and required KMS keys
**And** AWS-required resource wildcards such as an authorization-token action are isolated with service-specific justification and no unrelated action.

**Given** the application needs AWS API access
**When** explicit application policy statements are supplied
**Then** they attach only to the application-task role and remain inspectable in the Terraform plan with action, resource, condition, and statement identity preserved
**And** invalid statements, IAM self-management, role passing, permissions-boundary changes, or Terraform/runtime control-plane access fail validation.

**Given** application permissions contain wildcard, cross-account, or escalation-sensitive authority
**When** non-production policy analysis runs
**Then** findings use the versioned policy catalog's advisory or blocking severity and identify exact remediation
**And** the same authority remains production-blocking unless a later governed exception supplies owner, scope, justification, approver, expiry, and compensating control.

**Given** a customer-managed policy attachment is requested
**When** validation runs
**Then** it must be same-account, explicitly allowlisted, version-governed, compatible with the required boundary, and included in effective-policy analysis
**And** AWS-managed, cross-account, unapproved, or externally mutable attachments are rejected.

**Given** ECS-agent secret injection is configured
**When** policies are generated
**Then** only the execution role receives exact secret and KMS decrypt access required by the references
**And** secret values never enter module inputs, task environment variables, CONFIG, plans, outputs, fixtures, or documentation.

**Given** approved application-pull secret mode is selected
**When** policies are generated
**Then** only the application-task role receives exact secret and KMS access, and the declaration identifies the required network path
**And** cross-account, customer-managed KMS, or external-platform access requires explicit resource, key, trust, and network-policy validation.

**Given** ECS assumes the execution or application role
**When** trust policies are analyzed
**Then** trust is limited to `ecs-tasks.amazonaws.com`, the source account, and the narrowest supported source-resource condition
**And** named positive and negative confused-deputy fixtures prove correct source-account/source-ARN handling.

**Given** IAM validation executes
**When** static analysis, effective-policy analysis, and negative tests run
**Then** approved workload actions succeed while user/key creation, administrator policies, boundary removal, trust mutation, unrelated `PassRole`, OIDC changes, ledger writes, cross-job CONFIG access, and self-modification fail
**And** every unavoidable wildcard or standards deviation is documented at the exact statement.

**Given** role resources change
**When** module tests and migration checks run
**Then** stable role addresses, trust principals, policy statement identities, boundary attachment, and output types are preserved or accompanied by reviewed migration guidance
**And** rollback restores the prior compatible policies without deleting roles that remain referenced by task definitions or CONFIG.

### Story 2.3: Enforce Private Task Networking

As a Cloud Infrastructure Owner,
I want job networking validated against an explicit private-network policy,
So that scheduled tasks cannot gain public exposure or unintended egress.

**Acceptance Criteria:**

**Given** the organization's network classifications are required for deployment
**When** this story is implemented
**Then** a versioned policy catalog defines the approved private-subnet evidence, security-group rules, dependency reachability evidence, exception owner, and enforcement stage
**And** an absent or unknown policy version fails closed rather than relying on an unnamed organizational convention.

**Given** a consumer supplies VPC and subnet IDs
**When** a trusted plan evaluates them
**Then** every subnet is verified in the declared account and Region, belongs to the declared VPC, and satisfies the catalog's private-subnet classification method
**And** empty sets, public classification, mismatched VPC/account/Region, stale IDs, or unsupported availability configuration produce actionable findings.

**Given** ECS network configuration is rendered
**When** any Environment is planned
**Then** `awsvpc` mode uses explicit subnet and security-group IDs and public IP assignment is disabled
**And** consumer input cannot enable public IP assignment or add a public network interface.

**Given** consumers supply existing security groups
**When** trusted policy analysis inspects them
**Then** each group belongs to the declared VPC and is evaluated for ingress, IPv4/IPv6 egress, referenced groups, prefix lists, CIDRs, ports, protocols, and default-rule drift
**And** public ingress, unrestricted egress, cross-VPC references, stale rules, or policy mismatch receive the catalog-defined non-production severity and remain production-blocking.

**Given** a consumer enables module-created security-group mode
**When** Terraform plans the group
**Then** it has no ingress and only explicitly declared security-group, prefix-list, or bounded CIDR egress destinations, protocols, and ports
**And** implicit default egress, `0.0.0.0/0`, `::/0`, all-protocol rules, and unreviewed rule expansion are absent unless a later governed production exception authorizes exact scope.

**Given** the task needs ECR, S3, CloudWatch Logs, Secrets Manager, SSM, KMS, or application dependencies
**When** reachability inputs are validated
**Then** the declaration maps each dependency to an approved NAT, VPC endpoint, PrivateLink, proxy, stable egress, or internal network path
**And** the module reports missing evidence without creating routes, NAT gateways, endpoints, subnets, or other consumer network infrastructure.

**Given** application-pull secrets or an approved external secrets platform are configured
**When** network policy is evaluated
**Then** its exact endpoint or controlled egress path is consistent with Story 2.2 task-role permissions and the declared secret mode
**And** secret retrieval requires no public ingress and exposes no secret value in Terraform or network metadata.

**Given** networking validation succeeds
**When** module outputs are inspected
**Then** they expose non-sensitive VPC, subnet, security-group, public-IP policy, policy version, and dependency-reachability identifiers required for CONFIG
**And** unrelated route tables, gateways, endpoints, shared security groups, and subnet resources remain outside module ownership.

**Given** networking changes are tested
**When** policy fixtures and module tests run
**Then** they cover private/public classification, mismatched VPCs, supplied/created groups, IPv4/IPv6 exposure, default egress, missing endpoints, valid bounded access, policy-version mismatch, and exceptions
**And** every changed module and module-local example passes backend-free validation while cloud-dependent assertions run only in a trusted test context.

**Given** a networking change must be rolled back
**When** the prior known-good configuration is restored
**Then** the task generation remains disabled until the restored network evidence is revalidated
**And** shared consumer networking is never deleted or mutated by module rollback.

### Story 2.4: Provision the Fargate Task and Structured Logs

As an Application Engineer,
I want the module to create a validated Fargate task definition and retained log group,
So that my job runs with an immutable identity and emits evidence the Cell can correlate.

**Acceptance Criteria:**

**Given** a reserved job and approved IAM roles
**When** the task definition is planned
**Then** it uses Fargate compatibility, `awsvpc` network mode, explicit CPU and memory, configured platform compatibility, and the exact execution and application-task role ARNs
**And** unsupported CPU/memory combinations, invalid ephemeral storage, or incompatible runtime settings fail before apply.

**Given** a container image is declared
**When** image policy runs
**Then** an immutable digest or approved immutable reference is accepted and recorded in Deployment Identity
**And** mutable references such as `latest` are identified by non-production policy and remain blocking for any later production promotion.

**Given** command, entrypoint, and non-secret environment overrides are supplied
**When** container definitions are rendered
**Then** the reviewed values are preserved exactly and remain separate from runtime occurrence overrides
**And** consumer inputs cannot override reserved job, Occurrence ID, CONFIG, attempt, task, or Deployment Identity fields.

**Given** ECS-agent secret references are supplied
**When** container definitions are rendered
**Then** they use the ECS `secrets` contract with only approved locator metadata
**And** no secret value appears in ordinary environment variables, Terraform input examples, task-definition JSON, CONFIG, plan summaries, outputs, tags, or logs.

**Given** application-pull secret references are supplied
**When** container definitions are rendered
**Then** only non-sensitive locator and mode metadata are made available to the application
**And** the required task-role permissions and network path from Story 2.2 and Story 2.3 must validate before the task definition is considered deployable.

**Given** a per-job CloudWatch log group is created
**When** log configuration is applied
**Then** the group is encrypted, predictably named, protected-tagged, and assigned explicit configurable retention within platform guardrails
**And** defaults are 30 days for non-production and 90 days for production declarations unless a versioned policy requires a stricter value.

**Given** the task uses the `awslogs` driver
**When** execution-role scope is evaluated
**Then** the container writes only to the job's exact log group and discoverable stream prefix
**And** it cannot create or write another job's log group or omit the required log configuration.

**Given** the Job Completion Contract applies
**When** application logging requirements are validated
**Then** the declaration and example require structured start, success, and failure records asserting the supplied job, Occurrence ID, CONFIG, attempt, timestamps, status, exit code when available, and sanitized error reason
**And** documentation states that a success marker or zero exit alone does not establish successful completion.

**Given** the task-definition revision is registered
**When** outputs are inspected
**Then** they expose full revision ARN, family, immutable image identity, log group, role ARNs, module version, source revision input, and protected metadata needed for later CONFIG publication
**And** secret values, raw sensitive container configuration, and unbounded operational data are excluded.

**Given** task or logging configuration changes
**When** validation runs
**Then** tests cover valid and invalid compute combinations, immutable and mutable images, command rendering, reserved-field collisions, both secret modes, log encryption and retention, exact permissions, and structured completion examples
**And** the module and module-local basic example pass formatting, backend-free validation, security scanning, and address-stability checks.

**Given** a task-definition change must be rolled back
**When** the prior compatible configuration is restored
**Then** Terraform registers or selects the known-good immutable revision without deleting log history or referenced prior revisions
**And** later cleanup remains governed by the lifecycle proof rather than the rollback operation.

### Story 2.5: Publish Phase-One Job Resources and CONFIG

As an Application Engineer,
I want my job root to publish immutable launch resources while the schedule remains disabled,
So that the Cell can review exact AWS identities and configuration before any occurrence executes.

**Acceptance Criteria:**

**Given** the job has a reservation, task revision, IAM roles, logs, and validated networking
**When** phase-one Terraform is planned
**Then** it creates the job-owned EventBridge Scheduler schedule in a disabled state and a dedicated delivery role targeting the exact Scheduler source queue and DLQ from the Cell Contract
**And** no direct Scheduler-to-ECS target, enabled launch, shared Cell resource, or runtime-ledger mutation is present.

**Given** the Scheduler delivery role is rendered
**When** trust and permissions are analyzed
**Then** trust is restricted to `scheduler.amazonaws.com`, the source account, and exact schedule-group source ARN, while send authority is restricted to the exact source queue and DLQ
**And** named confused-deputy fixtures reject wrong account, wrong group, wrong schedule, stale role, cross-job queue, and unrelated event types.

**Given** the disabled schedule is rendered
**When** its target and timing configuration are inspected
**Then** it contains the normalized recurring expression, IANA time zone, disabled flexible window, future activation anchor, retry attempts, maximum event age, and canonical scheduled-time launch envelope required by the Compatibility Package
**And** unsupported expressions, one-time schedules, ambiguous anchors, mutable payload identity, or missing retry semantics fail planning.

**Given** all launch inputs are known
**When** the job module renders CONFIG
**Then** the canonical body includes job and ownership generation, normalized schedule and generation, activation window, full task-definition revision ARN, cluster, private subnets, security groups, public-IP policy, execution/task/launch roles, runtime deadline, overlap declaration, log group, notification metadata, Deployment Identity, policy versions, and supported contract versions
**And** only approved secret references appear; secret values and caller-generated occurrence identity are absent.

**Given** canonical CONFIG is rendered
**When** its version is calculated
**Then** `config_version` is the lowercase content hash of the exact canonical secret-free body and the object key follows the registered job prefix contract
**And** identical content produces the same version while any launch-relevant change creates a new immutable schedule/CONFIG generation.

**Given** phase one is applied
**When** CONFIG is published
**Then** the job apply role writes one encrypted object only to its reserved content-addressed inbox prefix and lifecycle becomes `PUBLISHED`
**And** it cannot overwrite another version, write another job's prefix, or claim `VALIDATED`, `MATERIALIZED`, or `ENABLED`.

**Given** job-side permissions are analyzed
**When** IAM-negative tests run
**Then** the apply identity can manage only its module-owned task, roles, logs, optional security group, disabled schedule, delivery role, and exact CONFIG prefix
**And** it cannot write namespace, registry, occurrence, outbox, notification, queue, processor, Cell Contract, protected state, or another job's resources.

**Given** phase-one outputs are inspected
**When** apply completes
**Then** they expose schedule ARN, delivery-role identity, task revision, launch-role ARN, CONFIG hash/key, ownership generation, activation anchor, Deployment Identity, and lifecycle `PUBLISHED` without secret values
**And** they state explicitly that publication is not Cell acknowledgement or launch authorization.

**Given** phase-one planning and apply are retried
**When** no launch-relevant input changes
**Then** Terraform is idempotent, resource addresses remain stable, and no additional CONFIG generation or schedule is created
**And** any required address migration uses reviewed `moved` blocks or explicit migration guidance.

**Given** phase one fails or must be rolled back
**When** the documented rollback executes
**Then** the schedule remains disabled, partial job-owned resources are reconciled, and prior task revisions, CONFIG objects, logs, and ownership evidence remain available
**And** rollback does not delete shared Cell resources or enable a previous generation implicitly.

### Story 2.6: Validate and Acknowledge Job Configuration

As a Platform Engineer,
I want the Cell to validate each published job configuration against its registered AWS identities,
So that only an immutable, authorized launch contract can advance toward activation.

**Acceptance Criteria:**

**Given** a reserved job has completed phase one
**When** the Registrar resolves its deployed identities
**Then** it verifies the actual schedule ARN, schedule group, Scheduler delivery-role ARN and Role ID, job-launch-role ARN and Role ID, task family, repository/root binding, account, Region, owner, and ownership generation
**And** stale, substituted, manually recreated, cross-job, cross-account, or unregistered identities are rejected.

**Given** immutable identities pass verification
**When** the reservation is updated
**Then** the Registrar conditionally binds the exact schedule ARN and IAM Role IDs to the existing ownership generation
**And** an identical retry is idempotent while a changed identity requires an approved new generation rather than overwrite.

**Given** a CONFIG candidate exists in the registered inbox prefix
**When** the Cell validation path consumes it
**Then** object key, encryption, ownership metadata, schema version, canonical bytes, content hash, job identity, ownership generation, and supported ranges are verified before AWS configuration is inspected
**And** malformed, noncanonical, secret-bearing, cross-prefix, or hash-mismatched candidates become `REJECTED`.

**Given** CONFIG syntax and ownership are valid
**When** AWS identity validation runs
**Then** the Cell verifies the exact task-definition revision and family, ECS cluster, private subnets, security groups, public-IP-disabled setting, execution/task/launch roles, log group, secret references, schedule target, retry configuration, notification metadata, and policy versions against authoritative APIs and registry data
**And** missing resources, public exposure, incompatible accounts/Regions, mutable identities, stale roles, or mismatched permissions fail validation.

**Given** schedule and occurrence semantics are validated
**When** the Cell compares the candidate with the Compatibility Package
**Then** normalized expression, time zone, start anchor, activation window, flexible-window setting, generation hash, runtime deadline, overlap declaration, and occurrence identity inputs are consistent
**And** unsupported schedule grammar, missing deadlines, ambiguous generation, or caller-supplied Occurrence IDs are rejected.

**Given** a candidate passes all validation
**When** the Cell records the acknowledgement
**Then** it copies one immutable CONFIG snapshot into the separate registry and records `VALIDATED` with config hash, schedule ARN, Role IDs, ownership generation, schema/contract versions, validation evidence, and timestamp
**And** it does not enable Scheduler, create an expectation horizon, or mutate the job Terraform state.

**Given** validation fails
**When** rejection is recorded
**Then** lifecycle becomes `REJECTED` with stable machine codes and an actionable secret-free reason at a job-scoped acknowledgement path
**And** the schedule remains disabled, no expectations are materialized, and prior valid generations remain unchanged.

**Given** the consumer reads the acknowledgement
**When** module data sources and outputs evaluate it
**Then** they verify Cell signature or checksum, job identity, ownership generation, config hash, schedule ARN, Role IDs, lifecycle state, and compatibility result
**And** a job can read only its own non-sensitive acknowledgement without direct registry-table or platform-state access.

**Given** Cell validation authority is analyzed
**When** IAM-positive and IAM-negative tests run
**Then** the Registrar and materializer can resolve only required AWS metadata, bind registered identities, read job inbox candidates, and write verified registry/acknowledgement records
**And** they cannot modify job-owned resources, enable schedules, write occurrence state, assume launch roles, pass roles, read secret values, or validate another account-Region Cell.

**Given** acknowledgement behavior is tested
**When** valid, retry, stale-role, replaced-schedule, hash mismatch, cross-prefix, wrong account, public network, mutable task identity, unsupported contract, and concurrent-generation cases run
**Then** only the exact compliant candidate reaches `VALIDATED` and all invalid cases remain disabled
**And** the test suite preserves deterministic results under repeated delivery.

**Given** a validation release regresses
**When** the prior compatible Cell validator is restored
**Then** existing immutable acknowledgements remain readable and no rejected generation is enabled automatically
**And** revalidation creates attributable evidence rather than rewriting historical results.

### Story 2.7: Activate the Non-Production Schedule Safely

As a Job Owner,
I want my reviewed non-production schedule enabled only after its expected occurrences are verified,
So that Scheduler delivery and occurrence tracking cannot disagree about what should run.

**Acceptance Criteria:**

**Given** a job declares a recurring schedule
**When** activation inputs are validated
**Then** they include the supported cron/rate expression, IANA time zone, explicit start anchor, activation window, disabled flexible window, retry attempts, maximum event age, completion deadline, overlap policy, and generation hash
**And** unsupported syntax, one-time schedules, ambiguous anchors, missing deadlines, or unknown policy versions fail before activation.

**Given** Scheduler retry settings are configured
**When** the non-production plan is reviewed
**Then** Scheduler delivery retries and event age are explicit and distinct from Cell launch reconciliation and application retry behavior
**And** the declaration acknowledges at-least-once delivery and records the job's duplicate-effect strategy.

**Given** runtime and overlap behavior are declared
**When** activation policy runs
**Then** maximum runtime is treated as the occurrence completion deadline and never as enforced cancellation
**And** an overlap-unsafe job requires explicit idempotency, locking, or compensation evidence at the severity defined by the non-production policy catalog.

**Given** the exact CONFIG is `VALIDATED` for a future activation anchor
**When** the materializer processes that generation
**Then** it creates and the Process Manager records at least 24 hours of deterministic expected occurrences with a matching conformance result
**And** lifecycle becomes `MATERIALIZED` only for the exact config hash, schedule ARN, Role IDs, ownership generation, and activation anchor.

**Given** an exact `MATERIALIZED` acknowledgement exists
**When** a separate non-production phase-two plan is generated
**Then** Terraform preconditions permit only that acknowledged generation to become enabled
**And** changed, stale, missing, rejected, incompatible, insufficient-horizon, or mismatched acknowledgements block the plan.

**Given** the phase-two plan is applied
**When** the activation anchor is reached
**Then** Scheduler emits canonical launch evidence through the Cell source queue, and occurrence IDs match the independently recorded expectations
**And** lifecycle becomes `ENABLED` for the same immutable generation without any direct Scheduler-to-ECS invocation.

**Given** a production Environment is selected
**When** enablement is planned during Epic 2
**Then** activation fails because protected delivery, completed Runbook, production readiness evidence, and required approvals are absent
**And** fixtures prove that a non-production acknowledgement cannot be relabeled or promoted to bypass that gate.

**Given** a Job Owner disables the non-production job
**When** enabled state is changed through Terraform or an authorized command
**Then** future Scheduler delivery stops without deleting task revisions, CONFIG, expected/actual occurrence history, logs, alarms, or ownership registration
**And** actor, reason, lifecycle state, and Deployment Identity remain attributable.

**Given** schedule expression, time zone, or another launch-relevant field changes
**When** rollout begins
**Then** the existing generation is disabled and retired before a new future-anchored immutable generation is published, validated, materialized, and enabled
**And** in-flight evidence is drained or reconciled and any planned gap is explicit.

**Given** Scheduler exhausts retry or event-age limits
**When** launch delivery fails
**Then** the message is retained in the Scheduler DLQ, Cell delivery metrics identify the failure, and the independently expected occurrence remains eligible to become `MISSED`
**And** a delivery retry cannot create a second platform task attempt.

**Given** non-production activation is tested
**When** tests cover schedule conformance, retries, duplicate delivery, runtime/overlap declarations, disabled schedules, stale acknowledgements, phase-two mutation, generation replacement, target denial, production bypass, and rollback
**Then** only the exact eligible non-production generation runs
**And** rollback disables launch first and restores a prior compatible generation without deleting evidence.

### Story 2.8: Connect Completion Evidence and Alert Metadata

As a Job Owner,
I want my job's completion records and operational ownership connected to the Platform Cell,
So that non-production failures are correlated and routed with enough context to diagnose them.

**Acceptance Criteria:**

**Given** the job has a retained log group and validated CONFIG
**When** occurrence-aware completion is enabled
**Then** the job root creates the exact CloudWatch Logs subscription defined by the Cell Contract for its registered log group
**And** the Cell accepts delivery only from the expected source account, log-group ARN, stream mapping, job ownership generation, and permitted completion schema.

**Given** the application emits structured start, success, or failure records
**When** the Cell log ingestor processes them
**Then** each record asserts the supplied job, Occurrence ID, CONFIG, attempt, timestamp, status, exit code when available, and sanitized error reason
**And** AWS-generated log-group/stream metadata and task-ARN mapping remain authoritative over application assertions.

**Given** an occurrence reports success
**When** completion is reduced
**Then** exactly one accepted success record for attempt zero must correlate with a zero essential-container exit
**And** an uncorrelated marker, adjacent-window marker, log count, Scheduler success metric, duplicate marker, or zero exit alone cannot satisfy completion.

**Given** job operational metadata is declared
**When** CONFIG validation runs
**Then** it records the Job Owner, operations/Runbook URI, completion deadline, log retention, detection mode, notification target when configured, and escalation classification
**And** production declarations require non-placeholder owner, completed Runbook location, occurrence-aware mode, and production notification target even though Epic 2 cannot activate them.

**Given** a non-production notification target is supplied
**When** a job failure or completion-contract alert is emitted
**Then** it routes through the Cell Alert Router to the registered low-noise/test destination with job, Occurrence ID, Environment, account, Region, failure plane, state, detection time, Deployment Identity, owner, and Runbook URI
**And** the job role and module cannot publish directly to arbitrary destinations.

**Given** non-production alarms are disabled by approved policy
**When** the module is planned
**Then** logs, occurrence tracking, Cell-health signals, deadline state, and alert-delivery capability remain enabled
**And** the reduced routing choice is explicit in outputs and cannot be promoted to production.

**Given** a non-production job selects best-effort completion detection during MVP
**When** configuration is validated
**Then** the module labels the reduced coverage and may create a bounded success-pattern metric filter and low-noise alarm tied to the job
**And** production policy rejects that mode because it cannot prove each expected occurrence completed.

**Given** CloudWatch Logs cannot deliver completion evidence
**When** subscription errors, disabled filters, permission changes, or sustained delivery failures occur
**Then** a job or Cell health alarm reaches the configured operational path
**And** affected occurrences remain eligible for `OVERDUE` rather than being considered successful.

**Given** completion or alert metadata is exposed
**When** plans, outputs, logs, or alert payloads are inspected
**Then** only non-sensitive identifiers and sanitized reasons are present
**And** secret values, raw CONFIG, unrestricted logs, credentials, saved-plan contents, and sensitive application data are excluded.

**Given** integration permissions are analyzed
**When** IAM-positive and IAM-negative tests run
**Then** the registered log subscription and Cell components can perform only their exact delivery, parsing, correlation, and registered notification actions
**And** cross-job log delivery, forged completion, arbitrary target publication, direct occurrence writes, and role or resource-policy mutation fail.

**Given** completion integration is tested
**When** valid success, non-zero exit, missing marker, marker without zero exit, wrong occurrence, duplicate marker, delayed prior completion, subscription failure, missing target, reduced-coverage mode, and consecutive failures run
**Then** occurrence-aware mode produces the canonical state and each required test alert arrives within five minutes
**And** healthy occurrence-aware runs produce no false failure notification.

### Story 2.9: Expose Job Operations and Optional Views

As an On-call Engineer,
I want stable job outputs and an optional operational view,
So that I can locate resources and assess health without inspecting Terraform state.

**Acceptance Criteria:**

**Given** a scheduled job has been deployed
**When** module outputs are inspected
**Then** documented outputs identify canonical job, Cell, account, Region, Environment, ownership generation, schedule/group, task-definition revision, cluster, log group, job roles, networking, CONFIG hash/generation, acknowledgement, alarms, notification metadata, operations URI, and lifecycle state
**And** every output has a stable explicit type, description, sensitivity classification, and operational purpose.

**Given** Deployment Identity is requested
**When** the module constructs it
**Then** it includes image digest, task-definition revision, source revision input, module version, workflow identity when supplied, CONFIG hash, schedule generation, target account/Region/Environment, Cell version, and deployment run reference when available
**And** the same non-sensitive identity is available to task tags, occurrence records, alerts, verification, and rollback evidence.

**Given** an operator uses the outputs
**When** they follow documented console or CLI references
**Then** they can locate the schedule, current task revision, ECS tasks/events, log group, occurrence state, alarms, notification route, CONFIG acknowledgement, and Cell health
**And** the procedure uses supported operator access and never requires platform or consumer Terraform-state inspection.

**Given** outputs appear in a plan, apply log, automation artifact, or documentation generator
**When** data-safety checks run
**Then** no secret value, secret payload, raw CONFIG body, binary plan content, unrestricted log text, credential, or sensitive application data is exposed
**And** secret-reference identifiers are omitted unless their non-sensitive operational use is explicitly documented.

**Given** a consumer enables the optional CloudWatch dashboard
**When** Terraform creates it
**Then** the view separates Scheduler delivery, ECS launch and runtime outcomes, occurrence completion states, deadline failures, log-delivery health, alert delivery, and linked Cell health
**And** it uses only bounded metrics and approved log queries without Occurrence ID, task ARN, error text, or log stream as metric dimensions.

**Given** dashboard cost and scale guardrails are evaluated
**When** the dashboard is planned
**Then** widget count, metric/query count, time range, refresh assumptions, log-query use, and expected cost remain within documented configurable limits
**And** invalid unbounded dimensions or unsupported query patterns fail validation.

**Given** a consumer omits or disables the dashboard
**When** Terraform is applied
**Then** logs, occurrence tracking, deadlines, required alarms, notification routing, and Cell-health collection remain unchanged
**And** no required monitoring or alert action depends on dashboard existence.

**Given** output or dashboard contracts evolve
**When** compatibility checks run
**Then** snapshots verify output names/types, resource identities, Deployment Identity, lifecycle state, redaction, bounded dimensions, dashboard-enabled behavior, and dashboard-disabled behavior
**And** breaking output changes require a major release and migration note rather than silent replacement.

**Given** a dashboard change must be rolled back
**When** the prior compatible view is restored or the dashboard is disabled
**Then** required operational signals and evidence remain intact
**And** rollback does not alter the job schedule, task revision, CONFIG, occurrence state, or alarms.

### Story 2.10: Perform a Controlled Non-Production Rerun

As a Job Owner,
I want to rerun a reviewed non-production occurrence through an authorized platform command,
So that I can recover without editing the schedule, bypassing tracking, or creating an untraceable duplicate.

**Acceptance Criteria:**

**Given** a Job Owner requests a rerun
**When** the command workflow starts
**Then** it requires canonical job ID, original Occurrence ID, reviewed CONFIG and Deployment Identity, reason, expected duplicate effects, verification plan, and rollback or compensation acknowledgement
**And** the requester cannot supply a new Occurrence ID, task ARN, arbitrary task definition, cluster, role, network configuration, or evidence payload.

**Given** the non-production rerun request is complete
**When** authorization is evaluated
**Then** the Job Owner and policy-required Platform approver authorize the exact command through the short-lived operator path
**And** actor, approval, Environment, job, original occurrence, timestamp, scope, and reason are retained.

**Given** the original occurrence is running, nonterminal, or has unresolved launch ambiguity
**When** a rerun is requested
**Then** the request blocks by default until overlap and launch uncertainty are resolved under the declared policy
**And** schedule cadence alone is not accepted as proof that another task is safe.

**Given** an authorized rerun reaches the command handler
**When** it is accepted
**Then** the handler generates the UUIDv7 command ID and deterministic `occurrence/manual/v1` identity linked by `replay_of_occurrence_id`
**And** duplicate delivery of the same approved command resolves to one logical synthetic occurrence.

**Given** the Process Manager receives the canonical rerun command
**When** launch eligibility is evaluated
**Then** it verifies command attribution, original occurrence, exact reviewed CONFIG, ownership generation, job state, overlap declaration, compensation acknowledgement, and safe launch window
**And** stale CONFIG, wrong job, expired approval, production target, changed Deployment Identity, or prohibited overlap fails before `RunTask`.

**Given** the synthetic occurrence is eligible
**When** it launches
**Then** it uses the same attempt-zero reservation, job-scoped launch role, exact task revision, private networking, client-token reconciliation, and ambiguity protections as a scheduled occurrence
**And** the EventBridge schedule remains unchanged.

**Given** the rerun task executes
**When** task state and completion records arrive
**Then** tags, overrides, logs, ECS events, ledger state, deadlines, and alerts use the synthetic Occurrence ID while retaining the original occurrence link
**And** the original occurrence and its terminal result remain immutable.

**Given** the rerun succeeds
**When** verification completes
**Then** zero essential-container exit and exactly one valid structured success record are both required
**And** command ID, task ARN, Deployment Identity, actor, approvals, result, verification evidence, and completed compensation checks are recorded.

**Given** the rerun fails, becomes overdue, or is ambiguous
**When** its terminal state or deadline is reached
**Then** standard occurrence alerts and non-production operational guidance apply
**And** the record identifies whether rollback, another approved command, or application compensation is required without automatically retrying.

**Given** a human attempts to rerun by assuming a workload role, calling `RunTask`, editing the schedule, or forging command evidence
**When** IAM and normalizer enforcement run
**Then** the action is denied outside the registered operator-command and Process Manager path
**And** the attempted bypass is attributable through CloudTrail or the relevant security signal.

**Given** rerun behavior is tested
**When** authorized success, unauthorized caller, wrong job, stale CONFIG, nonterminal original, ambiguous launch, duplicate command, concurrent command, failed rerun, production target, and compensation cases execute
**Then** no approved command creates more than one synthetic occurrence or ECS task
**And** rollback guidance disables further launch and preserves all original and synthetic evidence.

## Epic 3: Deliver and Evolve Jobs Through Governed Automation

Platform reviewers and deployers can validate changes, bind trusted targets, enforce policy, approve and apply exact plans, record Deployment Identity, and publish compatible immutable releases.

### Story 3.1: Expand Credential-Free Pull Request Validation

As a Platform Reviewer,
I want every pull request validated without cloud credentials,
So that malformed, insecure, or non-reproducible changes are rejected before they can access AWS or protected state.

**Acceptance Criteria:**

**Given** a pull request changes Terraform, runtime, contracts, examples, workflows, policy, documentation, or dependency files
**When** credential-free validation runs
**Then** it identifies every affected root, module, module-local example, runtime package, contract suite, policy bundle, and generated reference
**And** no changed validation target is silently skipped.

**Given** Terraform files change
**When** Terraform checks run
**Then** they execute recursive `terraform fmt -check`, backend-free initialization, validation for every changed root/module/example, focused module tests, and address/migration checks under Terraform `>= 1.10, < 2.0`
**And** failures identify the exact target and command needed to reproduce them locally.

**Given** runtime or contract files change
**When** code checks run
**Then** pinned dependency installation, formatting, linting, type checks, unit tests, schema tests, identity vectors, schedule fixtures, reducer permutations, IAM fixtures, and compatibility matrices run as applicable
**And** unsupported schema changes or test removals cannot pass by changing only expected output.

**Given** static security and repository-hygiene checks run
**When** the pull request is scanned
**Then** Terraform, IAM, workflows, dependencies, documentation, fixtures, and committed files are checked for credentials, secret values, state, saved plans, `.terraform/`, committed `.tfvars`, mutable production references, prohibited provisioners, `null_resource`, hardcoded deployment identifiers, and undocumented standards deviations
**And** obvious secrets, invalid Terraform, formatting failures, and prohibited artifacts block every Environment.

**Given** Terraform resource addresses or module structure change
**When** migration validation runs
**Then** stable addresses are preserved or reviewed `moved` blocks and explicit consumer migration guidance are present
**And** accidental replacement or undocumented address churn fails with the impacted resource list.

**Given** a pull request originates from a fork or another untrusted context
**When** validation executes
**Then** it receives no AWS credential, protected state, Environment secret, deployment manifest secret, write token, or privileged reusable-workflow input
**And** untrusted code cannot reach a privileged job through artifacts, caches, outputs, workflow commands, reusable-workflow indirection, or modified workflow files.

**Given** validation needs repository permissions or pull-request reporting
**When** `GITHUB_TOKEN` permissions are evaluated
**Then** each job declares the minimum read-only scope and any trusted reporting job consumes only sanitized non-executable results
**And** untrusted code never runs with pull-request write, Actions write, OIDC token, Environment, or contents-write authority.

**Given** providers, modules, Actions, workflows, Python packages, or container references are resolved
**When** supply-chain validation runs
**Then** immutable constraints, full-SHA workflow/Action pins, provider locks, dependency locks, checksums, and approved managed-runtime exceptions are verified
**And** unexpected selection, checksum change, floating production reference, or mutable image fails the applicable policy.

**Given** a check produces logs, caches, summaries, or artifacts
**When** results are retained
**Then** output excludes secret values, credentials, unrestricted environment dumps, raw sensitive plans, raw CONFIG, and executable content crossing trust boundaries
**And** artifact access and retention match the data classification.

**Given** non-production enforcement is staged
**When** a policy finding is reported
**Then** severity comes from the versioned rollout catalog and clearly distinguishes advisory from blocking status with its future enforcement point
**And** production-equivalent controls cannot inherit a lower Environment's advisory severity.

**Given** workflow security fixtures execute
**When** they simulate forked changes, malicious outputs, workflow edits, cache poisoning, generated-file injection, changed locks, committed `.tfvars`, and failing checks
**Then** none obtain privileged execution or satisfy required statuses
**And** all valid baseline fixtures pass without AWS credentials or network access beyond pinned dependency retrieval.

### Story 3.2: Bind Trusted Deployment Targets and OIDC Roles

As a Security Engineer,
I want every deployment Environment bound to immutable GitHub and AWS identities,
So that only the approved repository and workflow can access the intended account, Region, role, and state.

**Acceptance Criteria:**

**Given** an Environment is authorized for deployment
**When** its target manifest is defined
**Then** the immutable manifest binds repository owner/repository IDs and name, root path, Environment, account, Region, plan-role ARN, apply-role ARN, state bucket/key/lock path, Cell Contract path, policy catalog, and approved reusable-workflow full SHA
**And** consumer workflow inputs cannot substitute production targets, roles, state, Cell identity, or workflow revision.

**Given** the organization configures GitHub OIDC subjects
**When** a deployment token is issued
**Then** the custom `sub` includes immutable owner and repository IDs, deployment Environment, and full-SHA `job_workflow_ref`, while AWS trust requires exact `aud = sts.amazonaws.com` and the complete expected `sub`
**And** name-only, branch-only, wildcard repository, missing workflow, or unsupported custom-claim assumptions are rejected.

**Given** plan and apply require different authority
**When** IAM roles are provisioned
**Then** separate permissions-boundary-constrained plan and apply roles use distinct exact OIDC subjects, session names, duration limits, and protected tags
**And** neither trust accepts an unauthorized repository, workflow revision, Environment, branch/tag context, pull-request subject, audience, or cross-account provider.

**Given** the plan role is assumed
**When** effective permissions are evaluated
**Then** it can read only the exact state and lock metadata, Cell Contract, configuration, and AWS resources required for refresh and planning
**And** it cannot mutate infrastructure, write state, publish CONFIG, change schedules, pass roles, assume apply, alter its trust, or access another target.

**Given** the apply role is assumed after approval
**When** effective permissions are evaluated
**Then** it can mutate only the manifest-bound platform resource namespace and state path under the required boundary and organizational controls
**And** it cannot create IAM users/keys, remove boundaries, create administrator authority, alter OIDC/trust, pass unrelated roles, write runtime tables, change state-backend controls, or modify another root.

**Given** Terraform state is configured
**When** backend controls are inspected
**Then** state uses an encrypted, versioned, public-blocked S3 backend with native S3 lock files and exact path-scoped IAM
**And** each account, Environment, and root is isolated from all other state and lock objects.

**Given** a trusted job assumes an AWS role
**When** target preflight runs
**Then** it verifies caller identity, account, Region, repository IDs, Environment, workflow SHA, manifest checksum, root path, role ARN, state path, policy version, and Cell identity before Terraform initialization
**And** any mismatch exits before state or resource access.

**Given** production deployment controls are required
**When** GitHub configuration is reviewed
**Then** protected Environments enforce required reviewers, self-review prevention, restricted deployment refs, controlled concurrency, and disabled administrator bypass, or an explicitly equivalent auditable control is referenced
**And** production authorization remains blocked until the exact control set and versioned qualifying-review policy are demonstrated.

**Given** a trusted identity must rotate to a new workflow SHA or repository identity
**When** migration is planned
**Then** old and new subjects overlap only for a bounded reviewed transition, target manifests and trust update in a safe order, and the old subject is removed after verification
**And** a moving tag, unbounded wildcard, or destructive in-place trust replacement cannot become the rollback mechanism.

**Given** OIDC and target controls are tested
**When** positive and negative fixtures execute
**Then** exact approved plan/apply identities succeed while altered repository, transfer/rename, wrong Environment/ref/workflow/audience/account/Region/role/state path, self-review, and expired transition cases fail
**And** no long-lived AWS access key is created, stored, or documented.

### Story 3.3: Generate a Trusted and Reviewable Terraform Plan

As a Platform Reviewer,
I want an attributable Terraform plan generated with read-only cloud access,
So that I can review exact target impact without granting infrastructure mutation authority.

**Acceptance Criteria:**

**Given** credential-free validation passes for a reviewed revision
**When** trusted planning is requested
**Then** the workflow runs from the manifest-approved reusable-workflow SHA, checks out the exact source commit, verifies workflow and dependency integrity, and assumes only the target plan role
**And** changed privileged workflows, unreviewed commits, prohibited providers, provisioners, executable hooks, or mutable dependencies block planning.

**Given** the trusted plan job starts
**When** target preflight runs
**Then** it verifies repository IDs, source commit, Environment, account, Region, root path, manifest checksum, plan-role ARN, state path, Cell Contract checksum, policy catalog, and workflow SHA
**And** any mismatch terminates before protected state is read.

**Given** Terraform initializes against the trusted target
**When** providers and modules are selected
**Then** the manifest-bound encrypted backend and native lock path are used, the committed provider lock is verified with `-lockfile=readonly`, and immutable module references are enforced
**And** unexpected versions, checksums, backend changes, address migrations, or dependency selection fail the job.

**Given** initialization and refresh succeed
**When** Terraform planning runs
**Then** it generates a binary saved plan for the exact commit and target using only the read-only plan role
**And** the role cannot mutate AWS, write state/locks, publish CONFIG, alter schedules/IAM, invoke operators, or write Cell runtime data.

**Given** the plan is created
**When** metadata is recorded
**Then** it includes source and repository identity, workflow SHA/run, manifest checksum, account, Region, Environment, root/state path, Cell/module/contract versions, provider-lock checksum, assumed-role session, creation/expiry time, and plan checksum
**And** any later source, target, manifest, dependency, policy, or Cell-contract change invalidates it.

**Given** reviewers need an impact summary
**When** plan reporting runs
**Then** it publishes sanitized create/update/delete/replace counts, affected stable addresses, IAM/network/observability categories, lifecycle handshake effects, expected cost notes, and policy status
**And** unrestricted attribute values, secret data, raw CONFIG, sensitive outputs, and the binary plan remain access-restricted.

**Given** the binary plan is stored
**When** artifact controls are evaluated
**Then** it is treated as sensitive, checksum-verified, access-restricted to authorized jobs/reviewers, and retained only for the configured short review window
**And** it is never committed, placed in a cross-trust cache, printed, attached to an unrestricted PR comment, or exposed to untrusted jobs.

**Given** no infrastructure changes are present
**When** Terraform returns a no-change result
**Then** the workflow records a successful attributable no-op plan with target and dependency integrity checks
**And** policy evaluation and readiness prerequisites still run rather than being skipped.

**Given** a pull request needs an advisory cloud-backed plan
**When** the context is authorized and trusted
**Then** planning runs only after the untrusted workflow completes and against the reviewed commit using the exact plan role
**And** a fork, draft, changed workflow, unapproved ref, or attacker-controlled artifact cannot trigger credentialed execution.

**Given** trusted planning controls are tested
**When** fixtures alter commits, manifests, state paths, provider locks, module references, workflow SHAs, roles, accounts, Regions, artifact checksums, or executable hooks
**Then** every mismatch fails before mutation authority is available
**And** no path converts plan credentials or a plan artifact into apply authority.

### Story 3.4: Enforce Production Policies and Govern Exceptions

As a Production Approver,
I want consistent policy-as-code decisions applied to every trusted plan,
So that insecure or operationally incomplete changes cannot reach production through reviewer oversight.

**Acceptance Criteria:**

**Given** a trusted production plan is available
**When** baseline production policy runs
**Then** it blocks missing protected tags/ownership, mutable images, public IPs/subnets, unsafe security groups or egress, missing logs/retention/alarms, absent notification target, plaintext secret inputs, best-effort completion, incompatible Cell contracts, and missing lifecycle acknowledgement
**And** each denial names the resource address, policy ID/version, requirement, evidence, severity, and remediation.

**Given** a plan creates or changes IAM
**When** effective-policy analysis runs
**Then** actions, resources, conditions, trust, `PassRole`, managed-policy drift, cross-account access, privilege escalation, permissions boundaries, and CI self-modification are evaluated rather than wildcard syntax alone
**And** administrator authority, unrelated role passing, boundary removal, trust mutation, IAM users/keys, OIDC changes, runtime-data writes, and cross-job access are blocked.

**Given** trust or service-role policies are evaluated
**When** confused-deputy rules run
**Then** required source-account, source-ARN, principal, `PassedToService`, queue, schedule-group, task-family, cluster, and registered ownership conditions match the Compatibility Package
**And** named positive and negative fixtures prove wrong account/resource/principal and stale-role cases fail.

**Given** a plan changes schedule or launch configuration
**When** architecture policy runs
**Then** direct Scheduler-to-ECS targets, mutable CONFIG, unregistered jobs, stale Role IDs, insufficient expectation horizon, missing acknowledgement, phase-two mutation, unsafe overlap, or generation mismatch are denied
**And** only the exact `RESERVED` through `ENABLED` handshake can authorize launch.

**Given** repository, workflow, and dependency content is evaluated
**When** supply-chain and hygiene policy runs
**Then** state, saved plans, `.terraform/`, committed `.tfvars`, credentials, generated secrets, mutable Actions/workflows/modules/images, changed provider locks, prohibited provisioners, `null_resource`, hardcoded targets, and undocumented address changes are blocked as applicable
**And** secret scanning covers code, Terraform, workflow inputs, examples, documentation, fixtures, summaries, and generated output.

**Given** IAM or networking changes may require Security review
**When** the versioned qualifying-change catalog evaluates the plan
**Then** exact change types, resource scopes, risk thresholds, required reviewers, exception owner, and catalog version determine whether Security approval is required
**And** an unknown classification, missing catalog, ambiguous result, or stale version fails closed.

**Given** compliant and noncompliant fixtures exist
**When** policy CI runs
**Then** every blocking rule has deterministic positive and negative fixtures, and load-bearing NFR/architecture/AWS-standard mappings identify the stories and controls it enforces
**And** a policy change cannot silently remove coverage, lower production severity, or alter expected findings.

**Given** a policy permits an exception
**When** an exception is submitted
**Then** it is bound to exact policy, resource, Environment, source revision, plan checksum, owner, justification, approver, compensating control, and expiry/review date
**And** broad, reusable, expired, unsigned, mismatched, or changed-plan exceptions are rejected.

**Given** a non-exemptible control fails
**When** an exception is attempted
**Then** invalid Terraform, target mismatch, plaintext secret exposure, missing production approval controls, unauthorized escalation, mutable deployment identity, or absent occurrence-aware production tracking remains blocking
**And** the denial explains why normal exception governance cannot waive it.

**Given** non-production policy staging is active
**When** dev or staging plans are evaluated
**Then** advisory and blocking severities follow the versioned adoption timeline and remain visible in evidence
**And** production is blocking from the first release and never inherits a lower Environment's severity.

**Given** policy evaluation completes
**When** results are retained
**Then** policy bundle and catalog versions, plan checksum, source revision, target, findings, exceptions, actors, approvals, and timestamps are attributable
**And** sanitized summaries exclude secret values, raw plan content, credentials, and unrestricted sensitive attributes.

### Story 3.5: Approve and Apply the Exact Production Plan

As a Production Approver,
I want production to apply only a fresh, policy-compliant plan from the approved deployment commit,
So that reviewed intent cannot change between approval and infrastructure mutation.

**Acceptance Criteria:**

**Given** a revision merges to the authorized deployment ref
**When** production deployment starts
**Then** the workflow checks out the exact deployment commit and creates a fresh saved plan using the manifest-bound plan role and target
**And** no pull-request plan, prior-run plan, mutable ref, different target, or different workflow can be promoted directly.

**Given** the fresh deployment plan is created
**When** pre-approval checks run
**Then** target verification, dependency locks, Cell compatibility, policy evaluation, exception validation, lifecycle acknowledgement, and plan metadata execute again against its checksum
**And** any source, manifest, dependency, policy, target, Cell, or acknowledgement change blocks approval.

**Given** a plan can enable production launch
**When** readiness preflight runs
**Then** it requires a valid exact-generation readiness decision conforming to the Compatibility Package schema and bound to source, target, plan checksum, job, CONFIG, schedule generation, and Deployment Identity
**And** until Epic 4 produces that decision, production job activation remains blocked while workflow tests use only a controlled disposable fixture.

**Given** the plan passes all blocking checks
**When** the protected Environment gate opens
**Then** Platform Engineering and the Job Owner must approve, with Security approval added when the Story 3.4 qualifying-change catalog requires it
**And** self-review, administrator bypass, unrelated reviewers, stale approvals, missing policy version, or approval from another run are rejected.

**Given** deployments target the same account, Environment, and Terraform root
**When** concurrency controls run
**Then** only one plan/apply sequence holds the deployment lock, and a newer run cannot silently cancel an in-progress production apply
**And** separate roots cannot use concurrency to bypass shared state, namespace, or generation safeguards.

**Given** approval is granted
**When** the apply job starts
**Then** it assumes only the exact apply role and re-verifies caller, target manifest, source commit, workflow SHA, plan checksum, artifact provenance/expiry, state path, lock ownership, policy result, and readiness decision
**And** apply credentials are unavailable to planning, review, untrusted, reporting, or post-processing jobs.

**Given** all apply preconditions match
**When** Terraform executes
**Then** it applies the exact approved binary plan without replanning, variable substitution, target override, refresh mutation, or interactive changes
**And** state remains encrypted and natively locked for the complete mutation window.

**Given** job creation or a launch-relevant change requires two phases
**When** protected applies proceed
**Then** phase one and phase two use separate fresh plans, policy checks, readiness decisions where applicable, and approvals bound to their respective lifecycle states
**And** phase two cannot be folded into phase one or enable a generation changed after acknowledgement.

**Given** apply fails or the runner is lost
**When** failure handling runs
**Then** partial result, state/lock condition, plan identity, errors, and recovery guidance are recorded without automatic mutation retry
**And** a subsequent attempt requires lock recovery if needed and a new fresh plan reflecting actual state.

**Given** an emergency production path is invoked
**When** normal controls are bypassed under policy
**Then** access is time-bound, independently approved, immediately alerted, actor-attributable, exact-target-limited, and post-incident reviewed
**And** it cannot waive secret, target identity, authorization escalation, or occurrence-tracking controls.

**Given** apply workflow tests run
**When** they simulate changed plans, expired artifacts, stale approvals, wrong targets, concurrent runs, self-review, readiness mismatch, phase folding, runner loss, lock conflict, and emergency access
**Then** only the exact approved fixture plan mutates the disposable target
**And** production job launch remains impossible without the later real readiness evidence.

### Story 3.6: Record Deployment and Rollback Evidence

As an On-call Engineer,
I want every deployment tied to immutable workload identity and reviewed recovery instructions,
So that I can determine exactly what changed and restore a known-good configuration safely.

**Acceptance Criteria:**

**Given** a production plan is awaiting approval
**When** deployment evidence is assembled
**Then** it records repository/source commit, workflow SHA/run, module/Cell/contract versions, provider-lock checksum, image digest, task revision, CONFIG hash, schedule generation, account, Region, Environment, state path, plan checksum, policy bundle, target manifest, expected plan impact, and cost note
**And** missing required Deployment Identity or impact fields block approval.

**Given** production approval is granted
**When** approval evidence is retained
**Then** it records Platform, Job Owner, and required Security approvers, timestamps, reviewed plan/readiness checksums, policy catalog, exceptions, emergency status, and OIDC session identity
**And** approval is bound to the exact deployment rather than a mutable branch, tag, general Environment, or future plan.

**Given** Terraform apply completes or fails
**When** deployment evidence is finalized
**Then** it records apply actor/session, start/end times, state result, changed stable addresses and resource identities, lifecycle state, output checksums, errors, lock condition, and workflow conclusion
**And** partial or failed applies remain visible and cannot be represented as successful.

**Given** a task or occurrence is investigated
**When** an operator follows Deployment Identity
**Then** the operator can map it to exact image, task revision, source, CONFIG, schedule generation, module/Cell/workflow/contract versions, target, approvals, policy results, and deployment run
**And** the mapping does not require access to raw sensitive plan contents.

**Given** a production-impacting change is proposed
**When** recovery evidence is evaluated
**Then** rollback or forward-fix instructions identify a known-good compatible identity, launch-disablement order, generation retirement, evidence drain/quarantine, fresh-plan restore, state/address migration considerations, application compensation, recovery objective, and verification
**And** generic instructions such as "revert the commit" do not satisfy the gate.

**Given** rollback is required
**When** the protected recovery workflow executes
**Then** it disables launch first, retires the affected generation, reconciles in-flight evidence, creates a fresh plan for the known-good identity, and applies it through normal target, policy, readiness, and approval controls
**And** it never reuses a stale binary plan or deletes evidence as part of rollback.

**Given** deployment succeeds
**When** post-apply verification runs
**Then** it verifies target identity, lifecycle acknowledgement, schedule state, expectation horizon, task revision, private networking, log subscription, occurrence processing, alarms, and alert route as applicable to the change
**And** failed verification creates an actionable failed deployment result and invokes the reviewed rollback or forward-fix decision.

**Given** recovery completes
**When** launch-resume criteria are evaluated
**Then** scheduling, ECS launch, task events, completion logs, occurrence state, deadlines, notification delivery, and required application compensation are verified within the recorded recovery objective
**And** launch remains disabled while any blocking verification is unresolved.

**Given** evidence contains sensitive data
**When** it is stored or displayed
**Then** secret values, raw CONFIG, binary plans, credentials, unrestricted logs, and sensitive application data are excluded or retained only in access-controlled artifacts with explicit expiry
**And** non-sensitive audit and rollback evidence follows the organizational retention policy.

**Given** emergency or break-glass action affects production
**When** evidence is recorded
**Then** actor, independent approval, reason, exact scope, start/expiry, commands, resulting Deployment Identity, verification, alert receipt, and post-incident review are retained
**And** emergency authority cannot rewrite or delete prior deployment evidence.

**Given** evidence and rollback controls are tested
**When** success, partial apply, failed apply, stale identity, changed address, verification failure, rollback, forward-fix, compensation, and emergency scenarios run against fixtures
**Then** every result remains attributable and only a fresh compatible recovery plan can mutate the target
**And** rollback preserves logs, occurrences, CONFIG, task revisions, and audit history.

### Story 3.7: Publish Immutable Platform Releases

As a Platform Owner,
I want modules, workflows, runtimes, and contracts published as one attributable immutable release,
So that consumers can pin exactly what was tested and deployed.

**Acceptance Criteria:**

**Given** a platform change is proposed for release
**When** semantic-version classification runs
**Then** fixes and non-breaking documentation map to patch, backward-compatible capabilities map to minor, and breaking interface/schema/workflow/behavior changes map to major
**And** automated comparison rejects a classification inconsistent with changed inputs, outputs, schemas, fixtures, workflow contracts, resource addresses, or documented behavior.

**Given** a release candidate is assembled
**When** qualification prerequisites are checked
**Then** credential-free validation, module/examples, contracts, runtime tests, policy fixtures, IAM-negative tests, schedule/reducer suites, trusted-plan checks, and required disposable-Cell evidence for that release class are complete
**And** missing, stale, mismatched, or failed evidence blocks publication rather than being waived by a release note.

**Given** compatibility data is recorded
**When** the release manifest is generated
**Then** it lists exact source commit, semantic version, Terraform/provider/Python/Fargate tested matrix, Cell/module/workflow/contract versions, schema ranges, policy bundle, known limitations, checksums, and required migration class
**And** dated test versions are distinguished from permanent constraints and managed-runtime exceptions are explicit.

**Given** release validation passes on the authorized commit
**When** artifacts are published
**Then** Terraform modules use an immutable internal version or commit, reusable workflows use a full commit SHA, runtime artifacts use immutable digests, and contracts/policy bundles use version plus checksum
**And** no moving branch, mutable tag alone, floating Action, mutable image, or rewritten artifact is accepted as release identity.

**Given** publication occurs across internal repositories or registries
**When** provenance is recorded
**Then** every artifact links to the same release manifest, source commit, builder workflow SHA/run, checksums, qualification evidence, OIDC actor, and publication timestamp
**And** no long-lived credential, untrusted pull-request artifact, or manually rebuilt binary can enter the release.

**Given** consumers reference a release
**When** validation runs
**Then** module sources use immutable registry versions or commits, workflows and Actions use full SHAs, runtime images use digests, provider locks are committed, and contract checksums match
**And** mutable references or unexpected dependency selection fail production policy.

**Given** release notes are published
**When** consumers review them
**Then** they describe capabilities, security and operational impact, compatibility, state/address changes, required two-phase actions, known limitations, rollback identity, and whether migration/deprecation stories apply
**And** upgrade notices are sent through the approved GitHub release and internal engineering channels.

**Given** a published artifact is later found defective
**When** response begins
**Then** the immutable artifact is marked affected without being overwritten, a corrected release uses a new version, and consumers receive exact rollback or upgrade guidance
**And** prior known-good artifacts and evidence remain available through the rollback horizon.

**Given** publication controls are tested
**When** fixtures simulate wrong version class, changed source after testing, checksum mismatch, mutable references, missing evidence, untrusted builder, partial multi-repository publication, and duplicate release version
**Then** inconsistent or mutable releases fail closed
**And** a compliant release can be reproduced and verified from its manifest without secret or state access.

### Story 3.8: Migrate Compatible Platform Versions

As a Platform Owner,
I want major platform changes migrated through expand-migrate-contract,
So that active jobs, queued evidence, and rollback paths remain compatible during upgrade.

**Acceptance Criteria:**

**Given** a release changes Cell, module, CONFIG, schema, runtime, workflow, index, or state contracts
**When** migration planning begins
**Then** it inventories affected consumers, active/retired generations, CONFIG versions, occurrences, task attempts, queues/DLQs, replay and rollback horizons, state addresses, policies, and operator procedures
**And** unknown consumers, references, or horizon values block migration.

**Given** a breaking change requires a new major
**When** the expand phase is designed
**Then** additive schemas, indexes, IAM permissions, runtime readers/writers, contract ranges, and workflow support are deployed before any old behavior is removed
**And** the stable Process Manager principal remains unchanged within the existing Cell major.

**Given** current and previous majors coexist
**When** compatibility rules are applied
**Then** both remain interoperable through the longest queue, replay, maximum runtime, retention, investigation, recovery, and rollback horizon
**And** queued or delayed events can still resolve their original schema, CONFIG, runtime, and task-definition identities.

**Given** Terraform resource addresses or state shape must change
**When** migration code is reviewed
**Then** stable addresses are preserved where possible and exact `moved` blocks, import/state procedures, ordering, expected plan impact, and rollback limitations are documented where not
**And** destructive replacement cannot be hidden inside a compatibility upgrade.

**Given** data or index migration is required
**When** migration executes
**Then** it is idempotent, resumable, bounded, observable, attributable, and validated against source/target counts, checksums, schemas, access patterns, and reducer invariants
**And** launch remains disabled for any generation whose required data is incomplete or inconsistent.

**Given** consumers need to adopt the expanded contract
**When** readiness inventory runs
**Then** each job records current identity, target version, validation result, required configuration/code change, owner, due point, and rollback identity
**And** no consumer is marked ready solely because its Terraform plan succeeds.

**Given** migrated data and consumers are ready
**When** cutover occurs
**Then** versioned Lambda aliases, Cell Contract ranges/pointers, workflow manifests, and policy catalogs switch through fresh reviewed plans and protected approvals
**And** the cutover never exposes a mixed unsupported contract or enables a generation lacking acknowledgement and expectations.

**Given** cutover verification fails
**When** rollback begins
**Then** aliases and contract pointers return to the prior known-good compatible version, launch remains or becomes disabled, and retained evidence is replayed only through supported paths
**And** no old schema, CONFIG, runtime, module, or task revision is removed during rollback.

**Given** migration qualification runs
**When** tests exercise current-to-new, previous-to-new, delayed events, DLQ replay, active tasks, schedule generation changes, state moves, partial migration, rollback, and mixed-version failures
**Then** supported combinations preserve occurrence state, exactly-one launch, completion correlation, alerting, and recovery
**And** unsupported combinations fail before side effects with migration guidance.

**Given** migration completes successfully
**When** evidence is published
**Then** source/target versions, consumer inventory, plans, approvals, data checks, cutover timing, verification, rollback result, remaining compatibility horizon, and known limitations are retained
**And** completion does not authorize deprecation removal or lifecycle deletion, which belong to Story 3.9.

### Story 3.9: Deprecate and Retire Platform Versions

As a Platform Owner,
I want deprecated platform versions retired only after consumers and recovery horizons are clear,
So that support obligations end predictably without breaking active or replayable jobs.

**Acceptance Criteria:**

**Given** an input, output, workflow, schema, runtime, policy, or behavior will be deprecated
**When** a backward-compatible release introduces the deprecation
**Then** release notes and machine-readable metadata identify the replacement, warning behavior, affected consumers, migration steps, support status, earliest removal major, owner, and review date
**And** deprecation does not change existing behavior or remove compatibility in that release.

**Given** the support policy is applied
**When** supported-version status is calculated
**Then** the current and previous major remain supported through the documented maximum compatibility horizon unless an approved security emergency policy says otherwise
**And** any deviation names risk, compensating control, migration path, approvers, and exact end date.

**Given** a deprecated version approaches removal
**When** consumer inventory runs
**Then** it identifies every Cell, job, repository, CONFIG, schedule generation, workflow, runtime, queue/DLQ event, rollback identity, owner, and last observed use
**And** unknown ownership, missing telemetry, or unresolved references block retirement.

**Given** consumers are notified
**When** communication executes
**Then** notices use the approved GitHub release and internal engineering channels with version, impact, action, migration guide, deadline, support contact, and rollback guidance
**And** acknowledgement and unresolved exceptions are tracked without exposing secrets or sensitive deployment data.

**Given** a removal release is proposed
**When** production policy evaluates it
**Then** the change requires the documented major version, completed migration evidence, expired support/replay/retention/rollback horizons, no active references, and reviewed destructive plan impact
**And** a warning period alone cannot prove retirement safety.

**Given** a version appears eligible for retirement
**When** the retirement manifest is generated
**Then** it binds exact artifact identities, checksums, consumer inventory, reference proofs, horizon calculations, approvals, expected effects, preservation evidence, and rollback limitations
**And** wildcard versions, tag-only selection, or mutable aliases are prohibited.

**Given** retirement is approved
**When** execution begins
**Then** active aliases, Cell Contract ranges, workflow manifests, documentation, and support metadata stop advertising the retired version through protected fresh-plan changes
**And** physical deletion is delegated only to the Story 1.15 lifecycle principal using the exact retirement manifest.

**Given** a late reference or incompatible consumer is discovered before deletion
**When** retirement verification reruns
**Then** the manifest is invalidated, support status and communication are updated, and the artifact remains intact
**And** launch for an unsupported configuration fails closed with actionable migration guidance.

**Given** a retired artifact has been physically cleaned up
**When** post-retirement verification runs
**Then** current consumers, previous-major support, delayed evidence handling, rollback identities, documentation, monitoring, and canary operation remain healthy
**And** tombstones and audit evidence prevent silent version reuse or historical ambiguity.

**Given** retirement behavior is tested
**When** fixtures cover active consumers, unknown owners, delayed DLQ events, unexpired horizons, stale manifests, changed aliases, emergency deprecation, safe retirement, and post-cleanup validation
**Then** no referenced or supported artifact becomes eligible
**And** only a complete exact manifest can advance to lifecycle cleanup.

## Epic 4: Qualify and Adopt the Production Standard

Job Owners, Platform Engineering, Security, and operations can document, qualify, approve, and evaluate production candidates using complete Runbooks, readiness evidence, split failure qualification, rollback rehearsal, and an owned pilot launch package.

### Story 4.1: Publish the Scheduled Job Adoption Guide

As an Application Engineer,
I want a complete adoption guide and executable examples,
So that I can configure the platform without modifying module internals or reconstructing ECS operational controls.

**Acceptance Criteria:**

**Given** an engineer opens the platform README
**When** they follow the adoption path
**Then** it explains prerequisites, Cell discovery, job reservation, IAM/network preparation, task integration, phase-one publication, Cell acknowledgement, materialization, activation, verification, ownership handoff, and production promotion in execution order
**And** it consistently describes Scheduler-to-Cell-to-ECS delivery rather than the superseded direct Scheduler-to-ECS model.

**Given** a consumer needs module configuration details
**When** they use the input/output reference
**Then** every required and optional input/output documents type, default, validation, sensitivity, operational purpose, security implication, and example
**And** no required behavior is hidden behind an undocumented default or Terraform-state inspection.

**Given** a team integrates its application with the completion contract
**When** it follows application guidance
**Then** examples show how to consume supplied job, Occurrence ID, CONFIG, attempt, task, and Deployment Identity values and emit structured start/success/failure records
**And** the guide states that jobs do not generate Occurrence IDs and success requires both an accepted marker and zero essential-container exit.

**Given** a team reviews security prerequisites
**When** it reads the guide
**Then** it finds explicit guidance for separate roles, permissions boundaries, effective-policy review, source-account/source-ARN conditions, exact `PassRole`, secret-reference modes, private subnets, bounded egress, immutable images, OIDC, state isolation, protected Environments, and exceptions
**And** every unavoidable wildcard or standards deviation is shown with exact justification rather than normalized as a default.

**Given** a team reviews reliability and operations
**When** it reads lifecycle guidance
**Then** it finds at-least-once delivery, idempotency/locking, maximum runtime detection, overlap, occurrence states, alarms, manual rerun, disablement, two-phase schedule changes, rollback/forward-fix, evidence preservation, compensation, and Cell recovery boundaries
**And** it does not recommend direct `RunTask`, manual state/table edits, schedule mutation outside Terraform, or automatic cancellation.

**Given** the reusable module needs a basic example
**When** repository structure is inspected
**Then** `modules/ecs-scheduled-job/examples/basic` contains a secret-free non-production configuration using existing infrastructure inputs, immutable references, protected tags, retained logs, and documented outputs
**And** it initializes and validates independently without a backend or committed `.tfvars`.

**Given** a production example is provided
**When** it is validated
**Then** it demonstrates private networking, immutable image, occurrence-aware completion, notification routing, required alarms, completed Runbook/readiness references, protected workflow, state isolation, and two-phase activation using placeholders only for externally supplied identifiers
**And** it cannot be applied as production-ready while required launch-checklist values remain unresolved.

**Given** a consumer selects toolchain versions
**When** it reads `versions.tf` and compatibility documentation
**Then** both state Terraform `>= 1.10, < 2.0`, the dated tested Terraform/provider/Python/Fargate seeds, immutable dependency rules, managed-runtime exceptions, and supported Cell/module/contract/workflow matrix
**And** tested patch versions are distinguished from permanent constraints.

**Given** a team changes schedule, image, IAM, networking, secret references, module version, or resource addresses
**When** it follows change guidance
**Then** review classification, stable-address or `moved` migration, generation replacement, expected plan impact, Deployment Identity, verification, rollback, and application compensation are explicit
**And** moving references, destructive replacement, and cleanup during rollback are prohibited.

**Given** an engineer follows the basic example from a clean checkout
**When** hands-on setup is timed
**Then** the documented path can be completed without module-source changes and targets less than four engineering hours
**And** external approvals, infrastructure prerequisites, and waiting time are measured separately.

**Given** documentation or examples change
**When** CI runs
**Then** links, generated references, formatting, Terraform validation for every example, contract versions, policy scans, immutable pins, prohibited artifacts, and security assertions are checked
**And** stale, contradictory, insecure, non-executable, or secret-bearing guidance blocks release.

### Story 4.2: Complete an Actionable Job Runbook

As an On-call Engineer,
I want a job-specific Runbook tied to platform alerts and controls,
So that I can diagnose, rerun, escalate, and recover without guessing.

**Acceptance Criteria:**

**Given** a team prepares a production job
**When** it completes the Runbook template
**Then** the Runbook records canonical job ID, owners/escalation, account, Region, Environment, schedule/time zone, expected runtime, overlap policy, idempotency/locking, dependencies, notification target, Deployment Identity location, recovery objective, and support hours
**And** unresolved ownership, placeholder values, or missing external prerequisites block production readiness.

**Given** the platform-owned canary exists
**When** this story is accepted
**Then** a completed canary Runbook contains real non-secret fixture identifiers or discoverable outputs and no unresolved procedural placeholders
**And** it serves as the tested reference without embedding account-specific values in the reusable template.

**Given** the Job Completion Contract
**When** the Runbook documents expected behavior
**Then** it explains structured start/success/failure records, authoritative occurrence fields, marker-plus-zero-exit correlation, deadline behavior, late/duplicate/conflicting evidence, and every occurrence state
**And** it does not treat Scheduler delivery, log presence, a marker, or exit code alone as completion.

**Given** an alert is received
**When** the operator follows alarm mapping
**Then** every schedule-delivery, launch, runtime, completion, deadline, log-delivery, alert-routing, and Cell-health alert links to its first query, expected evidence, decision point, owner, escalation, and response
**And** every required production alert maps to at least one tested procedure.

**Given** an operator investigates one occurrence
**When** they use documented console, CLI, or query commands
**Then** they can locate ledger state, immutable CONFIG identity, task ARN/events, essential-container exit, structured logs, Scheduler/queue evidence, deadline evidence, alert receipts, and Deployment Identity
**And** commands use the operator role and never workload roles, direct table mutation, secret output, or Terraform-state inspection.

**Given** an occurrence is failed, missed, overdue, or ambiguous
**When** state-specific guidance is followed
**Then** the operator can distinguish delivery, launch, runtime, completion, dependency, and shared-Cell failures
**And** guidance identifies when to wait for reconciliation, disable launch, escalate, rerun, restore, or begin compensation.

**Given** a manual rerun is considered
**When** the checklist is followed
**Then** it requires authorization, original occurrence/Deployment Identity review, overlap/duplicate assessment, compensation acknowledgement, authenticated command execution, and marker-plus-exit verification
**And** direct `RunTask`, caller-created Occurrence IDs, schedule edits, and stale CONFIG are prohibited.

**Given** rollback or forward-fix is required
**When** recovery guidance is followed
**Then** it identifies the known-good identity, launch-disablement order, generation retirement, evidence drain/quarantine, fresh-plan deployment, state/address considerations, verification, recovery objective, and data-compensation steps
**And** launch cannot resume until scheduling, tasks, logs, occurrence state, deadlines, alerts, dependencies, and compensation are verified.

**Given** a job can affect application or shared data
**When** side effects are documented
**Then** idempotency keys, locking, partial writes, reconciliation, rollback limits, and compensating actions are explicit
**And** infrastructure rollback is never represented as automatically undoing application effects.

**Given** the completed canary Runbook is exercised
**When** a responder who did not author it performs a tabletop or non-production test
**Then** they diagnose representative failures and execute the safe escalation, rerun, disablement, or recovery path
**And** elapsed time, missing access, stale commands, ambiguous decisions, and corrections are recorded.

**Given** job behavior, contracts, alerts, ownership, dependencies, or Deployment Identity changes
**When** readiness runs
**Then** the Runbook version and reviewed source revision must match the proposed generation
**And** stale Runbooks, broken links, secrets, unsafe commands, missing alarm mappings, or unresolved placeholders block production.

### Story 4.3: Automate the Production Readiness Gate

As a Production Approver,
I want production readiness backed by attributable machine-verifiable evidence,
So that no job generation is activated with missing security, reliability, or operational controls.

**Acceptance Criteria:**

**Given** a job is proposed for production
**When** the readiness workflow starts
**Then** it creates a versioned evidence record bound to repository/source commit, workflow SHA, plan checksum, Deployment Identity, account, Region, Environment, job ID, CONFIG hash, schedule generation, Cell version, policy bundle, and target manifest
**And** evidence from another revision, target, plan, job, generation, or run cannot satisfy the gate.

**Given** technical validation has completed
**When** evidence is collected
**Then** it includes formatting, Terraform validation, module/examples, contracts, runtime tests, provider-lock verification, security scans, IAM analysis, policy results, representative plan impact, immutable image proof, Cell compatibility, target verification, and address-migration checks
**And** every item records tool/policy version, timestamp, result, artifact checksum, and sensitivity classification.

**Given** production infrastructure controls are evaluated
**When** the gate checks required categories
**Then** it verifies ownership/tags, boundaries, least-privilege roles, confused-deputy conditions, secret references, private networking, bounded egress, public-IP prohibition, encrypted state, retained logs, occurrence-aware completion, alarms, notification routing, and exact lifecycle acknowledgement
**And** absent, contradictory, stale, or placeholder outputs block readiness.

**Given** operational readiness is evaluated
**When** human-reviewed evidence is checked
**Then** the completed Runbook, alarm mapping, runtime/overlap/idempotency declaration, escalation, rollback/forward-fix, compensation, recovery objective, known limitations, and post-deployment verification plan are required
**And** each attestation is attributable and bound to the exact Deployment Identity.

**Given** failure-qualification evidence is required
**When** this story's gate logic is tested
**Then** controlled Compatibility Package fixtures prove the gate accepts complete signed schedule, launch/runtime, completion/alert, security, and recovery evidence and rejects every missing or mismatched category
**And** real production readiness remains blocked until later qualification stories produce equivalent evidence from the target release and disposable Cell.

**Given** approval roles are determined
**When** readiness approval is requested
**Then** Platform Engineering and the Job Owner are mandatory, while the versioned qualifying-change catalog determines whether Security or another control owner must approve
**And** self-approval, placeholder approvers, stale reviews, unknown policy versions, or approval for another revision are rejected.

**Given** an item is missing or failed
**When** readiness is evaluated
**Then** production activation remains blocked with an exact remediation, evidence owner, and resolution point
**And** a free-form comment, lower-Environment result, or manual workflow input cannot convert it to success.

**Given** an approved control supports an exception
**When** the gate evaluates it
**Then** exact policy/resource, owner, justification, approver, expiry/review date, compensating control, source, target, plan, and audit trail are required
**And** broad, expired, mismatched, changed-plan, or non-exemptible exceptions fail.

**Given** readiness completes
**When** its decision is published
**Then** it emits a checksum-bound pass/fail/exception/limitation record conforming to the Story 3.5 readiness schema and an authorized reviewer summary with access-controlled evidence links
**And** the summary excludes secret values, binary plans, credentials, raw CONFIG, unrestricted logs, and sensitive application data.

**Given** any bound input or evidence changes
**When** activation preflight revalidates readiness
**Then** the decision is invalidated and must be recomputed and reapproved
**And** only a current passing exact-generation decision can authorize the production phase-two plan.

**Given** readiness logic changes
**When** positive and negative fixtures run
**Then** every mandatory category, exception rule, approval classification, mismatch, expiry, and invalidation path has deterministic coverage
**And** policy or schema changes cannot silently reduce required evidence.

### Story 4.4: Qualify Schedule Delivery and Expectations

As a Platform Engineer,
I want the release candidate tested against schedule and expectation failure modes,
So that production missed-run detection is proven independently of successful task delivery.

**Acceptance Criteria:**

**Given** a release candidate is ready for schedule qualification
**When** the qualification suite starts
**Then** it deploys a platform-owned canary through the standard workflow into an isolated disposable non-production Cell
**And** it records the release version, Compatibility Package, account, Region, Cell identity, test configuration, policy versions, and evidence checksums.

**Given** supported schedule forms are exercised
**When** the suite evaluates representative cron, rate, time-zone, daylight-saving, anchored, and adjacent-window cases
**Then** the authoritative schedule contract produces the documented occurrence identifiers and windows
**And** ambiguous, unsupported, malformed, or out-of-horizon schedules fail closed with attributable diagnostics.

**Given** expectations must be independent of delivery
**When** the suite materializes at least 24 hours of expected occurrences
**Then** those expectations exist before and without successful Scheduler delivery
**And** their identity, generation, due time, completion deadline, and lifecycle remain deterministic across retries and reconciliations.

**Given** a schedule generation changes during the test
**When** old and new windows overlap
**Then** occurrences remain bound to the correct generation without gaps, reuse, or cross-generation completion
**And** retirement follows the documented ownership and lifecycle rules.

**Given** Scheduler target denial, throttling, retry exhaustion, dropped delivery, DLQ evidence where configured, or a silent delivery path is injected
**When** the relevant occurrence reaches its deadline without a valid launch
**Then** the occurrence becomes `MISSED` or the contractually equivalent terminal state
**And** the platform emits the correct occurrence alert and shared-Cell health signal without relying on a success log marker.

**Given** Scheduler performs at-least-once retries
**When** duplicate delivery attempts reach the Cell
**Then** the occurrence identity is idempotently correlated to exactly one accepted launch
**And** duplicate attempts do not create duplicate ECS tasks or overwrite terminal evidence.

**Given** schedule delivery later recovers
**When** reconciliation evaluates the affected window
**Then** existing terminal results are preserved, unresolved occurrences are handled by the documented policy, and delayed evidence cannot satisfy another occurrence
**And** the test distinguishes recovery from an unauthorized manual rerun.

**Given** the required failure cases are active
**When** monitoring evaluates the Cell
**Then** detection and alert evidence is produced within five minutes of the applicable deadline or platform-failure threshold
**And** alert routing, deduplication identity, ownership metadata, and acknowledgement evidence match the test manifest.

**Given** the same Cell runs twenty consecutive healthy schedule windows
**When** the qualification suite evaluates its results
**Then** every expected occurrence is launched and correlated once with zero false missed-run or Cell-health alerts
**And** any ambiguous, duplicate, late, or missing result fails qualification.

**Given** qualification completes or aborts
**When** cleanup runs
**Then** disposable schedules, tasks, roles, logs, expectations, and Cell resources are removed or retained only by an explicit evidence-retention policy
**And** cleanup preserves sanitized, immutable, checksum-bound qualification evidence without exposing secrets or customer data.

**Given** the evidence package is submitted to production readiness
**When** Story 4.3 validates it
**Then** only the schedule interpretation, expectation independence, Scheduler delivery, idempotency, timing, and healthy-window categories are satisfied
**And** unrelated launch, runtime, completion, security, or recovery categories remain unsatisfied until their dedicated qualification stories pass.

### Story 4.5: Qualify ECS Launch and Runtime Failures

As a Platform Engineer,
I want the release candidate tested against ECS launch and runtime failure modes,
So that production jobs cannot be approved until task execution behavior is deterministic and observable.

**Acceptance Criteria:**

**Given** the schedule qualification has passed
**When** ECS launch and runtime qualification starts
**Then** it uses the same release candidate and an isolated disposable non-production Cell with platform-owned canary fixtures
**And** it records the Compatibility Package, account, Region, Cell identity, task definition, Deployment Identity, injected fault, expected result, and evidence checksums.

**Given** the Cell calls `RunTask`
**When** ECS returns an HTTP error, throttling response, timeout, or an HTTP-success response containing a non-empty `failures` collection
**Then** the occurrence records an attributable launch failure without claiming a task was accepted
**And** retry behavior follows the bounded contract without producing an untracked or duplicate task.

**Given** ECS accepts a task launch
**When** the launch handler crashes, times out, or loses its response before persisting the result
**Then** reconciliation identifies the accepted task by the occurrence and Deployment Identity
**And** repeated processing converges on exactly one correlated task rather than launching another task blindly.

**Given** a task cannot start because of image pull, secret retrieval, ENI allocation, capacity, execution-role, or task-definition failure
**When** ECS reports the stopped or pending failure
**Then** the occurrence captures the task ARN, stop code, reason, timestamps, and responsible boundary
**And** the correct job or shared-Cell alert is emitted without exposing secret values.

**Given** a task starts successfully
**When** it exits unexpectedly, is externally stopped, exceeds the detection-only runtime threshold, or exits with a non-zero code
**Then** the occurrence transitions according to the authoritative state machine and retains immutable runtime evidence
**And** a zero exit code is never inferred from task launch, start, or absence of an error event.

**Given** a canary task starts and exits normally with code zero
**When** ECS evidence is reconciled
**Then** the launch and runtime portions of the occurrence are recorded exactly once
**And** completion success remains unresolved until the separate occurrence-bound completion contract is satisfied.

**Given** duplicate, delayed, reordered, or conflicting ECS events are delivered
**When** reconciliation processes them
**Then** monotonic transition and evidence-precedence rules preserve the correct task and occurrence history
**And** ambiguity is surfaced explicitly rather than silently converted to success or failure.

**Given** an ECS task belongs to another job, generation, account, Region, or Cell
**When** its evidence reaches the qualification target
**Then** correlation is rejected or quarantined with an attributable diagnostic
**And** it cannot satisfy or mutate the canary occurrence.

**Given** each required failure is injected
**When** detection and alerting are measured
**Then** actionable evidence is available within five minutes of the relevant ECS signal or runtime threshold
**And** ownership, routing, deduplication identity, task metadata, and remediation links match the qualification manifest.

**Given** twenty consecutive healthy launch and runtime cases execute
**When** results are evaluated
**Then** each occurrence has exactly one accepted task, correct start and stop evidence, and zero false launch or runtime alerts
**And** any missing task, extra task, unbounded retry, ambiguous state, or unattributed failure fails qualification.

**Given** qualification completes or aborts
**When** cleanup and evidence publication run
**Then** injected faults and disposable resources are removed safely while required sanitized evidence is retained immutably
**And** Story 4.3 marks only ECS launch, reconciliation, runtime, timing, and healthy-run categories as satisfied, leaving completion, security, and recovery categories open.

### Story 4.6: Qualify Completion, Deadlines, and Alert Durability

As an SRE,
I want the occurrence completion and alerting paths tested under failure, delay, and replay,
So that every production occurrence reaches a trustworthy result and actionable alerts are not silently lost.

**Acceptance Criteria:**

**Given** a canary occurrence has started
**When** the job reports `job_name`, occurrence ID, start time, completion time, status, exit code, and the configured success marker through the approved authenticated path
**Then** success is accepted only when the evidence matches the expected job, generation, task, and occurrence and agrees with ECS zero-exit evidence
**And** the resulting transition is attributable, monotonic, immutable, and idempotent.

**Given** a task exits zero without a valid success marker or reports a success marker without verified zero exit
**When** completion is evaluated
**Then** the occurrence does not become successfully completed
**And** it becomes overdue, failed, or ambiguous according to the authoritative deadline and evidence-precedence contract.

**Given** completion evidence contains a wrong, unknown, retired, future, or cross-job occurrence ID
**When** the completion path processes it
**Then** the evidence is rejected or quarantined without mutating any valid occurrence
**And** the diagnostic identifies the violated contract without leaking application payload or secrets.

**Given** completion evidence is delayed, duplicated, reordered, or replayed
**When** it arrives before or after the completion deadline
**Then** exact duplicates remain idempotent, late evidence is retained without erasing the prior deadline decision, and evidence cannot satisfy a different occurrence
**And** conflicting status, exit code, task, generation, or completion claims produce an explicit ambiguous result and alert.

**Given** a started occurrence produces no valid completion signal
**When** its configured completion window expires
**Then** the occurrence becomes `OVERDUE` or the contractually equivalent terminal state independent of log-marker aggregation
**And** the configured production occurrence alert is created within five minutes of the deadline.

**Given** an expected occurrence never starts
**When** its launch and completion deadlines expire
**Then** the platform distinguishes missed launch from started-but-overdue completion
**And** both cases preserve the expected occurrence identity, relevant evidence, ownership, and distinct remediation.

**Given** the deadline index is temporarily stale, throttled, or unavailable, or the deadline scanner restarts mid-page
**When** scanning resumes
**Then** bounded overlap and authoritative item reads find every due occurrence without an unbounded full-table scan
**And** duplicate evaluation does not duplicate terminal transitions or alert obligations.

**Given** an evidence or deadline batch contains poison, malformed, unauthorized, and valid records together
**When** partial-batch handling runs
**Then** valid records progress while failed records are isolated for bounded retry or quarantine
**And** one bad record cannot acknowledge, drop, or indefinitely block unrelated occurrence evidence.

**Given** a terminal failure creates an alert obligation
**When** the outbox writer, stream consumer, alert router, or notification target fails before or after delivery
**Then** the obligation remains durably replayable until the documented delivery acknowledgement is recorded
**And** retries use a stable deduplication identity while preserving attempt history, route, and final disposition.

**Given** alert delivery fails repeatedly or the alert pipeline stops making progress
**When** the configured consecutive-failure or age threshold is crossed
**Then** the shared-Cell alert-pipeline alarm activates through an independent monitored path
**And** recovery replays pending obligations without silently suppressing the original job alerts.

**Given** each completion and alert failure case is injected
**When** qualification measures detection
**Then** the expected occurrence transition and actionable alert evidence appear within five minutes of the applicable signal, deadline, or pipeline threshold
**And** receipts prove correct ownership, route, deduplication, runbook link, and alert content without sensitive values.

**Given** twenty consecutive healthy occurrences complete
**When** the qualification suite evaluates the full path
**Then** every expected occurrence has exactly one accepted start, zero-exit result, occurrence-bound success signal, terminal success state, and no failure alert
**And** duplicate processing, scanner overlap, and alert reconciliation produce zero false positives or ambiguous completions.

**Given** the evidence package is published
**When** Story 4.3 validates it
**Then** only completion correlation, deadline processing, missed-versus-overdue classification, durable alerting, pipeline health, timing, and healthy-window categories are satisfied
**And** security and recovery categories remain open until their dedicated qualification stories pass.

### Story 4.7: Prove Security and Delivery Boundaries

As a Security Reviewer,
I want adversarial qualification of platform identities and control boundaries,
So that production approval is based on demonstrated least privilege rather than configuration intent alone.

**Acceptance Criteria:**

**Given** a release candidate and disposable qualification Cell
**When** security qualification starts
**Then** it deploys only synthetic platform-owned jobs and identities through the standard delivery workflow
**And** the manifest binds every positive and negative fixture to the release, Compatibility Package, account, Region, policy version, expected authorization result, and evidence checksum.

**Given** an untrusted or wrongly scoped principal forges schedule, launch, ECS, or completion evidence
**When** it targets a valid occurrence
**Then** authentication or authorization rejects the evidence before state mutation
**And** the denial is attributable without disclosing credentials, tokens, secret values, or sensitive payloads.

**Given** a valid job identity submits evidence for another job, generation, task, occurrence, account, Region, or Cell
**When** correlation and authorization run
**Then** the request is rejected or quarantined and cannot advance either occurrence
**And** tests cover cross-job confused-deputy and replay attempts with otherwise valid signatures.

**Given** a consumer attempts to reserve an existing namespace, impersonate an owner, or transfer a job identifier
**When** registration is evaluated
**Then** squatting and unauthorized mutation fail closed
**And** an approved ownership transfer requires the documented identities, approvals, audit record, and generation-safe lifecycle.

**Given** application, CI, task, operator, and platform runtime roles are exercised
**When** they attempt direct writes to the occurrence ledger, CONFIG registry, expectation store, alert outbox, or protected control records
**Then** all access outside the explicitly assigned platform path is denied
**And** permitted reads and writes are constrained by resource, action, namespace, condition, and permissions boundary.

**Given** a job or workflow principal attempts arbitrary `ecs:RunTask` or `iam:PassRole`
**When** IAM evaluates task definition, cluster, passed role, source identity, account, Region, tags, and service conditions
**Then** only the exact authorized Deployment Identity path succeeds
**And** wildcard, cross-job, cross-account, alternate-role, untagged, and stale-generation attempts are denied by deterministic fixtures and IAM analysis.

**Given** GitHub OIDC delivery roles are tested
**When** trusted and untrusted repository, ref, workflow, environment, audience, and subject claims request access
**Then** only the versioned approved claim set can assume the matching validation, plan, or apply role
**And** pull-request code, forks, self-approval, administrator bypass, or a non-production identity cannot apply production changes.

**Given** Terraform state and plan artifacts exist
**When** unauthorized identities or workflows attempt to read, alter, unlock, replace, or reuse them
**Then** backend encryption, locking, access policy, retention, and source/target/checksum bindings prevent the action
**And** authorized recovery access is attributable, time-bounded where supported, and separately reviewed.

**Given** network controls are evaluated
**When** fixtures request public IPs, public subnets, broad ingress, unrestricted egress, cross-Cell access, or unapproved endpoints
**Then** policy and infrastructure controls block the configuration before production activation
**And** the compliant private-subnet path reaches only declared dependencies through the minimum security-group and endpoint rules.

**Given** secret-handling fixtures are scanned and planned
**When** plaintext values appear in Terraform inputs, normal container environment variables, state, plans, logs, workflow output, or evidence packages
**Then** the checks fail without echoing the value
**And** only approved Secrets Manager, SSM Parameter Store, or approved external-secret references with scoped runtime access pass.

**Given** an operator attempts rerun, launch disablement, generation change, quarantine release, alert suppression, or recovery
**When** the request bypasses the authenticated command path or lacks required scope and reason
**Then** it is denied without control-state mutation
**And** an authorized request succeeds only against the exact job, occurrence, Environment, and Deployment Identity with an immutable audit record.

**Given** all negative fixtures have run
**When** results are evaluated
**Then** every forbidden action is denied at the intended preventive boundary and produces an attributable control result, while every paired compliant fixture succeeds
**And** unexpected allow, unexpected deny, inconclusive IAM analysis, missing evidence, or reliance on a detective alert alone fails qualification.

**Given** the security evidence package is published
**When** Story 4.3 validates it
**Then** it satisfies identity, namespace, least-privilege IAM, confused-deputy, OIDC, state, networking, secrets, and operator-control categories
**And** access-controlled artifacts expose only sanitized findings and leave recovery qualification open.

### Story 4.8: Rehearse Job and Cell Recovery

As an On-Call Engineer,
I want rehearsed recovery procedures for job generations and shared Cell state,
So that rollback restores controlled service without duplicating work or misrepresenting application recovery.

**Acceptance Criteria:**

**Given** a newly activated job generation is found defective
**When** the job rollback rehearsal begins
**Then** authorized operators disable new launches for the affected generation before infrastructure changes
**And** in-flight tasks, unresolved occurrences, alert obligations, and possible side effects are inventoried and assigned an explicit drain, quarantine, preserve, or compensate action.

**Given** a known-good Deployment Identity has been selected
**When** rollback is planned and approved
**Then** the exact version-pinned configuration produces a fresh reviewable plan bound to the target account, Region, Environment, state, source, and approvers
**And** stale plans, mutable images, direct state edits, schedule edits, or reuse of the failed plan are prohibited.

**Given** the known-good generation is restored
**When** CONFIG acknowledgement and activation complete
**Then** scheduling resumes only after the expected-occurrence horizon, task definition, IAM, networking, logging, completion contract, alarms, and notification route are verified
**And** old and new generations cannot both launch the same occurrence.

**Given** the failed generation launched tasks or changed application data
**When** rollback results are assessed
**Then** infrastructure recovery preserves occurrence history and explicitly records unresolved, duplicate-risk, or partially completed work
**And** application effects are handled through the owner-approved reconciliation or compensation procedure rather than claimed as reversed by Terraform.

**Given** shared Cell state is corrupted, deleted, or found inconsistent
**When** the Cell recovery rehearsal starts
**Then** authorized operators stop or fence new launch mutations, preserve forensic evidence, drain or quarantine ingress, and maintain an independent alert path
**And** the recovery action and scope are bound to an incident identity and immutable audit record.

**Given** a valid point-in-time recovery point has been selected
**When** ledger, CONFIG, expectation, or alert state is restored
**Then** restoration creates fresh encrypted tables or stores rather than overwriting the damaged resources
**And** schemas, indexes, streams, TTL, point-in-time recovery, encryption, tags, resource policies, and Compatibility Package are verified before use.

**Given** restored resources pass structural checks
**When** platform traffic is redirected through the approved stable indirection or contract
**Then** the switch is atomic or ordered to prevent split-brain writers
**And** a failed cutover can return to the previous isolated resources without losing the preserved recovery evidence.

**Given** the recovery point precedes some valid platform events
**When** reconciliation and replay run
**Then** durable Scheduler, ECS, completion, command, and alert evidence is replayed through idempotent interfaces and missing future expectations are rematerialized
**And** occurrence identifiers, terminal-state precedence, task correlation, and alert deduplication prevent duplicate launches or erased outcomes.

**Given** tasks may still be running during Cell recovery
**When** ECS reconciliation inspects the affected Deployment Identities
**Then** accepted, running, stopped, and unknown tasks are matched to restored occurrences before launch is re-enabled
**And** ambiguity remains visible and requires the documented operator decision rather than triggering a replacement task automatically.

**Given** restored state and replay are complete
**When** service verification runs
**Then** the canary proves scheduling, exactly-one launch, logs, completion, deadlines, occurrence alerts, shared-Cell alarms, operator commands, and retained audit history
**And** alert obligations pending before recovery are either delivered with their stable identity or explicitly reconciled with attributable disposition.

**Given** the recovery rehearsal has declared objectives
**When** elapsed time and restored data are measured
**Then** actual recovery time and recovery-point loss are compared with the documented RTO and RPO assumptions
**And** an exceeded objective, unreconciled occurrence, duplicate task, lost alert, broken audit chain, or untested compensation blocks production readiness.

**Given** any recovery step fails
**When** responders invoke the backout path
**Then** launch remains disabled, the last coherent resources stay isolated and recoverable, and escalation identifies the next authorized restore point or forward fix
**And** repeated recovery cannot destroy prior backups, evidence, or the ability to determine application impact.

**Given** the rehearsal evidence is published
**When** Story 4.3 validates it
**Then** it satisfies job rollback, Cell restore, replay, reconciliation, compensation, verification, RPO/RTO, and failed-recovery categories
**And** the evidence is sanitized, checksum-bound, access-controlled, and tied to the exact release candidate.

### Story 4.9: Automate Pilot Measurement and Evidence Packaging

As a Platform Product Owner,
I want pilot results measured from attributable source evidence,
So that adoption decisions compare the platform with the baseline using reproducible data rather than estimates.

**Acceptance Criteria:**

**Given** pilot measurement definitions are versioned
**When** the measurement tool validates them
**Then** it defines start and stop events, units, inclusion rules, exclusions, evidence sources, owners, and calculation methods for every success metric
**And** setup time separates active engineering effort, review effort, approval wait, deployment wait, and unrelated interruption time.

**Given** baseline evidence from recent scheduled-job implementations or pull requests is supplied
**When** the tool ingests it
**Then** it records sample size, repository, period, job complexity classification, evidence provenance, and measured setup and review findings
**And** missing baseline data remains explicitly `UNKNOWN` rather than being replaced by the assumed one-to-three-day range.

**Given** one or two pilot jobs are supplied
**When** their evidence package is ingested
**Then** each pilot is bound to its owner, risk classification, repository, source revision, Deployment Identity, Environment, account, Region, module and workflow versions, pilot window, and approval record
**And** data from another job, revision, generation, or observation window cannot be combined silently.

**Given** delivery workflow evidence is available
**When** setup efficiency is calculated
**Then** the report shows active setup effort, elapsed lead time, review cycles, failed checks, manual interventions, and time to a successful standard deployment
**And** it evaluates the less-than-four-hour target and at-least-50-percent active-effort reduction only when comparable baseline and pilot samples exist.

**Given** pull-request and policy evidence is available
**When** security and review outcomes are calculated
**Then** findings are categorized for IAM scope, tags, alarms, log retention, networking, secrets, image immutability, rollback, and documentation
**And** the report distinguishes findings prevented automatically, found during review, accepted by governed exception, reopened, and unresolved.

**Given** deployed-job evidence is available
**When** control adoption is calculated
**Then** the report verifies required ownership tags, private networking, immutable images, scoped IAM, explicit log retention, occurrence-aware completion, production alarms, notification routing, Runbook, and rollback evidence for each pilot job
**And** a control is counted only when its exact-generation readiness evidence passes.

**Given** operational observation evidence is available
**When** reliability outcomes are calculated
**Then** the report includes expected, started, successful, failed, overdue, missed, duplicate, and ambiguous occurrences; alert detection and delivery latency; false alerts; lost alerts; reruns; incidents; and recovery rehearsal time
**And** denominators, observation windows, exclusions, and unresolved evidence are visible.

**Given** manual survey or interview evidence is supplied
**When** qualitative findings are recorded
**Then** adoption friction, ECS knowledge required, documentation gaps, operational clarity, and requested improvements are attributed to a role and collection date without exposing personal or sensitive data
**And** qualitative feedback is not converted into a quantitative success claim.

**Given** evidence is incomplete, contradictory, duplicated, stale, or outside the declared window
**When** calculations run
**Then** the affected metric is marked `INCOMPLETE`, `INCONCLUSIVE`, or `NOT COMPARABLE` with the exact reason
**And** the tool never fabricates a pass, drops an unfavorable sample, or treats an assumption as measured fact.

**Given** the same validated input package and tool version are used
**When** the report is regenerated
**Then** normalized metrics, comparisons, and decision inputs are deterministic
**And** the output records schemas, calculation version, source checksums, generated timestamp, limitations, and an auditable link to each non-sensitive source.

**Given** pilot data may contain sensitive operational information
**When** it is collected and published
**Then** access, retention, redaction, and artifact classification follow the evidence policy
**And** credentials, secret values, raw Terraform plans, unrestricted logs, and unnecessary application data are excluded.

**Given** no real pilot has yet executed
**When** development validation runs
**Then** synthetic complete, incomplete, contradictory, and non-comparable fixtures prove every calculation and fail-closed path
**And** passing fixture tests validates the measurement capability only, not the external pilot or launch decision.

**Given** a real pilot evidence package is later supplied
**When** measurement completes
**Then** it emits a versioned machine-readable result and concise reviewer report for Story 4.10
**And** the report presents target met, target missed, inconclusive, limitations, and unresolved risks without making the final rollout decision itself.

### Story 4.10: Publish Pilot Launch Checklist and Decision Record

As a Platform Product Owner,
I want a governed pilot checklist and decision record,
So that external pilot execution and broader adoption proceed only when named owners, evidence, and acceptance rules are complete.

**Acceptance Criteria:**

**Given** the MVP implementation is ready for pilot planning
**When** the pilot artifact is generated
**Then** it contains a versioned launch checklist, observation contract, qualifying-change catalog, evidence manifest, approval matrix, rollback criteria, and decision-record schema
**And** each field has an accountable owner, required evidence type, due point, status, and blocking classification.

**Given** pilot job names or owners are still unknown
**When** the checklist is published
**Then** it identifies one or two required low-risk, non-customer-facing maintenance, cleanup, reporting, sync, or internal batch candidates and the intended first-pilot-within-one-sprint target
**And** pilot launch remains `BLOCKED` until exact jobs, application owners, operational owners, repositories, accounts, Regions, Environments, dependencies, side effects, and risk classifications are assigned.

**Given** a candidate pilot is proposed
**When** entry gates are evaluated
**Then** the exact release has passed Stories 4.3 through 4.8, the job uses the standard module and workflows, compatibility is current, and the Runbook, rollback, compensation, immutable image, private networking, scoped IAM, logs, completion contract, alarms, notification route, and ownership metadata are complete
**And** fixture evidence or qualification from another release, Cell, job generation, account, or Region cannot satisfy the gate.

**Given** a pilot includes production execution
**When** launch authorization is requested
**Then** Platform Engineering and the owning application team must approve the exact Deployment Identity, while the qualifying-change catalog requires Security approval for applicable IAM, trust, secrets, state, or networking changes
**And** the configured production notification target, escalation policy, GitHub protected environment, self-review prevention, branch protections, and emergency-bypass policy must be verified rather than left as placeholders.

**Given** pilot observation is planned
**When** the observation contract is approved
**Then** it declares minimum duration and occurrence count, schedule frequencies, healthy windows, controlled failure exercises, alert latency target, false- and lost-alert limits, setup-time method, review-finding categories, recovery rehearsal, incident handling, and stop conditions
**And** changing a threshold or exclusion after observation starts creates a new version and cannot retroactively improve the result.

**Given** a release, contract, policy, module, workflow, IAM, networking, completion, alerting, or recovery behavior changes during the pilot
**When** the qualifying-change catalog evaluates it
**Then** the record identifies which qualification, approvals, observation windows, or pilot evidence are invalidated and must be repeated
**And** editorial or demonstrably non-behavioral changes are exempt only through the versioned deterministic classification rule.

**Given** the checklist is complete and all entry gates pass
**When** authorized reviewers sign the launch record
**Then** its status becomes `APPROVED_TO_START` for only the named jobs, release, Deployment Identities, targets, observation window, and rollback plan
**And** any changed bound input, expired approval, failed preflight, or unavailable alert path returns the record to `BLOCKED`.

**Given** the real pilot runs outside story implementation
**When** implementation artifacts are assessed
**Then** tooling can ingest, validate, and package externally supplied pilot evidence without requiring code changes
**And** synthetic fixtures, a published checklist, or an `APPROVED_TO_START` record cannot be represented as proof that the pilot executed or succeeded.

**Given** a stop condition, severe incident, uncontrolled duplicate, missing alert, security violation, or unrecoverable evidence gap occurs
**When** the pilot is operating
**Then** the checklist directs owners to pause launches, preserve evidence, follow the job or Cell recovery Runbook, assess application compensation, and notify the declared escalation path
**And** restart requires disposition of the failure and fresh approvals required by the qualifying-change catalog.

**Given** the declared pilot window has completed
**When** Story 4.9 produces measured results
**Then** the decision record links every metric, limitation, exception, incident, review finding, recovery result, unresolved risk, and stakeholder attestation to attributable evidence
**And** missing or inconclusive mandatory evidence prevents an `ACCEPTED` decision.

**Given** reviewers evaluate the pilot outcome
**When** they issue a final decision
**Then** the permitted outcomes are `ACCEPTED`, `REMEDIATE_AND_REPEAT`, or `REJECTED`, each with rationale, owners, due actions, scope, effective date, and approval identities
**And** acceptance requires Platform Engineering and the application owner, plus Security or another control owner when the catalog requires it.

**Given** the pilot is accepted
**When** rollout policy is published
**Then** all new ECS scheduled jobs are directed to the standard module, existing jobs migrate as they are materially changed, exceptions follow the governed process, and adoption metrics continue from the pilot baseline
**And** rollout scope, supported versions, support ownership, deprecation communication, and rollback or pause criteria are explicit.

**Given** the checklist or decision machinery changes
**When** automated tests run
**Then** complete, blocked, stale, changed-release, failed-pilot, inconclusive, exception, and accepted fixtures produce deterministic statuses
**And** no default, placeholder, free-form comment, administrator bypass, or missing approver can yield launch authorization or acceptance.
