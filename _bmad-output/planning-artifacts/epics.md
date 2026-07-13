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
---

# demo-bmad - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for demo-bmad, decomposing the requirements from the PRD and Architecture requirements into implementable stories. No UX design contract is in scope for this infrastructure platform service.

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

NFR15: The repository never commits Terraform state, saved plans, `.terraform/`, credentials, or generated secret material, and normal infrastructure workflows do not use provisioners or `null_resource`.

NFR16: Production plans, approvals, exceptions, applies, Deployment Identity, operator actions, and rollback evidence are attributable and retained under organizational policy.

NFR17: Optional views, telemetry dimensions, queues, and retention defaults have documented, configurable cost bounds within platform guardrails.

### Additional Requirements

AR1: Before implementation stories are baselined, the PRD/addendum must be reconciled to the adopted account-local Cell architecture: EventBridge Scheduler sends launch evidence to a policy-isolated queue, the Process Manager assumes a job-scoped launch role and calls ECS, and internal durability/DLQ queues are mandatory while consumer payload DLQs remain deferred.

AR2: Each AWS account-Region pair has one independently deployable shared Platform Cell; the Cell module/state and per-job module/state are separate, and cross-repository consumers use a versioned SSM Cell Contract rather than `terraform_remote_state`.

AR3: An independent EventBridge-rule-driven Occurrence Materializer creates `EXPECTED` occurrences at least 24 hours ahead from immutable, normalized schedule generations; one-time schedules are excluded from MVP and the supported cron/rate/time-zone/DST subset requires conformance fixtures.

AR4: `occurrence/v1` identity is a SHA-256 hash over exact canonical UTF-8 bytes containing canonical job ID, schedule generation, and Unix epoch minute; Scheduler and materializer outputs must match published identity vectors, and the Process Manager recomputes supplied identities.

AR5: Cross-component evidence, CONFIG, state, commands, and alerts use checked-in versioned schemas and canonical encodings; source-specific normalizers stamp identity from authenticated AWS metadata and reject caller-stamped producer or authorization claims.

AR6: Secret-free, content-addressed CONFIG is written to a job-scoped encrypted, versioned S3 inbox, validated and copied by the Cell to a physically separate immutable configuration registry, and hash-verified before every launch; job apply roles cannot write registry or ledger tables.

AR7: One Process Manager is the only runtime-ledger writer and uses a deterministic, commutative reducer so bounded permutations of immutable deduplicated evidence converge on the same state; checked-in transition fixtures prove the behavior.

AR8: MVP permits exactly one platform ECS task attempt per scheduled or synthetic occurrence. Attempt zero, exact CONFIG, stable client token, first-request time, and a conservative retry deadline are transactionally reserved; unresolved launch uncertainty after reconciliation becomes `AMBIGUOUS` rather than another `RunTask` call.

AR9: Authoritative task and log correlation derives from AWS task events, task-ARN ledger mappings, and AWS-generated log subscription metadata. Application-supplied IDs are assertions to validate, and early events remain orphan evidence until their launch mapping exists.

AR10: A durable deadline scanner uses a watermark, bounded lookback, base-table verification, and repeated reconciliation so eventual GSI propagation cannot permanently skip an occurrence deadline.

AR11: SQS/Lambda integrations use partial-batch responses, a maximum receive count of at least five, validated visibility-timeout relationships, 14-day queue retention, DLQs, quarantine behavior, and a processed canary heartbeat.

AR12: Role boundaries include Scheduler delivery, materializer, evidence normalizer, Process Manager, command handler, per-job launch, ECS execution, application task, plan, apply, operator, and break-glass roles with exact trust and authority; CI includes negative authorization tests.

AR13: Platform Lambdas remain outside consumer VPCs and have no inbound public interface. ECS task security groups have no ingress and only approved SG, prefix-list, or CIDR egress; unrestricted Internet egress is a blocking production exception.

AR14: Occurrence ID is never a CloudWatch metric dimension. Bounded job, Environment, state, and Cell-health dimensions are used, while terminal state and a unique alert outbox are committed transactionally and an Alert Router deduplicates delivery through a separate notification ledger.

AR15: The Cell Contract is JSON-Schema validated and publishes Cell/account/Region identity, semantic version, exact integration ARNs, supported schema/config ranges, metric namespace, encryption reference, and checksum; consumers validate identity and compatibility.

AR16: GitHub OIDC uses an organization-customized immutable `sub` containing repository owner/repository IDs, deployment Environment, and full-SHA `job_workflow_ref`, with exact `aud`, separate plan/apply subjects, protected Environments, required reviewers, self-review prevention, restricted refs, and no administrator bypass.

AR17: Module, workflow, Actions, provider, runtime, image, and dependency inputs use immutable versions or digests. Managed-runtime exceptions are explicit, tested, and recorded in Deployment Identity.

AR18: Schedule expression or time-zone changes use two production applies: first disable and drain the old generation, then publish a future-anchored new generation, verify its expectation horizon, and enable Scheduler at the same anchor.

AR19: Initial creation and launch-relevant changes follow the two-phase `RESERVED`, `PUBLISHED`, `VALIDATED`, `MATERIALIZED`, `ENABLED`, and `REJECTED` handshake; phase two may enable only the exact acknowledged generation.

AR20: A Platform-owned namespace registry reserves canonical job IDs and binds Environment/Application prefixes to immutable repository, root, apply-role, account, Region, owner, IAM Role ID, and schedule ARN; duplicate, cross-namespace, stale-role, and unauthorized transfers fail.

AR21: Job IDs follow the architecture's canonical grammar and length limits, protected standard tags cannot be overridden, resource encryption is enabled, production log/occurrence retention defaults to 90 days, non-production logs default to 30 days, ledger PITR is 35 days, and queue retention is 14 days pending reviewer confirmation.

AR22: Every integration edge has exactly one Terraform owner and is documented in the checked-in `contracts/` Compatibility Package, which contains schemas, canonical fixtures, identity vectors, transition permutations, IAM edge catalogs, queue/Lambda constraints, metric/alert catalogs, OIDC rendering, and Cell/job compatibility matrices.

AR23: Cell/module/runtime evolution follows expand-migrate-contract sequencing; the current and previous major remain interoperable through the longest queue, replay, runtime, retention, and rollback horizon, with a stable Process Manager principal within a major.

AR24: Only a dedicated lifecycle principal may garbage-collect CONFIG, task-definition, schema, or runtime versions after proving they are unreferenced across active, replayable, and rollback horizons.

AR25: Production DynamoDB enables 35-day PITR. The Cell recovery runbook restores to new tables, switches versioned aliases and contract pointers, replays post-restore evidence, rebuilds expectations, reconciles nonterminal occurrences, and verifies alerts before launch resumes; measured Cell RPO/RTO are pilot gates.

AR26: Manual reruns, replay, schedule disablement, and recovery use authenticated platform commands. Synthetic reruns have a separate `occurrence/manual/v1` identity and retain actor, approval, reason, Deployment Identity, verification, and compensation acknowledgement; users cannot supply occurrence IDs or arbitrary evidence.

AR27: Cell health covers materializer horizon, evaluator conformance, source and ingress queue age/depth, DLQs, Lambda errors/throttles/duration, deadline lag, log-subscription delivery, canary heartbeat, and alert-outbox reconciliation; Cell-wide incidents notify Platform on-call once while consecutive job failures notify the Job Owner per occurrence.

AR28: Terraform state uses encrypted, versioned, public-blocked S3 backends with native S3 lock files and path-scoped IAM. Production initialization verifies committed provider locks without modification, and the exact approved saved plan is applied.

AR29: Production acceptance includes IAM-negative, schedule-conformance, state-permutation, crash-window idempotency, task-correlation, namespace-claim, evidence-forgery, failure-injection, alert-delivery, rollback, and Cell-recovery tests before pilot promotion.

AR30: The implementation seed includes separate `modules/cell` and `modules/ecs-scheduled-job`, runtime packages for materialization, normalization, processing, log ingestion, deadline scanning, alert routing, commands, and registration, plus `contracts/`, executable examples, unit/contract/integration/failure tests, and operator Runbooks.

AR31: Pilot rollout uses a disposable non-production Cell followed by one or two low-risk jobs with named owners, notification targets, completed Runbooks, approved evaluator subset, verified GitHub controls, tested alarm delivery, measured recovery objectives, and rehearsed rollback before production promotion.

AR32: Rollback disables launch first, retires the affected generation, drains or quarantines evidence, restores a known-good compatible Deployment Identity, replays only safe messages, verifies scheduling/execution/logs/state/alarms, and completes any required application data compensation before cleanup.

### UX Design Requirements

No UX design contract was provided or required for MVP. This is an infrastructure module, runtime service, reusable workflow, and documentation product; its consumer experience requirements are captured in FR1, FR4, FR26, FR27, validation messages, examples, and module interface constraints.

### FR Coverage Map

FR1: Epic 2, Story 2.1 - Declare a complete Scheduled Job through the supported module interface.
FR2: Epic 2, Stories 2.1 and 2.4 - Consume existing account, network, cluster, notification, CI, and secret dependencies.
FR3: Epic 2, Story 2.1 - Apply predictable resource identity and protected standard tags.
FR4: Epic 2, Story 2.8 - Expose the operational identifiers needed to locate and support a job.
FR5: Epic 2, Story 2.3 - Provision a valid ECS Fargate task definition with immutable production image identity.
FR6: Epic 2, Stories 2.5 and 2.6 - Provision the reviewed schedule and occurrence contract through the Cell delivery path.
FR7: Epic 2, Story 2.6 - Configure and document delivery retry and duplicate-handling semantics.
FR8: Epic 2, Story 2.6 - Declare runtime deadlines, overlap safety, and required idempotency or locking.
FR9: Epic 2, Story 2.9 - Perform controlled, attributable manual reruns without schedule edits.
FR10: Epic 2, Stories 2.2 and 2.5 - Separate schedule delivery, job launch, task execution, and application IAM authority.
FR11: Epic 2, Story 2.2 - Declare and review least-privilege application permissions.
FR12: Epic 2, Stories 2.2 and 2.3 - Inject approved secret references without exposing secret values.
FR13: Epic 2, Story 2.4 - Run tasks in private subnets with minimally scoped network access.
FR14: Epic 2, Stories 2.3 and 2.7 - Retain structured occurrence-aware job logs with explicit retention.
FR15: Epic 1, Stories 1.4, 1.7, and 1.9 - Detect and diagnose schedule-delivery failures.
FR16: Epic 1, Stories 1.5 and 1.6 - Detect ECS launch, start, stop, and exit failures.
FR17: Epic 1, Stories 1.4 through 1.8 - Correlate every production occurrence with one authoritative completion outcome.
FR18: Epic 1, Story 1.8 - Route enriched, actionable alerts to the supplied notification target.
FR19: Epic 2, Story 2.8 - Enable bounded-cost operational views without weakening required alarms.
FR20: Epic 3, Stories 3.1 and 3.3 - Validate module and consumer changes safely in pull requests.
FR21: Epic 3, Story 3.4 - Enforce tested production policy gates and governed exceptions.
FR22: Epic 3, Story 3.2 - Authenticate trusted CI paths with exact, short-lived GitHub OIDC identities.
FR23: Epic 3, Stories 3.3 and 3.5 - Separate production plan, approval, and exact-plan apply.
FR24: Epic 3, Story 3.6 - Record Deployment Identity and reviewed rollback evidence.
FR25: Epic 3, Story 3.7 - Publish, support, deprecate, and migrate immutable platform releases.
FR26: Epic 4, Story 4.1 - Provide adoption documentation, references, guidance, and executable examples.
FR27: Epic 4, Story 4.2 - Provide and complete an actionable production Job Runbook.
FR28: Epic 4, Stories 4.3 through 4.5 - Enforce production readiness and pilot acceptance evidence.

## Epic List

### Epic 1: Establish a Trusted Regional Job Platform

Platform Engineering can deploy, secure, observe, test, and recover an account-Region Cell that reliably tracks scheduled occurrences and routes actionable failures.

**FRs covered:** FR15, FR16, FR17, FR18

**Implementation notes:** Establish the Cell Contract, occurrence materialization, evidence normalization, Process Manager, durable ledger, deadline scanning, alert outbox and routing, role boundaries, Cell-health signals, recovery controls, and conformance and failure-injection foundations. This epic is independently testable with fixtures and canary jobs before a consumer module is adopted.

### Epic 2: Deploy a Secure and Operable Scheduled Job

Application teams can declare and operate a private ECS Fargate scheduled job through a stable Terraform interface, including explicit permissions, occurrence correlation, logs, controlled reruns, and optional operational views.

**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8, FR9, FR10, FR11, FR12, FR13, FR14, FR19

**Implementation notes:** Consolidate the consumer module work around task definitions, schedules, CONFIG publication, IAM, networking, logging, alarms, inputs, outputs, and examples. The completed module integrates with the Epic 1 Cell and does not require later delivery or documentation epics to execute a job.

### Epic 3: Deliver and Evolve Jobs Through Governed Automation

Platform and application teams can validate, approve, deploy, identify, roll back, version, and upgrade scheduled jobs through auditable GitHub Actions and immutable releases.

**FRs covered:** FR20, FR21, FR22, FR23, FR24, FR25

**Implementation notes:** Add GitHub OIDC trust, trusted plans, policy gates, protected production applies, Deployment Identity, state protection, semantic releases, compatibility guarantees, and migration controls. This epic operates on the deployable Cell and job capability from Epics 1 and 2 without depending on Epic 4.

### Epic 4: Adopt and Operate the Production Standard

Teams can onboard without deep ECS expertise and demonstrate that every production job is documented, supportable, tested, and ready for controlled pilot rollout.

**FRs covered:** FR26, FR27, FR28

**Implementation notes:** Complete adoption documentation, executable examples, Job Runbooks, production-readiness evidence, failure-injection acceptance, rollback rehearsal, and pilot gates using the working platform from the preceding epics.

## Epic 1: Establish a Trusted Regional Job Platform

Platform Engineering can deploy, secure, observe, test, and recover an account-Region Cell that reliably tracks scheduled occurrences and routes actionable failures.

### Story 1.1: Publish Canonical Cell Contracts

As a Platform Engineering contributor,
I want a versioned Compatibility Package containing the Cell's canonical schemas, identities, fixtures, and integration ownership,
So that every Terraform and runtime component implements the same independently testable contract.

**Acceptance Criteria:**

**Given** the repository contains no established Compatibility Package
**When** this story is implemented
**Then** a checked-in `contracts/` package defines versioned schemas for the Cell Contract, CONFIG, canonical evidence envelopes, occurrence records, commands, and alert events
**And** each schema rejects unknown required fields, invalid versions, malformed identifiers, and secret-value fields.

**Given** the `occurrence/v1` identity contract
**When** identity fixtures are evaluated
**Then** the fixtures specify the exact canonical UTF-8 input bytes and expected SHA-256 result for job ID, schedule generation, and Unix epoch minute
**And** they include valid schedules plus malformed IDs, adjacent occurrences, time-zone boundaries, daylight-saving transitions, and mismatched hashes.

**Given** occurrence evidence may arrive duplicated or out of order
**When** the transition fixture suite is executed
**Then** every bounded permutation of the same immutable evidence reduces to the same expected state
**And** fixtures cover expected, started, succeeded, failed, overdue, missed, duplicate, conflicting, orphan, and ambiguous outcomes without allowing terminal-state overwrite.

**Given** the Cell and job modules have separate Terraform ownership and state
**When** contributors inspect the integration catalog
**Then** every cross-root ARN, permission, schema, configuration handoff, metric, and lifecycle edge has exactly one declared Terraform owner
**And** the catalog prohibits cross-repository `terraform_remote_state`.

**Given** Cell and consumer versions may evolve independently
**When** compatibility validation runs
**Then** the package defines supported Cell, module, CONFIG, evidence-schema, and runtime version ranges for the current and previous major versions
**And** incompatible or unknown major combinations fail with an actionable message.

**Given** a contributor changes a contract or canonical fixture
**When** repository validation runs
**Then** automated contract tests validate schemas, identity vectors, transition fixtures, ownership catalogs, and compatibility matrices
**And** the tests run without AWS credentials, network access, plaintext secrets, or account-specific values.

### Story 1.2: Deploy the Secure Cell Foundation

As a Platform Engineer,
I want to deploy the shared Cell's encrypted storage, messaging, and discovery resources in one account and Region,
So that runtime components and job modules have a durable, isolated platform foundation.

**Acceptance Criteria:**

**Given** an approved account, Region, Environment, retention configuration, and standard tags
**When** the Cell Terraform module is planned
**Then** it provisions resources only in that account-Region pair without hardcoded deployment identifiers
**And** its state and ownership remain separate from every scheduled-job root.

**Given** the Cell requires isolated and durable event delivery
**When** messaging resources are created
**Then** separate source queues exist for Scheduler, materializer, ECS events, completion logs, and commands, with a canonical ingress queue and required DLQs
**And** all queues are encrypted, retain messages for 14 days, use a maximum receive count of at least five, and satisfy the published visibility-timeout constraints.

**Given** job ownership, CONFIG, and runtime state have different trust boundaries
**When** storage resources are created
**Then** namespace ownership, CONFIG registry, occurrence ledger, alert-outbox, and notification-deduplication data are physically separated according to the architecture contract
**And** production DynamoDB resources use encryption, point-in-time recovery, and indexes required for task correlation and deadline processing.

**Given** job roots publish immutable CONFIG candidates
**When** the CONFIG inbox is created
**Then** it uses encrypted, versioned, public-blocked S3 storage with job-scoped prefixes and lifecycle settings compatible with replay and rollback horizons
**And** no job principal receives direct write authority to the CONFIG registry or occurrence ledger.

**Given** a consumer must discover the Cell without reading platform Terraform state
**When** the Cell deployment completes
**Then** it publishes a JSON-Schema-valid SSM Cell Contract containing Cell, account, Region, semantic version, exact integration ARNs, supported version ranges, metric namespace, encryption reference, and checksum
**And** all identifiers and compatibility claims match the deployed resources and Story 1.1 contracts.

**Given** production and non-production retention requirements differ
**When** retention inputs are omitted
**Then** approved defaults are applied for production occurrence data, non-production operational data, queues, and recovery windows
**And** invalid or unbounded retention settings fail validation with an actionable message.

**Given** the Cell module is changed
**When** repository validation runs
**Then** formatting, validation, module tests, contract checks, and security scanning cover encryption, public access, retention, PITR, tags, and cross-state isolation
**And** no state, lock artifacts, credentials, account-specific fixtures, or secret material are committed.

### Story 1.3: Authenticate and Normalize Platform Evidence

As a Platform Security Engineer,
I want every incoming platform event authenticated and converted into a canonical evidence envelope,
So that no producer can forge another job's identity, state transition, or command authority.

**Acceptance Criteria:**

**Given** the Cell receives Scheduler, materializer, ECS, completion-log, or command evidence
**When** Terraform creates source integrations
**Then** each producer uses its own policy-isolated source queue and narrowly scoped delivery role or AWS service policy
**And** source-account, source-resource, queue, and permitted evidence-type restrictions are enforced where supported.

**Given** evidence arrives on an isolated source queue
**When** the evidence normalizer processes it
**Then** producer identity, account, Region, source ARN, job binding, generation, and permitted evidence type are derived from trusted AWS metadata and the namespace registry
**And** caller-supplied identity fields are treated only as assertions to validate.

**Given** a valid source event matches its registered ownership and schema
**When** normalization succeeds
**Then** the normalizer emits a versioned canonical evidence envelope to the canonical ingress queue
**And** the envelope includes deterministic deduplication data, authenticated source context, event time, payload hash, and trace context without secret values.

**Given** a message contains a forged job ID, generation, producer, evidence type, source ARN, or command authority
**When** the normalizer evaluates it
**Then** the message is rejected without writing the runtime ledger or launching ECS
**And** the rejection is quarantined or redriven with a bounded security metric containing no unbounded or secret dimensions.

**Given** a batch contains both valid and invalid source messages
**When** the Lambda invocation completes
**Then** partial-batch response handling acknowledges successful records and retries only failed records
**And** poison messages reach the configured DLQ without blocking unrelated evidence.

**Given** platform runtime roles are provisioned
**When** their effective permissions and trust policies are analyzed
**Then** the normalizer can read only its assigned source queues and write only canonical ingress
**And** it cannot write CONFIG or ledger tables, assume job launch roles, invoke ECS, alter queue policies, or pass IAM roles.

**Given** the normalizer runs as a shared Cell component
**When** it is deployed
**Then** it remains outside consumer VPCs, has no inbound public interface, uses encrypted AWS service endpoints, and publishes logs with explicit retention
**And** contract and negative-security tests prove rejection of cross-job, cross-generation, malformed, replayed, and caller-stamped evidence.

### Story 1.4: Materialize Expected Schedule Occurrences

As an On-call Engineer,
I want expected job occurrences created independently before Scheduler attempts delivery,
So that a missing Scheduler invocation becomes a detectable occurrence failure.

**Acceptance Criteria:**

**Given** an authorized, secret-free CONFIG candidate exists in the job-scoped inbox
**When** the Cell validates it
**Then** the schema, content hash, Cell identity, job ownership, schedule generation, task revision, runtime deadline, and supported version ranges are verified
**And** only a valid immutable snapshot is copied into the separate CONFIG registry.

**Given** a registered recurring schedule uses the supported contract
**When** the materializer evaluates it
**Then** expression, time zone, explicit start anchor, activation window, flexible-window policy, and generation hash are normalized consistently with the Compatibility Package
**And** unsupported expressions, one-time schedules, ambiguous anchors, or invalid daylight-saving behavior are rejected before activation.

**Given** an active schedule generation
**When** the EventBridge scheduled rule invokes the materializer
**Then** deterministic `EXPECTED` evidence is emitted for every occurrence at least 24 hours into the future
**And** each Occurrence ID matches the exact `occurrence/v1` identity vector for job, generation, and Unix epoch minute.

**Given** the materializer is invoked repeatedly or after a partial failure
**When** it emits an occurrence already present in the horizon
**Then** the operation is idempotent and cannot create a second logical occurrence
**And** duplicate or reordered evidence produces the same expected state.

**Given** a schedule generation is retired or replaced
**When** materialization runs
**Then** it does not create occurrences outside that generation's activation window
**And** existing occurrences remain attributable to their immutable original generation and CONFIG.

**Given** Scheduler and the materializer evaluate the same supported schedule fixtures
**When** the conformance suite compares their occurrence times
**Then** they agree across cron and rate expressions, time zones, daylight-saving transitions, and consecutive windows
**And** any mismatch blocks production activation.

**Given** the expectation horizon is no longer advancing safely
**When** freshness approaches exhaustion or evaluation fails
**Then** bounded Cell-health metrics and an actionable Platform alarm fire before the 24-hour horizon is exhausted
**And** the alert identifies the Cell, account, Region, failure plane, and operator Runbook without using Occurrence ID as a metric dimension.

### Story 1.5: Launch Exactly One ECS Task per Occurrence

As a Job Owner,
I want each valid scheduled occurrence to launch no more than one platform-managed ECS task,
So that retries or platform crashes cannot create duplicate workload effects.

**Acceptance Criteria:**

**Given** canonical `EXPECTED` and `LAUNCH` evidence for a registered occurrence
**When** the Process Manager consumes the evidence
**Then** it validates the envelope, recomputes the Occurrence ID, resolves the exact immutable CONFIG, and verifies its canonical content hash
**And** no launch occurs for an unknown job, generation, CONFIG version, activation window, or identity mismatch.

**Given** an occurrence is eligible for its first launch
**When** the Process Manager prepares `RunTask`
**Then** one DynamoDB transaction reserves attempt zero, the exact CONFIG version, deterministic client token, first-request time, conservative retry deadline, and launch state
**And** a duplicate or concurrent launch message cannot reserve another attempt.

**Given** attempt zero is successfully reserved
**When** the Process Manager invokes ECS
**Then** it assumes only that job's launch role and calls `RunTask` with the exact task-definition revision, cluster, subnets, security groups, capacity settings, and public-IP-disabled network configuration from verified CONFIG
**And** it supplies reserved job, occurrence, CONFIG, and attempt values through ECS tags and container overrides.

**Given** ECS returns a task successfully
**When** the response is processed
**Then** the task ARN is conditionally indexed to the occurrence and attempt
**And** the occurrence records launch timing, Deployment Identity, task revision, and authoritative task mapping without accepting identity from application output.

**Given** ECS returns an HTTP error or HTTP 200 with a non-empty `failures[]` and no task
**When** the response is processed
**Then** the occurrence transitions to the appropriate launch-failure state with a sanitized reason
**And** failure evidence is available to the alert path even though no ECS lifecycle event exists.

**Given** the Process Manager crashes after ECS accepts the launch but before the task ARN is recorded
**When** the queue retries the same evidence
**Then** the same ECS client token is reused and existing tasks are reconciled by cluster, Cell tags, and `startedBy=occurrence_id`
**And** exactly one matching task restores the ledger mapping without another logical launch.

**Given** launch outcome remains unresolved or conflicting
**When** the conservative retry deadline is reached, multiple task ARNs are found, parameters differ, or the token conflicts
**Then** the Process Manager makes no further `RunTask` call and marks the occurrence `AMBIGUOUS`
**And** recovery requires a separately authorized synthetic rerun rather than silently creating attempt one.

**Given** Process Manager permissions are analyzed
**When** negative authorization tests run
**Then** it can read canonical ingress and verified CONFIG, update only runtime and outbox records, publish bounded metrics, and assume registered job launch roles
**And** it cannot pass unrelated roles, mutate CONFIG, change schedules, alter its trust path, or launch an unregistered task family or cluster.

### Story 1.6: Correlate Task State and Completion Evidence

As an On-call Engineer,
I want ECS lifecycle events and application completion signals correlated to the authoritative occurrence record,
So that I can distinguish successful, failed, duplicate, delayed, and ambiguous job outcomes.

**Acceptance Criteria:**

**Given** ECS emits a task lifecycle event for the Cell's cluster
**When** the event enters the authenticated evidence path
**Then** task identity is derived from AWS event resource and detail fields and resolved through the task-ARN ledger index
**And** application-supplied job or Occurrence IDs cannot authorize or redirect the event.

**Given** an ECS event arrives before its task mapping is committed
**When** the Process Manager cannot yet resolve the task ARN
**Then** the event is retained as orphan evidence and retried or reconciled within a bounded window
**And** it is neither discarded nor applied to another occurrence.

**Given** a mapped task reaches `RUNNING`
**When** normalized task-state evidence is reduced
**Then** the occurrence records `started_at` and transitions to `STARTED` idempotently
**And** duplicate or reordered start events do not alter the reserved attempt or task mapping.

**Given** the job emits a structured completion record
**When** the log ingestor processes the CloudWatch Logs subscription envelope
**Then** authoritative log identity comes from the AWS-generated log-group and log-stream metadata mapped to the registered job and task
**And** asserted job, occurrence, CONFIG, attempt, status, completion time, exit code, and optional error reason are schema-validated without trusting them as authorization.

**Given** attempt zero has one valid structured success marker and the essential container exits with code zero
**When** both evidence records have been correlated
**Then** the occurrence transitions exactly once to `SUCCEEDED` and records the authoritative completion fields
**And** neither the log marker nor zero exit alone can declare success.

**Given** the task fails to start, stops unexpectedly, or an essential container exits non-zero
**When** task-state evidence is processed
**Then** the occurrence transitions to `FAILED` with sanitized stop code, reason, and exit details
**And** a later success marker cannot overwrite that terminal result.

**Given** completion evidence is duplicated, delayed, conflicting, tied to another occurrence, or associated with multiple task ARNs
**When** the reducer evaluates all immutable evidence
**Then** adjacent-window and wrong-occurrence evidence cannot satisfy the expected occurrence
**And** conflicts produce the documented duplicate or `AMBIGUOUS` outcome rather than silently selecting a result.

**Given** event permutations and failure scenarios are tested
**When** contract and integration suites run
**Then** they cover success, start failure, non-zero exit, missing marker, marker without zero exit, delayed prior completion, duplicate completion, wrong Occurrence ID, retry delivery, early events, and consecutive schedule windows
**And** every permutation converges on the state defined by Story 1.1 fixtures.

### Story 1.7: Detect Overdue and Missed Occurrences

As an On-call Engineer,
I want every due occurrence reconciled against its expected launch and completion deadlines,
So that missing invocations and unfinished jobs cannot disappear because of delayed evidence or index propagation.

**Acceptance Criteria:**

**Given** an expected occurrence reaches its launch deadline without valid launch evidence
**When** deadline evidence is processed
**Then** the Process Manager marks the occurrence `MISSED` according to the canonical transition contract
**And** the record identifies the schedule-delivery failure plane and retains its immutable job, generation, CONFIG, and scheduled-time context.

**Given** a launched or started occurrence reaches its completion deadline without a valid completion result
**When** deadline evidence is processed
**Then** the Process Manager marks it `OVERDUE`
**And** detection does not stop the ECS task or claim that enforced cancellation occurred.

**Given** the deadline scanner is invoked repeatedly
**When** it queries due occurrences
**Then** it advances a durable watermark, uses a bounded lookback, paginates safely, and verifies candidates against the authoritative base-table record
**And** repeated scans and duplicate deadline evidence are idempotent.

**Given** a newly due record is temporarily absent from an eventually consistent deadline index
**When** later scans execute
**Then** the watermark and lookback strategy revisit the affected time range until base-table verification processes the record
**And** no deadline can be permanently skipped because of index propagation delay.

**Given** the scanner crashes after reading candidates or emitting only part of a batch
**When** the next invocation resumes
**Then** uncommitted candidates are rediscovered and safely re-emitted through the authenticated evidence path
**And** the scanner never writes occurrence state directly.

**Given** valid, late, duplicate, or conflicting evidence arrives after deadline evidence
**When** the Process Manager reduces the complete evidence set
**Then** the result follows the canonical deterministic transition fixtures
**And** a late signal cannot silently overwrite a terminal missed, overdue, failed, or ambiguous outcome.

**Given** deadline processing falls behind or stops
**When** scanner lag, errors, throttling, or stale watermark exceed configured thresholds
**Then** bounded Cell-health metrics trigger an actionable Platform alarm before required detection windows are breached
**And** the alarm includes Cell, account, Region, failure plane, and Runbook context.

**Given** deadline behavior is tested
**When** unit and integration suites run
**Then** they cover no launch, start without completion, zero exit without success marker, delayed index visibility, duplicate scans, pagination boundaries, scanner restart, and late evidence
**And** required failures are detected within five minutes of the observable deadline during accelerated acceptance tests.

### Story 1.8: Deliver Actionable Occurrence Alerts Reliably

As an On-call Engineer,
I want every terminal job failure delivered once with complete diagnostic context,
So that I can identify the affected occurrence and begin the correct response without reconstructing the event manually.

**Acceptance Criteria:**

**Given** an occurrence transitions to `FAILED`, `MISSED`, `OVERDUE`, or `AMBIGUOUS`
**When** the Process Manager commits the terminal state
**Then** the same DynamoDB transaction creates a unique alert-outbox record for that occurrence, state, and failure event
**And** a state commit cannot succeed without its corresponding outbox record.

**Given** a new outbox record exists
**When** the Alert Router receives its DynamoDB Streams event
**Then** it resolves the immutable job notification metadata and publishes to the configured target
**And** the alert includes job, Occurrence ID, state, failure plane, account, Region, Environment, detection time, Deployment Identity, sanitized reason, and Runbook link.

**Given** an alert payload is constructed
**When** schema and security validation run
**Then** it contains no secret values, raw CONFIG body, unrestricted log content, or sensitive Terraform data
**And** it conforms to the versioned alert contract from Story 1.1.

**Given** the Alert Router is retried or receives duplicate Stream records
**When** it attempts delivery
**Then** a conditional notification-ledger record deduplicates the occurrence alert
**And** duplicate processing does not produce duplicate notifications for the same alert identity.

**Given** two consecutive scheduled occurrences fail
**When** each terminal transition is committed
**Then** each occurrence produces its own Job Owner notification even if an aggregate CloudWatch alarm remains in `ALARM`
**And** the distinct Occurrence IDs remain visible in both the ledger and notification evidence.

**Given** terminal state commits but Stream processing is delayed or unavailable
**When** the outbox reconciliation scan runs
**Then** it discovers and retries every unpublished or unresolved outbox record
**And** no committed terminal failure remains permanently stranded without delivery evidence.

**Given** publication succeeds but the router crashes before recording completion
**When** processing resumes
**Then** notification-ledger and target-delivery semantics prevent or explicitly identify ambiguous duplicate delivery
**And** the outbox retains attributable attempts, timestamps, target identity, and final delivery status.

**Given** Alert Router authority is analyzed
**When** negative IAM tests run
**Then** it can read outbox and notification metadata and publish only to registered notification targets
**And** it cannot mutate occurrence state, CONFIG, schedules, workload roles, or arbitrary SNS topics.

**Given** alert delivery failure scenarios are injected
**When** acceptance tests simulate crashes before publication, after publication, Stream delay, reconciliation, target denial, and duplicate records
**Then** every required occurrence alert is delivered or surfaced as an actionable Cell alert within the defined detection window
**And** accelerated successful occurrences produce no false failure notifications.

### Story 1.9: Monitor Cell Health and Delivery Paths

As a Platform On-call Engineer,
I want bounded health signals and tested alarms for every shared Cell failure plane,
So that platform-wide degradation is detected before scheduled occurrences are silently affected.

**Acceptance Criteria:**

**Given** a production Cell is deployed
**When** its observability resources are created
**Then** metrics and alarms cover expectation-horizon freshness, evaluator conformance, Scheduler attempts and target failures, source and ingress queue age/depth, DLQs, Lambda errors/throttles/duration, deadline-scanner lag, log-subscription delivery, outbox reconciliation, and processed canary freshness
**And** every alarm identifies Cell, account, Region, Environment, failure plane, owner, and Platform Runbook.

**Given** occurrence processing emits operational metrics
**When** metric dimensions are inspected
**Then** dimensions are limited to bounded values such as Cell, job, Environment, state, and failure plane
**And** Occurrence ID, task ARN, error text, log stream, and other unbounded values are excluded from metric dimensions.

**Given** EventBridge Scheduler cannot deliver launch evidence
**When** target errors, throttling, dropped invocations, or Scheduler DLQ depth breach configured thresholds
**Then** an actionable delivery-path alarm reaches the Platform notification target
**And** independently materialized occurrences still become per-job `MISSED` results at their deadlines.

**Given** the Scheduler or evidence path stops producing messages without reporting a direct error
**When** the Cell canary traverses the scheduled delivery and canonical processing path
**Then** a processed heartbeat proves that evidence reached the expected checkpoint
**And** stale or missing heartbeat detection creates one Cell-wide incident rather than an unbounded alert per internal component.

**Given** a shared Cell fault affects multiple jobs
**When** aggregate alarms enter `ALARM`
**Then** Platform on-call receives a deduplicated Cell incident with affected scope and diagnostic links
**And** the occurrence alert path continues to notify each Job Owner for distinct failed occurrences.

**Given** the Cell returns to healthy operation
**When** recovery thresholds are satisfied
**Then** alarms recover without suppressing unresolved occurrence failures
**And** alarm history, state changes, and notification evidence remain attributable for the required retention period.

**Given** non-production and production Cells have different noise tolerances
**When** alarm settings are configured
**Then** production alarms and routing are mandatory while approved non-production signals may use lower-noise routing
**And** disabling optional non-production alarms cannot disable required Cell health data collection.

**Given** Cell observability changes are validated
**When** automated alarm tests inject Scheduler delivery failure, horizon staleness, queue backlog, DLQ messages, Lambda errors, scanner lag, log-subscription failure, stale canary, and stranded outbox records
**Then** each required failure is detected within five minutes of becoming observable
**And** at least 20 accelerated healthy windows produce zero false alerts.

### Story 1.10: Operate and Recover the Cell Safely

As a Platform On-call Engineer,
I want bounded, attributable operational commands and a rehearsed Cell recovery procedure,
So that I can contain incidents and restore occurrence processing without assuming workload roles or corrupting authoritative state.

**Acceptance Criteria:**

**Given** a responder needs to diagnose or operate a production Cell
**When** access is granted
**Then** the responder assumes a separate short-lived operator role with approval, actor attribution, session limits, and bounded diagnostic and command permissions
**And** the role cannot assume workload roles, write tables directly, alter its own trust, pass unrelated roles, or bypass the command handler.

**Given** an authorized operator submits a replay, rerun, schedule-disablement, or recovery command
**When** the command handler evaluates it
**Then** it verifies actor, approval, command type, registered job or Cell scope, reason, reviewed Deployment Identity, and required compensation acknowledgement
**And** it stamps authoritative identity from system metadata rather than accepting caller-supplied occurrence IDs or evidence.

**Given** an operator authorizes a synthetic rerun
**When** the command is accepted
**Then** the handler creates a UUIDv7 command ID and derives an `occurrence/manual/v1` identity from job, original occurrence, CONFIG, and command ID
**And** the synthetic occurrence retains `replay_of_occurrence_id`, actor, approval, reason, verification, and compensation metadata without mutating the original result.

**Given** break-glass access is necessary
**When** the documented emergency path is invoked
**Then** access is time-bound, independently approved, attributable in CloudTrail, and immediately alerts Platform on-call
**And** the session and resulting actions require post-incident review.

**Given** Cell corruption or data loss requires recovery
**When** the recovery procedure begins
**Then** launch is disabled before state changes, affected evidence is drained or quarantined, and DynamoDB PITR restores data into new tables rather than overwriting the source
**And** the recovery records its restore point, expected RPO/RTO, actor, approvals, and Deployment Identity.

**Given** restored tables are available
**When** the Cell is brought forward
**Then** versioned processor aliases and Cell Contract pointers switch to the compatible recovery generation, post-restore evidence is replayed, future expectations are rebuilt, and nonterminal occurrences are reconciled
**And** scheduling remains disabled until ledger integrity, queue health, completion processing, and alert delivery are verified.

**Given** a runtime or schema upgrade must be rolled back
**When** the known-good version is restored
**Then** expand-migrate-contract compatibility preserves the current and previous major through the longest replay and rollback horizon
**And** incompatible schema, CONFIG, module, or runtime combinations cannot resume launch.

**Given** obsolete CONFIG, task-definition, schema, or runtime versions are eligible for cleanup
**When** garbage collection is requested
**Then** only the dedicated lifecycle principal can delete them after proving they are unreferenced across active, replayable, runtime, retention, and rollback horizons
**And** failed proof leaves the resource intact with an attributable denial record.

**Given** recovery and operator controls are tested before production
**When** exercises simulate schedule disablement, queue replay, synthetic rerun, break-glass, PITR restore, alias and contract switching, expectation rebuild, ambiguous occurrence reconciliation, and alert verification
**Then** measured recovery objectives and evidence are retained for review
**And** launch resumes only after all blocking recovery checks pass.

## Epic 2: Deploy a Secure and Operable Scheduled Job

Application teams can declare and operate a private ECS Fargate scheduled job through a stable Terraform interface, including explicit permissions, occurrence correlation, logs, controlled reruns, and optional operational views.

### Story 2.1: Declare and Reserve a Scheduled Job

As an Application Engineer,
I want to validate and reserve a scheduled-job declaration against the target Platform Cell,
So that my repository has an authorized, collision-free identity before workload resources are created.

**Acceptance Criteria:**

**Given** a consumer root declares a scheduled job
**When** module validation runs
**Then** required inputs cover Environment, Application, job name, owner, repository identity, account, Region, ECS cluster, image, schedule, compute, command, configuration, secret references, permissions, runtime, overlap policy, networking, notification target, and tags
**And** every input has a description, type constraint, meaningful validation, and secret-reference inputs that cannot accept plaintext secret values.

**Given** the target Cell Contract exists in SSM
**When** the module resolves it
**Then** its JSON schema, checksum, Cell identity, account, Region, Environment, semantic version, integration ARNs, and supported CONFIG and evidence ranges are validated
**And** missing, malformed, mismatched, or incompatible contracts fail planning with an actionable message.

**Given** valid Environment, Application, and job-name inputs
**When** canonical identity is derived
**Then** the job ID follows the architecture's grammar, normalization, and length limits
**And** invalid characters, empty segments, reserved prefixes, or names that cannot produce valid AWS resource names fail before apply.

**Given** an authorized repository requests the canonical job ID
**When** the Platform-owned namespace registry evaluates the reservation
**Then** it conditionally binds the ID to immutable repository identity, root path, apply-role identity, account, Region, Environment, Application, owner, and an ownership generation
**And** the lifecycle state becomes `RESERVED` without granting runtime launch authority.

**Given** the same authorized owner retries an identical reservation
**When** the request is processed
**Then** it returns the existing reservation idempotently
**And** a different repository, root, account, Region, or owner cannot claim or overwrite that job ID.

**Given** ownership must move to another repository or application boundary
**When** a transfer is requested
**Then** the existing owner and Platform approver must authorize a recorded ownership-generation change
**And** stale reservations, stale roles, and cross-namespace transfers remain rejected until the approved transfer completes.

**Given** required standard metadata and consumer tags
**When** the module calculates resource tags and names
**Then** Environment, Application, Service, Owner, ManagedBy, Repository, and applicable CostCenter tags are present with predictable names
**And** consumer values cannot remove, empty, or conflict with protected platform tags.

**Given** a declaration is valid and reserved
**When** the consumer runs a backend-free validation or plan
**Then** the module reports the canonical job ID, Cell identity, compatibility result, reservation generation, and normalized declaration without requiring workload resources or direct platform-state access
**And** no account IDs, Regions, repository names, Environment names, credentials, secrets, provisioners, or `null_resource` implementations are hardcoded.

### Story 2.2: Create Least-Privilege Job IAM Roles

As a Security Reviewer,
I want every scheduled job to use separate, reviewable IAM roles with bounded authority,
So that schedule delivery, ECS execution, and application access cannot be combined into an escalation path.

**Acceptance Criteria:**

**Given** a reserved scheduled-job identity
**When** the module creates IAM resources
**Then** it creates distinct job-launch, ECS task-execution, and application-task roles
**And** every platform-created role carries the mandatory permissions boundary and protected ownership tags.

**Given** the Process Manager needs to launch the job
**When** the job-launch trust policy is rendered
**Then** only the exact registered Process Manager principal may assume it, with the narrowest supported account and Cell conditions
**And** the Registrar binds the resulting immutable IAM Role ID to the job reservation before activation.

**Given** the job-launch role invokes ECS
**When** its effective permissions are evaluated
**Then** `ecs:RunTask` is restricted to the intended task-definition family and ECS cluster
**And** `iam:PassRole` is restricted to the exact execution and task roles with `iam:PassedToService = ecs-tasks.amazonaws.com`.

**Given** ECS must pull the image, write logs, and inject agent-managed secrets
**When** the task-execution policy is rendered
**Then** it grants only required ECR, exact log-group, exact secret-reference, and required KMS permissions
**And** any AWS-required resource wildcard, such as an authorization-token action, is isolated and documented with its service limitation.

**Given** the application needs AWS API access
**When** explicit application IAM statements are supplied
**Then** they are attached only to the application-task role and remain visible in the Terraform plan
**And** wildcard actions, wildcard resources, privilege escalation, or cross-account access fail production policy unless a governed exception is present.

**Given** a consumer requests a customer-managed policy attachment
**When** the module validates it
**Then** the policy must be same-account, present on an approved allowlist, and governed for policy-version changes
**And** unapproved or externally mutable attachments fail planning.

**Given** a secret reference uses ECS-agent injection
**When** permissions are generated
**Then** access is granted through the task-execution role to the exact Secrets Manager or SSM resource and required KMS key
**And** the secret value never appears in Terraform inputs, plans, CONFIG, logs, or outputs.

**Given** an approved integration requires the application to retrieve a secret at runtime
**When** application-pull mode is selected
**Then** only the task role receives exact secret and KMS access and the networking contract declares the required endpoint
**And** cross-account or external secret access requires validated resource, key, and network policies.

**Given** ECS assumes the execution or application-task role
**When** trust policies are analyzed
**Then** trust is limited to `ecs-tasks.amazonaws.com`, the source account, and the narrowest supported source-resource condition
**And** no GitHub, human, Scheduler, Lambda, or unrelated service principal can assume those roles.

**Given** IAM validation runs
**When** positive and negative policy fixtures and IAM Access Analyzer or equivalent checks execute
**Then** approved workload access succeeds while user/key creation, administrator policies, boundary removal, trust mutation, unrelated `PassRole`, OIDC-provider changes, ledger writes, and cross-job CONFIG writes fail
**And** every exception records owner, justification, approver, and expiry or review date.

### Story 2.3: Provision the Fargate Task and Structured Logs

As an Application Engineer,
I want the module to create a validated Fargate task definition and retained log group from my job declaration,
So that my workload executes with an immutable identity and emits evidence the platform can correlate.

**Acceptance Criteria:**

**Given** a valid reserved job with approved IAM roles
**When** the task definition is planned
**Then** it uses Fargate compatibility, `awsvpc` network mode, explicit CPU and memory, the configured platform compatibility, and the exact execution and application-task roles
**And** unsupported CPU/memory combinations or incompatible runtime settings fail before apply.

**Given** a production container image is declared
**When** image validation runs
**Then** mutable references such as `latest` are rejected and the deployed image is bound to an immutable digest or approved immutable reference
**And** the resolved image identity is retained as part of Deployment Identity.

**Given** command, entrypoint, and non-secret environment overrides are supplied
**When** container definitions are rendered
**Then** the values appear exactly as reviewed and remain distinct from runtime occurrence overrides
**And** reserved platform fields for job, Occurrence ID, CONFIG, attempt, and Deployment Identity cannot be overridden by consumer inputs.

**Given** approved secret references are supplied
**When** container definitions are rendered
**Then** ECS-agent references use the container `secrets` contract and application-pull references expose only non-sensitive locator metadata
**And** no secret value appears in Terraform state configuration, plan output, task-definition environment values, tags, or logs.

**Given** the job is deployed in production or non-production
**When** its CloudWatch log group is created
**Then** it is encrypted, tagged, named predictably, and uses an explicit configurable retention within platform guardrails
**And** defaults are 90 days for production and 30 days for non-production unless an approved policy requires otherwise.

**Given** the task definition configures the `awslogs` driver
**When** the container starts
**Then** logs are written only to the job's exact log group and discoverable stream prefix
**And** execution-role permissions cannot write to another job's log group.

**Given** the Job Completion Contract
**When** application logging requirements are validated
**Then** the job declaration requires structured start, success, and failure records containing the supplied job, Occurrence ID, CONFIG, and attempt assertions plus timestamps, status, exit code when available, and optional sanitized error reason
**And** documentation states that a success marker alone does not establish successful completion.

**Given** a task-definition revision is registered
**When** module outputs and tags are inspected
**Then** the full revision ARN, family, image digest, log group, role ARNs, module version, source revision, and protected ownership metadata are available for later CONFIG publication
**And** secret values and unbounded operational data are excluded.

**Given** task and logging configuration changes
**When** automated module tests run
**Then** fixtures cover valid compute combinations, invalid combinations, immutable and mutable images, command rendering, reserved environment collisions, secret modes, log retention, encryption, and exact log permissions
**And** formatting, validation, security scanning, and example planning pass without production credentials.

### Story 2.4: Enforce Private Task Networking

As a Cloud Infrastructure Owner,
I want scheduled tasks restricted to validated private networking with explicit egress,
So that production workloads cannot become publicly reachable or gain unintended network access.

**Acceptance Criteria:**

**Given** a consumer supplies VPC and subnet IDs
**When** network validation runs
**Then** every subnet belongs to the declared VPC, account, and Region and is classified according to the organization's approved private-subnet policy
**And** a detected public subnet, mismatched VPC, unsupported availability configuration, or empty subnet set blocks production planning.

**Given** the module renders ECS network configuration
**When** a task launch CONFIG is produced
**Then** public IP assignment is always disabled for production and private subnet IDs are explicit
**And** consumer input cannot override the production public-IP prohibition.

**Given** consumers supply existing security group IDs
**When** production policy evaluates them
**Then** each group belongs to the declared VPC and satisfies the approved no-ingress and bounded-egress policy
**And** public ingress, unrestricted IPv4 or IPv6 egress, stale references, or cross-VPC groups fail unless covered by a governed exception.

**Given** a consumer enables module-created security-group mode
**When** the security group is planned
**Then** it has no ingress rules and permits only declared security-group, prefix-list, or bounded CIDR egress destinations and ports
**And** `0.0.0.0/0`, `::/0`, all-protocol egress, and implicit default egress are blocked in production without an approved exception.

**Given** the task requires ECR, S3, CloudWatch Logs, Secrets Manager, SSM, KMS, or workload dependencies
**When** network prerequisites are validated
**Then** the declaration identifies the approved NAT or VPC endpoint path for every required service and external dependency
**And** missing reachability evidence produces an actionable validation or production-readiness failure rather than silently creating network infrastructure.

**Given** application-pull secrets or approved external secret platforms are configured
**When** network policy is evaluated
**Then** required endpoints and destinations are explicit and consistent with the task-role secret permissions
**And** secret retrieval does not require public ingress or expose secret values in network metadata.

**Given** validated networking is available
**When** module outputs are inspected
**Then** the exact VPC, subnet, security-group, public-IP policy, and declared dependency reachability metadata are available for immutable CONFIG publication
**And** unrelated route, gateway, subnet, or shared-security-group resources remain outside module ownership.

**Given** networking changes are tested
**When** policy fixtures and module tests run
**Then** they cover private and public subnets, mismatched VPCs, supplied and created security groups, IPv4 and IPv6 exposure, unrestricted egress, missing endpoints, and valid bounded access
**And** production exposure failures block while explicitly staged non-production checks follow the approved advisory policy.

### Story 2.5: Publish and Validate Immutable Job Configuration

As a Platform Engineer,
I want each job's complete launch configuration published and acknowledged while launch remains disabled,
So that the Cell can verify immutable AWS identities and policy boundaries before any occurrence executes.

**Acceptance Criteria:**

**Given** a reserved job has a task revision, roles, logs, and validated networking
**When** phase-one Terraform is applied
**Then** it creates the EventBridge Scheduler schedule in a disabled state with its final schedule group, target source queue, target payload contract, retry policy, and dedicated delivery role
**And** the delivery role can send only to that exact source queue and its Scheduler DLQ under restricted source-account and schedule-group conditions.

**Given** the disabled schedule and job launch role exist
**When** the Registrar acknowledges their AWS identities
**Then** it binds the schedule ARN and immutable IAM Role ID to the existing repository, root, account, Region, owner, and ownership generation
**And** stale, substituted, cross-job, or manually recreated identities are rejected.

**Given** all launch inputs are known
**When** the module builds CONFIG
**Then** the canonical body includes job and generation identity, normalized schedule contract, activation window, full task-definition revision ARN, cluster, private subnets, security groups, public-IP policy, execution/task/launch roles, runtime deadline, overlap declaration, log group, notification metadata, Deployment Identity, and supported contract versions
**And** CONFIG contains secret references only, never secret values.

**Given** canonical CONFIG has been rendered
**When** the module publishes it
**Then** the object key and metadata include its content hash and ownership generation and are written only to the job's exact encrypted, versioned inbox prefix
**And** publishing identical content is idempotent while launch-relevant changes create a new immutable generation rather than overwriting prior CONFIG.

**Given** a CONFIG candidate reaches the Cell inbox
**When** Cell validation runs
**Then** schema, canonical hash, repository ownership, bound AWS identities, task family, cluster, networking, roles, retention, notification target, and compatibility ranges are verified against authoritative AWS and registry data
**And** a valid snapshot is copied into the separate CONFIG registry with lifecycle state `VALIDATED`.

**Given** CONFIG validation fails
**When** the candidate is processed
**Then** lifecycle state becomes `REJECTED` with an actionable sanitized reason
**And** the schedule remains disabled, no expectations are materialized, and no task can launch.

**Given** phase-one apply permissions are analyzed
**When** security tests run
**Then** the job apply role can write only its reserved inbox prefix and manage only its module-owned disabled schedule and roles
**And** it cannot write the CONFIG registry, occurrence ledger, another job's prefix, Cell queues, runtime processors, or protected state controls.

**Given** a valid Cell acknowledgement exists
**When** module outputs are inspected
**Then** they expose the CONFIG hash, generation, registry acknowledgement, bound Role ID, schedule ARN, compatibility result, and current lifecycle state without exposing secret data
**And** the module clearly reports that `VALIDATED` is not authorization to enable production launch until materialization and phase-two approval complete.

### Story 2.6: Activate the Scheduled Occurrence Contract Safely

As a Job Owner,
I want the reviewed schedule generation enabled only after its expected occurrences are verified,
So that Scheduler delivery and occurrence tracking cannot disagree about what should run.

**Acceptance Criteria:**

**Given** a job declares a recurring schedule
**When** the schedule contract is validated
**Then** it defines a supported cron or rate expression, time zone, explicit start anchor, activation window, flexible-window behavior, retry attempts, maximum event age, completion deadline, and generation hash
**And** flexible windows default to disabled while unsupported expressions and one-time schedules fail before activation.

**Given** production retry settings are configured
**When** reviewers inspect the plan
**Then** Scheduler delivery retries and event age are explicit and distinct from ECS launch reconciliation and application retry behavior
**And** the declaration acknowledges at-least-once delivery and documents the job's duplicate-effect strategy.

**Given** a production job declares expected runtime and overlap behavior
**When** activation policy runs
**Then** maximum runtime becomes the occurrence completion deadline and does not claim enforced cancellation
**And** an overlap-unsafe job cannot activate without reviewed evidence of application idempotency or locking.

**Given** CONFIG is `VALIDATED` for a future activation anchor
**When** the Occurrence Materializer processes that generation
**Then** it creates the required expectation horizon for the exact generation and records the horizon watermark and conformance result
**And** lifecycle state advances to `MATERIALIZED` only when at least 24 hours of expected occurrences are verified.

**Given** an exact `MATERIALIZED` acknowledgement exists
**When** a separately reviewed phase-two plan is generated
**Then** Terraform preconditions and blocking policy permit only the acknowledged CONFIG hash, schedule ARN, Role ID, generation, and activation anchor to become enabled
**And** changed, stale, absent, rejected, or insufficient-horizon acknowledgements block the plan.

**Given** the approved phase-two plan is applied
**When** the activation anchor is reached
**Then** EventBridge Scheduler sends a canonical launch envelope with scheduled-time context to the Cell source queue rather than invoking ECS directly
**And** the lifecycle state becomes `ENABLED` for the same generation materialized by the Cell.

**Given** an operator disables a job
**When** the enabled-state input is changed through the authorized path
**Then** future Scheduler delivery stops without deleting task revisions, CONFIG, occurrence history, logs, alarms, or ownership registration
**And** the disablement actor, reason, approval, and Deployment Identity remain attributable.

**Given** schedule expression, time zone, or another launch-relevant field changes
**When** production rollout begins
**Then** the first apply disables and retires the old generation and drains or reconciles its in-flight evidence
**And** a second apply publishes a new future-anchored generation, verifies its horizon, and enables only that generation, making any planned gap explicit.

**Given** Scheduler cannot deliver a launch envelope
**When** retry and maximum-event-age limits are exhausted
**Then** the message is retained in the job's Scheduler DLQ and Cell delivery metrics identify the failure
**And** the independently materialized expected occurrence remains eligible to become `MISSED`.

**Given** schedule activation behavior is tested
**When** module, contract, and integration suites run
**Then** they cover supported cron/rate/time-zone/DST cases, retries, duplicate delivery, overlap declarations, missing runtime, disabled schedules, stale acknowledgements, phase-two mutation, schedule replacement, and target failure
**And** no test can enable direct Scheduler-to-ECS delivery.

### Story 2.7: Connect Completion Evidence and Production Alerts

As a Job Owner,
I want my job's structured completion records and alert destination connected to the Platform Cell,
So that production failures and missing completions reach the responsible on-call path with occurrence context.

**Acceptance Criteria:**

**Given** a job has a retained CloudWatch log group and validated CONFIG
**When** completion integration is enabled
**Then** the module creates the exact log-subscription integration required by the Cell Contract
**And** delivery permissions allow only the registered log group to send to the Cell's completion-evidence path.

**Given** a task emits structured start, success, or failure records
**When** the Cell log ingestor processes them
**Then** each record must conform to the versioned completion schema and assert the supplied job, Occurrence ID, CONFIG, attempt, timestamp, status, exit code when available, and sanitized error reason
**And** AWS log-group and task mappings remain the authoritative correlation source.

**Given** a production occurrence reports success
**When** completion is evaluated
**Then** exactly one valid success record for attempt zero must correlate with a zero essential-container exit
**And** an uncorrelated marker, marker from another occurrence, log-window count, Scheduler success metric, or zero exit alone cannot satisfy completion.

**Given** a production job is declared
**When** production policy evaluates observability inputs
**Then** an existing notification-target ARN, Job Owner, Runbook location, completion deadline, log retention, and occurrence-aware completion integration are mandatory
**And** missing or invalid values block activation.

**Given** the job's Scheduler delivery, task execution, log subscription, or completion contract fails
**When** an alarm or occurrence alert is emitted
**Then** it identifies job, Occurrence ID when applicable, Environment, account, Region, failure plane, occurrence state, detection time, Deployment Identity, owner, and Runbook
**And** it routes through the registered production target without placing secret or raw log content in the payload.

**Given** CloudWatch Logs cannot deliver completion evidence
**When** subscription errors, disabled filters, or sustained delivery failures occur
**Then** a job or Cell alarm reaches the configured operational path
**And** affected occurrences remain eligible for overdue detection rather than being treated as successful.

**Given** a non-production job opts out of occurrence-aware completion during MVP
**When** best-effort detection is configured
**Then** the module clearly labels the reduced coverage and may create a bounded success-pattern metric filter and low-noise alarm
**And** that configuration cannot be promoted to production.

**Given** production and non-production alert settings differ
**When** the module is planned
**Then** production completion and failure alerts cannot be disabled, while approved non-production alarms may be disabled or use a separate engineering target
**And** disabling optional non-production alarms does not remove logs or Cell-health signals.

**Given** completion and alert integration is tested
**When** fixtures and accelerated integration tests run
**Then** they cover valid success, non-zero exit, missing marker, marker without zero exit, wrong Occurrence ID, duplicate marker, delayed prior completion, log delivery failure, missing target, and consecutive failures
**And** every required production failure reaches the test destination within five minutes of becoming observable or reaching its deadline.

### Story 2.8: Expose Job Operations and Optional Views

As an On-call Engineer,
I want documented outputs and an optional operational view for each scheduled job,
So that I can locate its deployed resources and assess its health without inspecting Terraform state.

**Acceptance Criteria:**

**Given** a scheduled job has been deployed
**When** module outputs are inspected
**Then** documented outputs identify the canonical job, Cell, account, Region, Environment, schedule and group, task-definition revision, cluster, log group, job IAM roles, CONFIG hash and generation, alarms, notification target identity, Runbook, and lifecycle state
**And** every output has a stable type and description.

**Given** Deployment Identity is requested
**When** the module constructs it
**Then** it includes image digest, task-definition revision, source revision, module version, workflow identity when supplied, CONFIG hash, schedule generation, target account and Region, and deployment timestamp or run reference
**And** the same identity is available to task tags, occurrence records, alerts, and rollback evidence.

**Given** operators use module outputs
**When** they follow the documented AWS console or CLI references
**Then** they can locate the schedule, current task revision, task events, logs, occurrence status, alarms, and notification path without direct Terraform-state access
**And** identifiers remain scoped to the deployed job and Cell.

**Given** outputs are rendered in a plan, apply log, or automation artifact
**When** data-safety checks run
**Then** no secret value, secret payload, sensitive plan content, unrestricted log text, or application credential is exposed
**And** secret-reference outputs are omitted unless a non-sensitive identifier is explicitly required.

**Given** a consumer enables the optional CloudWatch dashboard
**When** Terraform creates it
**Then** the view separates Scheduler delivery, ECS launch and runtime outcomes, occurrence completion states, deadline failures, log-delivery health, and relevant Cell-health context
**And** it uses only bounded metric dimensions without Occurrence ID, task ARN, error text, or log stream.

**Given** a dashboard is enabled for one or more jobs
**When** cost and scale guardrails are evaluated
**Then** widget count, query count, time range, metric cardinality, and retention assumptions remain within documented configurable limits
**And** the design supports the MVP job count without preventing later use across dozens of jobs.

**Given** a consumer disables or omits the optional dashboard
**When** the module is applied
**Then** required production logs, occurrence tracking, alarms, and notifications remain unchanged
**And** no monitoring dependency relies on the dashboard.

**Given** output or dashboard contracts change
**When** module tests and compatibility checks run
**Then** snapshots verify output types, resource identifiers, Deployment Identity, redaction, bounded dimensions, dashboard-enabled behavior, and dashboard-disabled behavior
**And** breaking output changes require the major-version process rather than silent replacement.

### Story 2.9: Perform a Controlled Manual Rerun

As a Job Owner,
I want to rerun a reviewed job occurrence through an authorized platform command,
So that I can recover from a failure without editing the schedule, bypassing occurrence tracking, or creating an untraceable duplicate.

**Acceptance Criteria:**

**Given** a Job Owner requests a manual rerun
**When** the rerun workflow starts
**Then** it requires the canonical job ID, original Occurrence ID, reviewed CONFIG and Deployment Identity, reason, expected duplicate effects, verification plan, and rollback or compensation acknowledgement
**And** the requester cannot supply a new Occurrence ID, task ARN, arbitrary task definition, cluster, role, or evidence payload.

**Given** a production rerun request is complete
**When** authorization is evaluated
**Then** the Job Owner and required Platform approver authorize the command through the short-lived operator path
**And** any required application or Security approval is retained with the actor, timestamp, scope, and reason.

**Given** the original occurrence is still running, nonterminal, or has an unresolved launch outcome
**When** a rerun is requested
**Then** the workflow blocks by default and requires resolution of overlap, ambiguity, and duplicate-effect risk
**And** schedule cadence alone is not accepted as proof that another task is safe.

**Given** an authorized rerun command reaches the Cell
**When** the command handler accepts it
**Then** it generates the UUIDv7 command ID and deterministic `occurrence/manual/v1` identity linked through `replay_of_occurrence_id`
**And** the Process Manager uses the exact reviewed CONFIG and the same attempt-zero launch protections as a scheduled occurrence.

**Given** the synthetic occurrence launches
**When** its task executes
**Then** task tags, runtime overrides, logs, task events, occurrence state, and alerts use the synthetic Occurrence ID while retaining the original occurrence link
**And** the EventBridge schedule remains unchanged.

**Given** the rerun succeeds
**When** completion evidence is correlated
**Then** the workflow verifies zero essential-container exit plus exactly one valid structured success record
**And** it records the result, actor, approvals, command ID, task ARN, Deployment Identity, verification evidence, and any completed compensation checks.

**Given** the rerun fails, becomes overdue, or is ambiguous
**When** the occurrence reaches a terminal state or deadline
**Then** standard occurrence alerts and Runbook guidance apply
**And** the original occurrence remains immutable while required rollback or application compensation is recorded.

**Given** a human attempts to rerun by assuming the workload role or calling `ecs:RunTask` directly
**When** IAM enforcement is evaluated
**Then** the action is denied outside the Process Manager's registered job-launch path
**And** attempted bypasses are attributable through CloudTrail and relevant security signals.

**Given** rerun behavior is tested
**When** automated and operator-path tests execute
**Then** they cover authorized success, unauthorized caller, wrong job, stale CONFIG, nonterminal original, ambiguous launch, duplicate command delivery, concurrent request, failed rerun, and compensation evidence
**And** duplicate delivery of one approved command never creates a second synthetic occurrence or ECS task.

## Epic 3: Deliver and Evolve Jobs Through Governed Automation

Platform and application teams can validate, approve, deploy, identify, roll back, version, and upgrade scheduled jobs through auditable GitHub Actions and immutable releases.

### Story 3.1: Validate Pull Requests Without Cloud Credentials

As a Platform Reviewer,
I want every pull request validated without granting untrusted code cloud credentials,
So that unsafe or malformed changes are rejected before they can access AWS or protected Terraform state.

**Acceptance Criteria:**

**Given** a pull request changes Terraform, runtime, contract, workflow, example, or policy files
**When** the validation workflow runs
**Then** it performs recursive `terraform fmt -check`, backend-free initialization, Terraform validation, focused module tests, executable example checks, contract tests, and applicable runtime tests
**And** each check reports a distinct actionable status rather than collapsing all failures into one result.

**Given** static security and quality checks are configured
**When** pull-request validation runs
**Then** it scans Terraform, IAM, workflows, dependencies, committed files, and configuration for security issues, credentials, secret values, state, plans, `.terraform/`, mutable production references, and prohibited provisioners
**And** obvious secret exposure, invalid Terraform, formatting errors, or prohibited generated artifacts block merge in every Environment.

**Given** a pull request originates from a fork or another untrusted context
**When** the workflow executes
**Then** it receives no AWS credential, cloud-backed state access, protected Environment secret, write token, or privileged reusable-workflow input
**And** attacker-controlled code cannot execute in a later privileged job through artifacts, caches, outputs, or workflow-command injection.

**Given** the validation workflow requires repository access
**When** GitHub permissions are evaluated
**Then** `GITHUB_TOKEN` permissions are explicitly declared at the minimum read-only scope required for each job
**And** pull-request write access is isolated to a trusted reporting path that never executes untrusted repository code.

**Given** Terraform initialization is required for validation
**When** modules and examples initialize
**Then** backend access is disabled and committed dependency locks or approved immutable provider constraints are honored
**And** unexpected provider selection, checksum changes, or dependency drift fails with an actionable result.

**Given** a check produces logs or artifacts
**When** results are uploaded or summarized
**Then** output is sanitized to exclude secret values, sensitive Terraform content, credentials, unrestricted environment dumps, and saved binary plans
**And** artifacts use explicit retention and access appropriate to their sensitivity.

**Given** a check is advisory during the approved MVP non-production phase
**When** it reports a finding
**Then** the result clearly distinguishes advisory findings from blocking failures and records the planned enforcement stage
**And** production-equivalent policy failures are never downgraded by this workflow.

**Given** the validation workflow and referenced Actions are reviewed
**When** supply-chain checks run
**Then** third-party Actions and reusable workflows are pinned to full commit SHAs and workflow files pass static analysis
**And** tests prove that forked pull requests, malicious outputs, modified workflow files, cache poisoning attempts, and failing checks cannot obtain privileged execution or pass required status checks.

### Story 3.2: Bind Trusted Deployment Targets and OIDC Roles

As a Security Engineer,
I want every deployment Environment bound to immutable GitHub and AWS identities,
So that only the approved repository and reusable workflow can access the intended account, Region, role, and Terraform state.

**Acceptance Criteria:**

**Given** an Environment is authorized for deployment
**When** its deployment-target manifest is defined
**Then** the manifest binds immutable repository owner and repository IDs, repository name, root path, Environment, account, Region, plan-role ARN, apply-role ARN, state bucket and key, Cell Contract path, and approved reusable-workflow SHA
**And** consumers cannot replace production targets through arbitrary workflow inputs.

**Given** the organization configures GitHub OIDC subjects
**When** a deployment token is issued
**Then** the custom `sub` contains immutable owner and repository IDs, deployment Environment, and full-SHA `job_workflow_ref`
**And** AWS trust requires exact `aud = sts.amazonaws.com` and the expected complete `sub`.

**Given** plan and apply require different authority
**When** IAM roles are provisioned
**Then** separate plan and apply roles use distinct exact OIDC subjects and sessions
**And** neither trust policy accepts an unauthorized repository, workflow revision, Environment, branch, tag, pull-request context, or audience.

**Given** the plan role is assumed
**When** its effective permissions are evaluated
**Then** it can read only the target's state path, lock metadata, Cell Contract, configuration, and AWS resources required to refresh and plan
**And** it cannot mutate infrastructure, write state, pass roles, publish CONFIG, alter schedules, or assume the apply role.

**Given** the apply role is assumed after production approval
**When** its effective permissions are evaluated
**Then** it can update only the approved state path and platform-managed resource namespace under the required permissions boundary and organizational controls
**And** it cannot create IAM users or keys, remove boundaries, create administrator-equivalent policies, alter its trust, modify the OIDC provider, pass unrelated roles, write runtime tables, or change state-backend controls.

**Given** Terraform remote state is configured
**When** backend controls are inspected
**Then** state uses an encrypted, versioned, public-blocked S3 bucket with native S3 lock files and path-scoped IAM
**And** account and Environment roots cannot read or write one another's state or lock paths.

**Given** a trusted workflow assumes an AWS role
**When** its preflight runs
**Then** it verifies caller identity, account, Region, manifest checksum, root path, role ARN, state path, Cell identity, and approved workflow SHA before Terraform initialization
**And** any mismatch terminates the job before state or infrastructure access.

**Given** production deployment controls are required
**When** GitHub configuration is reviewed
**Then** protected Environments enforce required reviewers, self-review prevention, restricted deployment refs, and disabled administrator bypass or an equivalent auditable control
**And** production authorization remains blocked if those controls cannot be demonstrated.

**Given** OIDC and target controls are tested
**When** positive and negative trust fixtures execute
**Then** the exact approved plan and apply identities succeed while altered repository, renamed or transferred repository, wrong Environment, branch, tag, workflow SHA, audience, account, Region, role, state path, and self-review attempts fail
**And** no long-lived AWS access key is created, stored, or documented.

### Story 3.3: Generate a Trusted and Reviewable Terraform Plan

As a Platform Reviewer,
I want an attributable Terraform plan generated with read-only cloud access,
So that I can review the exact target impact without granting infrastructure mutation authority.

**Acceptance Criteria:**

**Given** credential-free validation has passed for a reviewed revision
**When** trusted planning is requested
**Then** the workflow executes from the approved reusable-workflow SHA, checks out the exact source commit, verifies workflow and dependency integrity, and assumes only the target's plan role
**And** changed privileged workflow files, unreviewed commits, prohibited providers, provisioners, or executable data-source patterns block cloud-backed planning.

**Given** the trusted plan job starts
**When** target preflight runs
**Then** it verifies repository identity, source commit, Environment, account, Region, root path, manifest checksum, plan-role ARN, state path, and Cell Contract compatibility
**And** any mismatch terminates before Terraform reads protected state.

**Given** Terraform initialization runs against the trusted target
**When** providers and modules are selected
**Then** the encrypted backend and native lock file use the manifest-bound path and the committed provider dependency lock is verified without modification
**And** unexpected versions, checksums, mutable module sources, or backend reconfiguration fail the job.

**Given** initialization and refresh succeed
**When** Terraform planning runs
**Then** it generates a binary saved plan for the exact source commit and target using the read-only role
**And** the plan role cannot mutate AWS resources, state, locks, CONFIG, schedules, IAM, or Cell runtime data.

**Given** the plan is created
**When** metadata is recorded
**Then** it includes source commit, repository and workflow identity, manifest checksum, account, Region, Environment, root, state path, Cell and module versions, provider-lock checksum, assumed-role session, creation time, and plan checksum
**And** later target, source, dependency, or manifest changes invalidate the plan.

**Given** reviewers need a pull-request summary
**When** plan reporting runs
**Then** it publishes a sanitized resource-action and policy-impact summary without unrestricted attribute values, secret data, sensitive outputs, or the binary plan
**And** detailed plan access remains restricted to authorized reviewers.

**Given** the binary plan is stored
**When** artifact controls are evaluated
**Then** it is treated as sensitive, encrypted by the platform, access-restricted, checksum-verified, and retained only for the configured short review window
**And** it is never committed, cached across trust boundaries, or exposed to untrusted workflow jobs.

**Given** no infrastructure changes are present
**When** Terraform returns its no-change result
**Then** the workflow records a successful, attributable no-op plan
**And** required policy and target-integrity checks still run.

**Given** trusted planning controls are tested
**When** negative workflow fixtures execute
**Then** altered commits, manifests, state paths, provider locks, module references, workflow SHAs, roles, accounts, Regions, artifact checksums, and prohibited execution hooks fail
**And** no test path can convert plan authority into apply authority.

### Story 3.4: Enforce Production Policies and Govern Exceptions

As a Production Approver,
I want consistent policy-as-code decisions applied to every trusted plan,
So that insecure or operationally incomplete jobs cannot reach production through reviewer oversight.

**Acceptance Criteria:**

**Given** a trusted production plan is available
**When** policy evaluation runs
**Then** it blocks missing protected tags or ownership, mutable images, public IP assignment, public subnets, unsafe security groups, unrestricted egress, missing logs or retention, missing occurrence tracking or alarms, absent notification targets, plaintext secret inputs, and incompatible Cell contracts
**And** each denial identifies the affected resource, policy, requirement, evidence, and remediation.

**Given** a plan creates or changes IAM
**When** IAM policy analysis runs
**Then** it evaluates actions, resources, conditions, trust, `PassRole`, managed-policy drift, privilege escalation, cross-account access, permissions boundaries, and CI self-modification rather than checking wildcard syntax alone
**And** administrator-equivalent authority, unrelated role passing, boundary removal, trust mutation, IAM user or key creation, OIDC-provider changes, runtime-table writes, and cross-job CONFIG access are blocked.

**Given** a plan changes schedule or launch configuration
**When** architecture policies run
**Then** direct Scheduler-to-ECS targets, unregistered job identities, stale Role IDs, mutable CONFIG, missing generation acknowledgement, insufficient expectation horizon, or phase-two mutation are denied
**And** only the exact `RESERVED` through `ENABLED` handshake defined by the architecture can activate production launch.

**Given** repository and workflow content is evaluated
**When** supply-chain and data-safety policies run
**Then** state, plans, `.terraform/`, credentials, generated secret material, mutable Actions or workflow references, unexpected provider locks, provisioners, and `null_resource` are blocked as applicable
**And** secret scanning covers Terraform, workflow inputs, environment values, documentation, fixtures, logs, and generated summaries.

**Given** compliant and noncompliant policy fixtures exist
**When** CI validates the policy suite
**Then** every blocking rule has at least one positive and one negative fixture with deterministic expected output
**And** policy changes cannot merge if they remove coverage, silently change severity, or produce ambiguous results.

**Given** a policy supports an exception
**When** an exception is submitted
**Then** it is scoped to the exact policy, resource, Environment, source revision, owner, justification, approver, and expiry or review date
**And** broad, expired, unsigned, mismatched, or reusable exceptions are rejected.

**Given** a non-exemptible control fails
**When** an exception is attempted
**Then** invalid Terraform, target-identity mismatch, plaintext secret exposure, missing production approval controls, or unauthorized IAM escalation remains blocking
**And** the denial explains why the control cannot be waived through the normal exception path.

**Given** non-production policy staging is active
**When** dev or staging plans are evaluated
**Then** advisory and blocking severities follow the approved adoption timeline and remain visible in evidence
**And** production rules are blocking from the first release and cannot inherit a lower Environment's advisory setting.

**Given** policy evaluation completes
**When** results are retained
**Then** the policy bundle version, plan checksum, source revision, target, findings, exceptions, actors, approvals, and timestamps are attributable
**And** sanitized summaries do not disclose secrets or unrestricted sensitive plan content.

### Story 3.5: Approve and Apply the Exact Production Plan

As a Production Approver,
I want production to apply only a fresh, policy-compliant plan from the approved deployment commit,
So that reviewed intent cannot change between approval and infrastructure mutation.

**Acceptance Criteria:**

**Given** a revision has merged into the authorized deployment ref
**When** production deployment starts
**Then** the workflow checks out the exact deployment commit and creates a fresh saved plan using the trusted plan role and manifest-bound target
**And** a pull-request plan or plan from another commit, ref, workflow, target, or prior run cannot be promoted directly.

**Given** the fresh deployment plan is created
**When** pre-approval checks run
**Then** target verification, dependency-lock validation, Cell compatibility, policy evaluation, exception validation, and plan metadata checks execute again against that exact plan checksum
**And** any changed dependency, manifest, policy result, target identity, or source content blocks approval.

**Given** a production plan passes all blocking checks
**When** the protected Environment gate opens
**Then** approval requires Platform Engineering and the Job Owner, plus Security review for qualifying IAM or networking changes
**And** self-review, administrator bypass, unauthorized reviewers, and approval from an unrelated deployment run are rejected.

**Given** multiple deployments target the same account, Environment, and Terraform root
**When** concurrency controls evaluate them
**Then** only one plan/apply sequence may hold the deployment lock and newer runs cannot silently cancel an in-progress production apply
**And** separate roots cannot use concurrency to bypass shared state or schedule-generation safeguards.

**Given** approval is granted
**When** the apply job starts
**Then** it assumes only the exact apply role through the approved OIDC subject, re-verifies caller, target, source commit, plan checksum, artifact provenance, state path, and lock ownership
**And** apply credentials are unavailable to planning, review, untrusted, or post-processing jobs.

**Given** all apply preconditions match
**When** Terraform executes
**Then** it runs `terraform apply` against the exact approved binary plan without replanning, variable substitution, target override, refresh mutation, or interactive change
**And** state remains encrypted and locked for the complete mutation window.

**Given** a two-phase job creation or schedule change is required
**When** production applies proceed
**Then** phase one and phase two use separate fresh plans and approvals bound to their respective lifecycle states and acknowledgements
**And** phase two cannot be folded into phase one or enable a generation that changed after acknowledgement.

**Given** apply fails or loses its runner
**When** the deployment workflow handles the failure
**Then** it records the partial result, preserves state and plan evidence, avoids automatic mutation retries, and provides bounded lock-recovery guidance
**And** a subsequent deployment requires a new fresh plan reflecting actual state.

**Given** an emergency production path is invoked
**When** normal approval controls are bypassed under documented break-glass policy
**Then** access is time-bound, independently approved, immediately alerted, actor-attributable, and limited to the approved target
**And** the event requires post-incident review and cannot weaken future normal deployments.

### Story 3.6: Record Deployment and Rollback Evidence

As an On-call Engineer,
I want every deployment tied to an immutable workload identity and reviewed recovery instructions,
So that I can determine exactly what ran and restore a known-good configuration safely.

**Acceptance Criteria:**

**Given** a production plan is awaiting approval
**When** deployment evidence is assembled
**Then** it records repository and source commit, workflow SHA and run, module and Cell versions, contract versions, provider-lock checksum, image digest, task-definition revision, CONFIG hash, schedule generation, account, Region, Environment, state path, plan checksum, policy bundle, and target manifest
**And** missing Deployment Identity fields block approval.

**Given** production approval is granted
**When** approval evidence is retained
**Then** it records Platform, Job Owner, and required Security approvers, timestamps, reviewed plan checksum, exceptions, emergency status, and OIDC session identity
**And** approvals are bound to the exact deployment rather than a mutable branch, tag, or general Environment authorization.

**Given** Terraform apply completes or fails
**When** deployment evidence is finalized
**Then** it records the apply actor, role session, start and completion times, state result, changed resource identities, lifecycle state, output checksums, errors, and workflow conclusion
**And** partial or failed applies remain visible rather than being represented as successful deployments.

**Given** a task or occurrence is investigated
**When** an operator follows its Deployment Identity
**Then** the operator can map it to the exact image digest, task-definition revision, source revision, CONFIG, schedule generation, module and workflow versions, target, approvals, and deployment run
**And** the mapping does not require access to sensitive Terraform plan contents.

**Given** a production-impacting change is proposed
**When** readiness checks run
**Then** rollback or forward-fix instructions identify the known-good Deployment Identity, launch-disablement step, generation retirement, evidence drain or quarantine, compatible restore versions, data compensation considerations, and post-change verification
**And** generic instructions such as "revert the commit" do not satisfy the gate.

**Given** rollback is required
**When** the approved recovery workflow executes
**Then** it disables launch first, retires the affected generation, reconciles in-flight evidence, creates a fresh plan for the known-good compatible identity, and applies it through normal protected controls
**And** launch resumes only after scheduling, task execution, logs, occurrence transitions, notification delivery, and required compensation are verified.

**Given** deployment succeeds
**When** post-apply verification runs
**Then** it confirms target identity, lifecycle handshake, schedule state, expectation horizon, task revision, log subscription, alarms, and alert route
**And** failed verification creates an actionable deployment result and invokes the reviewed rollback or forward-fix decision.

**Given** evidence contains sensitive information
**When** it is stored or displayed
**Then** secret values, raw CONFIG bodies, binary plans, credentials, and unrestricted logs are excluded or access-restricted according to policy
**And** non-sensitive audit evidence is retained for the organizational production-audit and rollback horizon.

**Given** an emergency or break-glass action affects production
**When** its evidence is recorded
**Then** actor, independent approval, reason, scope, start and expiry, commands, resulting Deployment Identity, verification, alert, and post-incident review are retained
**And** the emergency path cannot rewrite or delete prior deployment evidence.

### Story 3.7: Publish and Evolve Immutable Platform Releases

As a Platform Owner,
I want modules, workflows, contracts, and runtimes released with explicit compatibility and migration guarantees,
So that consumers can upgrade or roll back without depending on mutable platform artifacts.

**Acceptance Criteria:**

**Given** a platform change is ready for release
**When** semantic versioning is evaluated
**Then** bug fixes and non-breaking documentation use patch versions, backward-compatible capabilities use minor versions, and breaking interface or behavior changes use major versions
**And** automated checks reject a release classification inconsistent with detected contract, input, output, schema, workflow, or behavior changes.

**Given** a release candidate is built
**When** release validation runs
**Then** module tests, examples, contract suites, state permutations, IAM-negative tests, schedule conformance, policy fixtures, runtime tests, failure injection, and current/previous-major compatibility tests pass
**And** the tested Terraform, AWS provider, Python runtime, and Fargate compatibility matrix is recorded.

**Given** validation succeeds on the authorized release commit
**When** artifacts are published
**Then** the Terraform modules are published from the internal platform repository, reusable workflows from the centralized workflow repository, runtime artifacts by immutable digest, and contracts by immutable version and checksum
**And** publication records source commit, builder workflow SHA, test evidence, checksums, provenance, and release actor without long-lived credentials.

**Given** a consumer references a platform release
**When** validation runs
**Then** module sources use an immutable registry version or commit, reusable workflows and Actions use full commit SHAs, runtime images use digests, and provider locks are committed
**And** mutable branches, floating workflow tags, mutable images, or unexpected dependency changes fail production policy.

**Given** an input, output, schema, or behavior is being deprecated
**When** a backward-compatible release introduces the deprecation
**Then** documentation identifies the replacement, warning behavior, supported majors, migration steps, and planned removal version
**And** removal cannot occur before the documented major release and compatibility horizon.

**Given** a major Cell, module, CONFIG, schema, or runtime change is introduced
**When** rollout is designed
**Then** it follows expand-migrate-contract sequencing and preserves a stable Process Manager principal within the major
**And** current and previous majors interoperate through the longest queue, replay, runtime, retention, and rollback horizon.

**Given** consumers plan an upgrade
**When** they review release artifacts
**Then** release notes describe capabilities, security impact, compatibility, state migration, required two-phase changes, rollback identity, known limitations, and deprecations
**And** upgrade notices are published through GitHub releases and the approved internal engineering channel.

**Given** an upgrade fails validation or post-deployment verification
**When** rollback is initiated
**Then** the workflow can restore the documented compatible module, workflow, contract, and runtime identities using a fresh reviewed plan
**And** prior immutable CONFIG, task revisions, artifacts, and evidence remain available for the required rollback horizon.

**Given** an old platform version appears eligible for retirement
**When** lifecycle cleanup evaluates it
**Then** only the dedicated lifecycle principal may remove it after proving no active, replayable, retained, or rollback-relevant reference remains
**And** incomplete proof, unsupported consumer versions, or an unexpired compatibility horizon blocks deletion.

## Epic 4: Adopt and Operate the Production Standard

Teams can onboard without deep ECS expertise and demonstrate that every production job is documented, supportable, tested, and ready for controlled pilot rollout.

### Story 4.1: Publish the Scheduled Job Adoption Guide

As an Application Engineer,
I want a complete adoption guide and working examples for the scheduled-job platform,
So that I can deploy a basic job without modifying module internals or needing deep ECS expertise.

**Acceptance Criteria:**

**Given** an engineer opens the platform README
**When** they follow the adoption path
**Then** it explains prerequisites, Cell discovery, job reservation, module configuration, phase-one publication, phase-two activation, verification, and ownership handoff in execution order
**And** it consistently describes Scheduler-to-Cell-to-ECS delivery rather than the superseded direct Scheduler-to-ECS model.

**Given** a consumer needs module configuration details
**When** they use the input and output reference
**Then** every required and optional input, type, default, validation, security implication, and example is documented
**And** every output explains its operational use without exposing secret values or requiring Terraform-state inspection.

**Given** a team integrates its application with the Job Completion Contract
**When** it follows the application guidance
**Then** examples show how to consume supplied job, Occurrence ID, CONFIG, attempt, and Deployment Identity values and emit structured start, success, and failure records
**And** the guide states that success requires correlation with ECS exit evidence and that jobs must not generate their own Occurrence IDs.

**Given** a team reviews security and infrastructure prerequisites
**When** it reads the guide
**Then** it finds explicit guidance for private subnets, bounded security-group egress, NAT or endpoints, separate IAM roles, permissions boundaries, application policy review, secret-reference modes, immutable images, OIDC, state isolation, and protected production Environments
**And** examples contain no credentials, secret values, account-specific assumptions, unrestricted production networking, or unjustified IAM wildcards.

**Given** non-production and production examples are provided
**When** they are initialized and validated
**Then** both use immutable module and workflow references, existing infrastructure inputs, standard tags, retained logs, and documented outputs
**And** the production example additionally enables occurrence-aware completion, notification routing, required alarms, private networking, immutable image identity, and the two-phase activation handshake.

**Given** a consumer selects toolchain versions
**When** it reads `versions.tf` and the compatibility section
**Then** both state Terraform `>= 1.10, < 2.0`, the dated validated Terraform, AWS provider, Python runtime, and Fargate seeds, and the supported Cell/module/contract matrix
**And** dated test versions are distinguished from permanent patch constraints.

**Given** a team changes a schedule, image, IAM policy, network path, secret reference, or module version
**When** it follows lifecycle guidance
**Then** the guide explains review expectations, generation replacement, safe disablement, Deployment Identity, verification, rollback or forward-fix, evidence preservation, and application compensation
**And** it does not suggest direct `RunTask`, manual state edits, schedule mutation outside Terraform, or mutable release references.

**Given** an engineer follows the basic non-production example from a clean repository
**When** the documented validation and deployment steps are timed
**Then** the example can be configured without module-source changes and targets less than four hours for a basic job
**And** assumptions or external approval delays are identified separately from hands-on setup time.

**Given** documentation or examples change
**When** CI runs
**Then** links, generated references, formatting, Terraform validation, example plans, policy scans, contract versions, and immutable pins are checked
**And** stale, contradictory, insecure, or non-executable examples block release.

### Story 4.2: Complete an Actionable Job Runbook

As an On-call Engineer,
I want a completed job-specific Runbook tied to platform alerts and controls,
So that I can diagnose failures, rerun safely, escalate correctly, and recover without guessing.

**Acceptance Criteria:**

**Given** a team creates a production job
**When** it completes the Runbook template
**Then** the Runbook records canonical job ID, owners and escalation paths, account, Region, Environment, schedule and time zone, expected runtime, overlap policy, idempotency or locking, dependencies, notification target, Deployment Identity location, and support hours
**And** unresolved ownership or placeholder values block production readiness.

**Given** the Job Completion Contract
**When** the Runbook documents expected behavior
**Then** it describes the structured start, success, and failure records, authoritative occurrence fields, zero-exit correlation, completion deadline, late and duplicate behavior, and all possible occurrence states
**And** it does not treat Scheduler delivery, log presence, a success marker, or exit code alone as proof of completion.

**Given** an alert is received
**When** an operator follows the alarm mapping
**Then** each schedule-delivery, launch, runtime, completion, log-delivery, and Cell-health alert links to its first diagnostic query, expected evidence, decision point, escalation owner, and response action
**And** every required production alarm maps to at least one tested Runbook procedure.

**Given** an operator investigates a specific occurrence
**When** they use the documented queries
**Then** they can locate the occurrence ledger state, immutable CONFIG, task ARN and events, essential-container exit, structured logs, Scheduler and queue evidence, alert-delivery evidence, and Deployment Identity using supported console, CLI, or query commands
**And** the procedure uses the operator role rather than workload roles or direct table mutation.

**Given** an occurrence is failed, missed, overdue, or ambiguous
**When** the operator follows state-specific guidance
**Then** the Runbook explains how to distinguish delivery, launch, runtime, completion, dependency, and platform failures
**And** it identifies when to wait for reconciliation, disable launch, escalate to Platform, or begin application compensation.

**Given** a manual rerun is considered
**When** the rerun checklist is followed
**Then** it requires authorization, original occurrence and Deployment Identity review, overlap and duplicate-effect assessment, compensation acknowledgement, authenticated command execution, and result verification
**And** it prohibits direct `RunTask`, caller-created Occurrence IDs, schedule edits, or reuse of stale CONFIG.

**Given** rollback or forward-fix is required
**When** the recovery procedure is followed
**Then** it identifies the known-good identity, launch-disablement order, generation retirement, evidence drain or quarantine, fresh-plan deployment, verification, and data-compensation steps
**And** launch cannot resume until scheduling, tasks, logs, occurrence state, alerts, and dependencies are verified.

**Given** a job handles customer or shared data
**When** rollback and rerun procedures are reviewed
**Then** application-specific side effects, idempotency keys, locking, partial writes, reconciliation, and compensating actions are explicit
**And** infrastructure rollback is not represented as automatically undoing application data changes.

**Given** the completed Runbook is reviewed
**When** a tabletop or non-production exercise runs
**Then** a responder who did not author the job can diagnose representative failures and execute the safe escalation or recovery path
**And** findings, elapsed time, missing access, stale commands, and required corrections are recorded before production approval.

**Given** job behavior, platform contracts, alerts, ownership, or dependencies change
**When** deployment readiness runs
**Then** the Runbook version and reviewed source revision must match the proposed Deployment Identity
**And** stale Runbooks, broken links, secret values, unsafe commands, or missing alarm mappings block production.

### Story 4.3: Automate the Production Readiness Gate

As a Production Approver,
I want production readiness backed by complete, attributable, machine-verifiable evidence,
So that no scheduled job is activated with missing security, reliability, or operational controls.

**Acceptance Criteria:**

**Given** a job is proposed for production
**When** the readiness workflow starts
**Then** it creates a versioned evidence record bound to repository, source commit, workflow SHA, plan checksum, Deployment Identity, account, Region, Environment, job ID, CONFIG hash, and schedule generation
**And** evidence from another revision, target, job, plan, or deployment run cannot satisfy the gate.

**Given** technical validation has run
**When** readiness evidence is collected
**Then** it includes Terraform formatting and validation, module and example tests, contract tests, provider-lock verification, security scans, IAM analysis, policy results, representative plan impact, immutable image proof, Cell compatibility, and target verification
**And** every result records its tool or policy version, timestamp, outcome, and artifact checksum.

**Given** production infrastructure controls are evaluated
**When** the gate checks required categories
**Then** it verifies ownership and protected tags, permissions boundaries, least-privilege roles, secret references, private networking, bounded egress, public-IP prohibition, encrypted state, retained logs, occurrence-aware completion, all failure planes, notification routing, and lifecycle acknowledgement
**And** absent or contradictory module outputs block readiness.

**Given** operational readiness is evaluated
**When** the gate checks human-reviewed evidence
**Then** it requires the completed Runbook, alarm-to-procedure mapping, expected runtime, overlap and idempotency declaration, escalation path, rollback or forward-fix plan, application compensation, known limitations, and post-deployment verification plan
**And** each attestation is scoped to the exact Deployment Identity and attributable reviewer.

**Given** approval roles are determined
**When** readiness approval is requested
**Then** Platform Engineering and the Job Owner are mandatory and qualifying IAM or networking changes require Security
**And** self-approval, missing owners, placeholder approvers, stale reviews, or approvals for another revision are rejected.

**Given** an item is incomplete or failed
**When** readiness is evaluated
**Then** production activation remains blocked with a specific remediation and evidence owner
**And** the workflow cannot convert a missing mandatory item into success through a free-form comment.

**Given** an approved policy supports an exception
**When** readiness evaluates the exception
**Then** owner, exact control, resource, justification, approver, expiry or review date, compensating control, and audit trail are required
**And** expired, broad, mismatched, or non-exemptible exceptions fail.

**Given** non-production adoption is still staged
**When** the readiness workflow evaluates dev or staging
**Then** advisory and blocking items follow the approved timeline while invalid Terraform, missing required tags, and obvious secret exposure use the mandated severity
**And** non-production evidence cannot be promoted as production acceptance evidence without production execution.

**Given** readiness completes
**When** its report is published
**Then** authorized reviewers receive a concise pass, fail, exception, and limitation summary with links to access-controlled evidence
**And** the report excludes secret values, binary plans, unrestricted logs, credentials, and other sensitive data.

**Given** any bound input or evidence changes after approval
**When** activation preflight revalidates readiness
**Then** the readiness decision is invalidated and must be recomputed and reapproved
**And** only a passing exact-generation result can authorize the production phase-two plan.

### Story 4.4: Qualify the Platform Through Failure Injection

As a Platform SRE,
I want repeatable end-to-end failure and recovery tests in a disposable Cell,
So that production approval is based on demonstrated detection and containment rather than design claims.

**Acceptance Criteria:**

**Given** an immutable release candidate
**When** qualification begins
**Then** a disposable non-production Cell and representative scheduled-job fixtures are deployed through the standard workflows using production-equivalent contracts and controls
**And** no customer workload, production secret, production state, or production notification target is used.

**Given** supported schedule expressions and time zones
**When** conformance tests run
**Then** Scheduler and the independent materializer agree on occurrence identity and timing across cron, rate, daylight-saving boundaries, adjacent windows, activation anchors, and generation changes
**And** unsupported or divergent cases block qualification.

**Given** schedule-delivery failures are injected
**When** Scheduler target denial, throttling, dropped delivery, DLQ redrive, missing launch evidence, and complete Scheduler-path silence are exercised
**Then** native delivery alarms, Cell-health signals, and occurrence-specific `MISSED` results fire through their intended routes
**And** each alert identifies the correct failure plane and Runbook.

**Given** ECS launch and runtime failures are injected
**When** tests simulate `RunTask` HTTP errors, HTTP 200 with `failures[]`, Process Manager crash after accepted launch, start failure, unexpected stop, and non-zero essential-container exit
**Then** exactly one task is launched at most, every outcome reaches the correct durable occurrence state, and required alerts are delivered
**And** unresolved launch uncertainty becomes `AMBIGUOUS` without a second `RunTask`.

**Given** completion-contract failures are injected
**When** tests simulate missing markers, markers without zero exit, zero exit without a marker, wrong Occurrence ID, delayed prior-run completion, duplicate and conflicting completion, overdue execution, log-delivery failure, and consecutive windows
**Then** no invalid signal satisfies the wrong occurrence and each expected occurrence reaches the canonical result
**And** application text never overrides authoritative AWS task or log identity.

**Given** Cell durability failures are injected
**When** tests simulate poison messages, partial batches, queue retries, delayed GSI visibility, scanner restart, stale horizon, stale canary, Process Manager replay, stranded outbox records, and router crashes before and after publication
**Then** evidence is retried or quarantined safely, deadlines are not skipped, alerts are not stranded, and duplicate processing remains idempotent
**And** actionable Cell alarms fire for shared failures.

**Given** security boundaries are tested
**When** negative tests attempt forged evidence, cross-job CONFIG access, namespace squatting, stale Role IDs, unauthorized transfers, direct ledger writes, arbitrary `RunTask`, unrelated `PassRole`, boundary removal, OIDC mismatch, cross-state access, and operator bypass
**Then** every unauthorized action is denied and attributable
**And** approved operations remain functional through their intended roles.

**Given** rollback and recovery qualification runs
**When** tests disable launch, drain evidence, restore DynamoDB through PITR, switch versioned aliases and contract pointers, replay post-restore evidence, rebuild expectations, reconcile nonterminal occurrences, restore a known-good release, and verify alerts
**Then** measured Cell RPO/RTO and job recovery time are recorded
**And** launch resumes only after all integrity and observability checks pass.

**Given** detection performance is measured
**When** each required failure becomes observable or reaches its declared deadline
**Then** the configured alert reaches the test destination within five minutes
**And** at least 20 accelerated successful windows complete with zero false failure alerts.

**Given** qualification completes
**When** evidence is published
**Then** results are bound to release digests, contract versions, test configuration, account, Region, actors, timestamps, alert receipts, recovery measurements, known limitations, and cleanup status
**And** any failed mandatory scenario blocks production readiness until corrected and rerun.

### Story 4.5: Execute and Evaluate the MVP Pilot

As a Platform Owner,
I want the standard proven with named low-risk jobs and measured adoption outcomes,
So that stakeholders can decide whether to require it for new scheduled jobs and expand rollout safely.

**Acceptance Criteria:**

**Given** pilot planning begins
**When** candidate jobs are selected
**Then** one or two non-customer-facing cleanup, maintenance, reporting, synchronization, or internal batch jobs are chosen with named Job Owners
**And** customer-critical, irreversible, or ownership-unknown workloads are excluded until owners and risks are resolved.

**Given** pilot prerequisites are reviewed
**When** the pilot is authorized
**Then** one non-production and one production account, the primary Region, notification targets, operator access, protected GitHub controls, deployment manifests, completed Runbooks, support escalation, approved schedule subset, and measured recovery objectives are confirmed
**And** unresolved placeholders for account, Region, owner, target, or escalation block execution.

**Given** baseline data is required
**When** two or three recent scheduled-job implementations or pull requests are sampled
**Then** setup time, duplicated Terraform, IAM findings, missing tags, mutable images, missing log retention, missing alarms, unclear rollback, and observability review comments are measured
**And** assumptions such as the current one-to-three-day setup time are replaced or explicitly retained when data is unavailable.

**Given** each pilot job is configured in non-production
**When** the owning team follows the standard path
**Then** it reserves the job, uses the published module and workflow, completes phase-one and phase-two deployment, emits occurrence-aware completion, routes test alerts, and passes readiness checks
**And** application code, Terraform changes, approvals, waiting time, and hands-on setup time are measured separately.

**Given** non-production validation succeeds
**When** the pilot job is promoted to production
**Then** Platform Engineering and the Job Owner approve the exact plan, required Security review is complete, the schedule generation is materialized before activation, and production notification and on-call paths are verified
**And** launch remains disabled if any mandatory evidence has changed or expired.

**Given** a pilot job is active
**When** its observation window runs
**Then** expected, started, succeeded, failed, overdue, missed, and ambiguous behavior is verified as applicable through real or controlled occurrences
**And** operators demonstrate log, ECS event, ledger, alert, rerun, disablement, rollback, and escalation procedures from the completed Runbook.

**Given** pilot efficiency is evaluated
**When** measured results are compared with the baseline
**Then** a basic-job setup target of less than four hours and at least 50 percent reduction are reported
**And** required tags, logs, alarms, immutable images, explicit IAM, completed Runbooks, and occurrence-aware completion are measured for every pilot job.

**Given** pilot security and review quality are evaluated
**When** findings are summarized
**Then** repeated IAM wildcard, privilege, missing observability, tagging, mutable-image, secret, networking, and rollback findings are compared with the baseline
**And** new platform-caused findings, exceptions, operational friction, and unresolved risks are assigned owners and target dates.

**Given** pilot rollback readiness is tested
**When** a controlled rollback or schedule-disablement exercise runs
**Then** launch is disabled, the known-good Deployment Identity is restored or verified, in-flight evidence is reconciled, application compensation is considered, and scheduling, logs, occurrence state, and alerts are revalidated
**And** actual recovery timing is compared with the approved objectives.

**Given** pilot evidence is complete
**When** stakeholders review the outcome
**Then** Platform Engineering, Job Owners, Security or Cloud/IAM reviewers, and operations record acceptance, conditional acceptance, or rejection with reasons
**And** failed mandatory criteria prevent broad production adoption.

**Given** the pilot is accepted
**When** rollout policy is published
**Then** all new ECS scheduled jobs use the standard module, existing jobs migrate when touched or improved, and non-production policy enforcement advances on the approved timeline
**And** adoption metrics, issue ownership, release communication, and future enhancements are tracked without forcing immediate migration of every existing job.
