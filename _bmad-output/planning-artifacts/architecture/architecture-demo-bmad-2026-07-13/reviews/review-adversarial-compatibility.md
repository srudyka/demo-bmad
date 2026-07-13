# Adversarial Compatibility Review

## Verdict

**FAIL - independently built units can obey every stated Architecture Decision and still be mutually incompatible or violate Cell data integrity.**

The spine has a strong component decomposition and useful invariants, but it stops one level above several contracts that independent module/runtime teams need. The highest-risk holes are not cosmetic schema choices: they can split one scheduled occurrence into two ledger records, let a job-scoped Terraform role mutate runtime occurrence state, launch an unreviewed task-definition revision, or break every existing job during a Cell identity upgrade.

This review treats each viable pair of compliant-but-conflicting implementations as a missing architecture contract. Findings ADV-01 through ADV-08 should block independent implementation. ADV-09 through ADV-13 should be resolved before integration-test design.

## Review Method

For each architecture boundary, construct two units owned and built independently using only `ARCHITECTURE-SPINE.md`. A hole exists when both units can reasonably claim compliance with every applicable AD and convention but cannot interoperate safely. The review attacks shared data shapes, ownership, state transitions, IAM, schedule evaluation, deployment, and operations, with emphasis on multi-account security and data integrity.

## Critical Findings

### ADV-01: Compliant producers can calculate different Occurrence IDs for the same schedule window

**Severity:** Critical  
**Locations:** AD-3 (lines 59-64), AD-4 (lines 65-69), AD-5 (lines 71-75), consistency conventions (lines 174-180).

**Pair:** `EXPECTATION` Scheduler producer vs `LAUNCH` Scheduler producer, with the Process Manager as consumer.

**Compliant implementation A:** The expectation event uses `schema_version = "1.0"`, normalizes scheduled time as `2026-07-13T10:00:00Z`, and hashes those bytes with the canonical job ID.

**Compliant implementation B:** The launch event is independently upgraded to `schema_version = "1.1"`, or normalizes the same instant as `2026-07-13T10:00:00.000Z`. Both values are valid versioned envelopes and RFC 3339 UTC representations. It hashes its own schema version and normalized string as AD-4 instructs.

**Conflict:** The two signals produce different `occurrence_id` values for one schedule window. The Process Manager creates two occurrences: one can become `MISSED` and the other can launch and complete. Retries and completion logs can then correlate to only one side. The architecture's central integrity guarantee fails even though both producers obey AD-3 through AD-5.

**Required contract:** Define a distinct, immutable `occurrence_identity_version` unrelated to event schema versions; exact UTF-8 byte serialization; canonical job-ID grammar and normalization; exact timestamp precision and formatting; and published test vectors. The Process Manager must recompute and reject mismatched IDs. Event schema upgrades must never change occurrence identity.

### ADV-02: Terraform CONFIG ownership and runtime ledger ownership are not enforceable in one table

**Severity:** Critical  
**Locations:** AD-2 (lines 53-57), AD-5 (lines 71-75), AD-6 (lines 77-81), AD-12 (lines 128-132), AD-15 (lines 146-150), DynamoDB conventions (line 180).

**Pair:** Per-job Terraform apply role/module vs Process Manager, sharing the DynamoDB control ledger.

**Compliant implementation A:** The job module uses Terraform to `PutItem` immutable `CONFIG#<hash>` records into `PK=JOB#<job_id>`. Its IAM grants `dynamodb:PutItem` on the Cell ledger for that job partition so Terraform can own CONFIG as required.

**Compliant implementation B:** The Process Manager owns `OCC#...` and `EVENT#...` items in the same job partition and relies on conditional expressions in its own writes, exactly as AD-6 requires.

**Conflict:** The job apply principal's table-level `PutItem`, `UpdateItem`, or `DeleteItem` authorization can also target `OCC#...` and `EVENT#...` sort keys in the same partition unless a separately specified enforceable control prevents it. A compromised workflow or faulty provider operation can forge success, erase failure evidence, or reset processed-event markers. The sentence "Terraform owns CONFIG" is a logical ownership statement, not an IAM/data boundary. In a multi-team account, this defeats the single-writer invariant and audit trust.

**Required contract:** Use a separate CONFIG table or a Cell-owned validated configuration API/queue so consumer apply roles never receive write access to runtime ledger items. If one table is retained, specify and prove an enforceable IAM/resource-policy mechanism that restricts both partition and item type, plus deny tests for `OCC`/`EVENT` mutation and cross-job CONFIG writes. Define immutable CONFIG creation as conditional create-only and assign deletion/retention to a trusted Cell lifecycle principal.

## High Findings

### ADV-03: The Cell Contract has no interoperable manifest schema or compatibility negotiation

**Severity:** High  
**Locations:** AD-2 (lines 53-57), AD-5 (lines 71-75), AD-15 (lines 146-150), AD-17 (lines 158-162), structural seed (lines 199-216).

**Pair:** `ecs-scheduled-job-platform` module as SSM publisher vs `ecs-scheduled-job` module as consumer.

**Compliant implementation A:** The Cell publishes a versioned JSON manifest at `/platform/ecs-jobs/cell` containing `ingress_queue_arn`, `ledger_table_name`, `process_manager_role_arn`, and `contract_version = 1`.

**Compliant implementation B:** The job module reads a versioned SSM manifest at `/<environment>/ecs-scheduled-jobs/cell`, expects nested `ingress.queue_arn`, `ledger.table_arn`, a KMS key ARN, event-schema ranges, and semantic `contract_version = "1.0.0"`.

**Conflict:** Both comply with "versioned contract manifest in SSM" but cannot plan together. The spine does not define parameter path/discovery, JSON schema, required/optional fields, ARN versus name forms, schema-version grammar, backward-compatibility rules, minimum/maximum supported Cell versions, integrity checks, or failure behavior.

**Required contract:** Publish a normative Cell Contract JSON Schema with canonical SSM path derivation, field semantics and ARN forms, version negotiation, compatibility matrix, unknown-field behavior, checksum/signature or trusted-source validation, and conformance fixtures consumed by both modules.

### ADV-04: The event envelope cannot guarantee globally unique processed-event keys

**Severity:** High  
**Locations:** AD-5 (lines 71-75), AD-6 (lines 77-81), AD-11 (lines 122-126), event/DynamoDB conventions (lines 178-180).

**Pair:** Log Ingestor, Deadline Scanner, Scheduler transformers, and ECS event transformer as independent evidence producers vs Process Manager deduplication.

**Compliant implementation A:** The Log Ingestor emits `source_event_id = "abc"` and `event_type = "completion.observed.v1"`.

**Compliant implementation B:** The Deadline Scanner independently emits `source_event_id = "abc"` and `event_type = "deadline.reached.v1"`. Both envelopes contain every required AD-5 field.

**Conflict:** The DynamoDB convention requires `EVENT#<source>#<id>`, but the mandatory envelope has no canonical `source` field or source namespace. A Process Manager using only `source_event_id` collides; one inferring source from `event_type` can change deduplication when event types version; one using AWS service name can collide between multiple rules/functions. Legitimate evidence can be silently treated as already processed, or replay can create a second record under a different inferred source.

**Required contract:** Add immutable `producer_id` and `producer_event_id` fields with registered producer namespaces and per-producer uniqueness rules. Define the exact processed-event key serialization and retention horizon. Require the event type's major suffix to agree with `schema_version`, and reject disagreement before deduplication.

### ADV-05: Paired schedule generation is declared but absent from the runtime envelope and transition checks

**Severity:** High  
**Locations:** AD-3 (lines 59-64), AD-5 (lines 71-75), AD-7 (lines 83-102), AD-18 (lines 164-168).

**Pair:** Expectation schedule resource vs launch schedule resource vs Process Manager during a two-phase schedule update.

**Compliant implementation A:** The expectation schedule carries schedule-generation hash `G1` in a tag or payload field.

**Compliant implementation B:** Due to Terraform's sequential apply or rollback, the launch schedule temporarily carries `G2`; its AD-5 envelope is still valid because `schedule_generation` is not a required envelope field. The Process Manager follows AD-7, which has no generation mismatch transition.

**Conflict:** Signals from different schedule generations can be combined into one occurrence and launch a task against a schedule contract that was never jointly active. AD-18's operational drain procedure reduces risk but does not give the runtime a field or rule with which to detect half-updated pairs, stale retries, or queued pre-change evidence.

**Required contract:** Make `schedule_generation` a mandatory immutable envelope field for every schedule-derived event and CONFIG record. Define how the Process Manager handles mismatches, queued old generations, disabled schedules, rollback generations, and drain completion. Add Terraform preconditions plus integration tests that interrupt each apply step.

### ADV-06: The state machine has no result for valid out-of-order evidence

**Severity:** High  
**Locations:** AD-3 (lines 59-64), AD-6 and AD-7 (lines 77-102), AD-9 through AD-11 (lines 110-126).

**Pair:** Independent SQS producers and Process Manager under standard-queue at-least-once delivery.

**Compliant implementation A:** `LAUNCH`, ECS `RUNNING`, or a completion log reaches SQS before `EXPECTATION`; Scheduler groups, EventBridge, Logs, and SQS offer no cross-source ordering.

**Compliant implementation B:** The Process Manager implements only the canonical diagram, whose initial state is `EXPECTED` and whose transitions assume expectation exists before started/completed/deadline evidence.

**Conflict:** The Process Manager must invent behavior: discard, DLQ, buffer, synthesize `EXPECTED`, launch before expectation, or mark ambiguous. Each choice can comply with the written state list while producing different launches and terminal states. Two implementations cannot share replay fixtures, and one can create duplicate tasks when late expectation/launch evidence arrives.

**Required contract:** Provide a complete transition table for every evidence type against absent and existing states, including late expectation, launch-first, completion-first, deadline-first, duplicates, conflicts, and DLQ replay. Transitions must be commutative/idempotent where the evidence set is equivalent. Publish executable model tests with all bounded permutations.

### ADV-07: ECS lifecycle and completion producers have no canonical task-to-occurrence correlation contract

**Severity:** High  
**Locations:** Diagram lines 32-35; AD-5 (lines 71-75), AD-8 and AD-9 (lines 104-114), log convention (line 182).

**Pair:** Process Manager `RunTask` caller vs ECS task-event transformer vs application container/log ingestor.

**Compliant implementation A:** The Process Manager uses the Occurrence ID only as `clientToken` and records returned task ARNs in DynamoDB.

**Compliant implementation B:** The ECS event transformer receives task ARN, task-definition ARN, cluster ARN, `startedBy`, group, tags if enabled, and container exits, but AWS lifecycle events do not expose the original `RunTask` client token. The application emits structured JSON with occurrence ID but chooses its own environment-variable name and task-attempt semantics.

**Conflict:** The transformer cannot deterministically derive occurrence ID without querying an unspecified index, inspecting a required tag/`startedBy` contract, or depending on write ordering in the ledger. Logs can arrive before the returned task ARN is recorded. Independent implementations can use ECS tags, `startedBy`, task group, environment overrides, or ledger lookup and fail to correlate one another's evidence.

**Required contract:** Define the exact `RunTask` fields and tags used to carry `job_id`, `occurrence_id`, `config_version`, and attempt identity; enable managed tag propagation where required; define the task-ARN index and race handling; specify container environment names and structured completion schema; and require the event transformer to verify task family, cluster, and Cell ownership before accepting evidence.

### ADV-08: Cell identity upgrades can break every existing job launch role

**Severity:** High  
**Locations:** AD-2 (lines 53-57), AD-8 (lines 104-108), AD-12 (lines 128-132), AD-15 through AD-18 (lines 146-168).

**Pair:** Cell module/Process Manager deployment vs independently versioned job module/launch roles.

**Compliant implementation A:** A Cell upgrade replaces or renames the Process Manager IAM role and publishes the new ARN in a new versioned Cell Contract.

**Compliant implementation B:** Existing job launch roles trust only the old Process Manager role, satisfying least privilege and immutable prior deployment. New job modules trust only the new role. Neither module mutates resources owned by the other.

**Conflict:** Upgrading the Cell first makes the new Process Manager unable to launch existing jobs; updating jobs first trusts a principal that may not exist or be active. AD-18 defines two-phase schedule changes but no expand/migrate/contract protocol for shared identity, event schema, DynamoDB indexes, Lambda code, or Cell Contract changes. Rollback can be equally incompatible with queued newer events.

**Required contract:** Define Cell/job compatibility ranges and a zero-downtime upgrade protocol: additive contract publication, dual-trust overlap or stable non-replaced principal, consumer readiness inventory, queued-event compatibility, schema migration order, cutover, verification, and delayed removal. Include rollback across both old and new event/config versions.

### ADV-09: A reviewed CONFIG does not guarantee the exact task-definition revision launched

**Severity:** High  
**Locations:** AD-5 (lines 71-75), AD-8 (lines 104-108), AD-12 (lines 128-132), AD-17 (lines 158-162).

**Pair:** Job Terraform module/task-definition publisher vs Process Manager/launch role.

**Compliant implementation A:** The job module creates several immutable task-definition revisions in one family and stores a launch-relevant CONFIG hash.

**Compliant implementation B:** The launch role permits that one family, and the Process Manager calls `RunTask` with a family name or an under-specified CONFIG field, satisfying AD-8's stated family restriction.

**Conflict:** ECS resolves the latest active revision, which can differ from the reviewed revision represented by CONFIG and Deployment Identity. An old or emergency revision in the allowed family can also be selected without violating the IAM family boundary. Image immutability does not help if the wrong immutable revision is launched.

**Required contract:** Require CONFIG to store the full task-definition ARN including revision, have the Process Manager call that exact ARN, verify its family/account/Region/config hash, and record it before launch. Define how IAM scopes the family while runtime validation pins the revision, and add negative tests for family-only and mismatched-revision launches.

## Medium Findings

### ADV-10: Deadline Scanner and ledger table can disagree on the due-occurrence index

**Severity:** Medium  
**Locations:** AD-7 (lines 83-102), AD-10 (lines 116-120), DynamoDB convention (line 180), structural seed (lines 201-212).

**Pair:** Cell Terraform table/GSI definition vs Deadline Scanner query implementation.

**Hole:** The spine names a "deadline-bucket index" but defines no GSI names, partition/sort-key encoding, bucket size/time zone, sparse-item rules, pagination/checkpointing, read consistency, late-write behavior, or index-lag tolerance. A table module can use hourly epoch buckets while the scanner expects minute RFC3339 buckets; both comply. Due occurrences may never be scanned or may alert twice.

**Required contract:** Specify the ledger item JSON schema and every key/index encoding with test vectors, scanner watermark/checkpoint semantics, GSI-lag allowance, pagination, retry, and duplicate deadline evidence behavior.

### ADV-11: Metric producers, alarms, and Alert Router lack a shared operational schema

**Severity:** Medium  
**Locations:** AD-14 (lines 140-144), metrics convention (line 183), capability map lines 234-239.

**Pair:** Process Manager metric emitter vs per-job Terraform alarm resources vs Alert Router.

**Hole:** Bounded dimension names are specified, but metric namespace, name, unit, value semantics, periods, statistics, missing-data policy, alarm naming/tags, and alarm-to-current-occurrence lookup are not. One producer can emit `OccurrenceState=1` in namespace A while alarms watch `JobFailures` in namespace B. Even if an alarm fires, its state-change event does not identify a unique occurrence; choosing the "latest" ledger item can enrich an alert with the wrong run during overlap.

**Required contract:** Publish a metric/alarm catalog and Alarm Router event contract. Alarm identity must map deterministically to job/config/failure plane; alert enrichment must select occurrence by durable alarm context rather than an unqualified latest-item query.

### ADV-12: Queue and Lambda runtime settings can be individually valid but operationally incompatible

**Severity:** Medium  
**Locations:** AD-11 (lines 122-126), AD-12 (lines 128-132), retention default line 248.

**Pair:** Cell SQS module/event-source mapping vs Process Manager Lambda implementation.

**Hole:** The architecture requires partial-batch responses but does not bind Lambda timeout, SQS visibility timeout, batch size/window, concurrency, reserved concurrency, `maxReceiveCount`, maximum event age, payload size, or `ReportBatchItemFailures` configuration. A 15-minute Lambda with a 5-minute visibility timeout and batch partial failures can process the same launch concurrently. A low redrive threshold can move transiently blocked events to DLQ before CONFIG propagation completes.

**Required contract:** Define validated inequalities and defaults across queue, event-source mapping, Lambda timeout/concurrency, idempotency, redrive, retention, and throughput. Contract tests must force timeout, partial failure, throttling, and replay while proving at most one ECS task launch.

### ADV-13: OIDC subject generation is split across GitHub and Terraform without a canonical byte contract

**Severity:** Medium  
**Locations:** AD-16 (lines 152-156), stack lines 187-197, Open Assumption A-3 (line 255).

**Pair:** GitHub organization subject-template configuration/caller workflow vs AWS IAM trust policy Terraform.

**Hole:** The spine requires immutable repository IDs, Environment, and `job_workflow_ref` in exact `sub`, but it does not define the claim-template JSON, claim ordering, URL/colon encoding, reusable-workflow ref form, audience partition variants, or onboarding verification. GitHub can emit one valid custom subject while Terraform trusts a differently ordered or name-based exact string. Both sides believe they implemented AD-16, but production cannot assume the role; a fallback to wildcards would weaken isolation.

**Required contract:** Check in the exact GitHub subject-template definition and deterministic IAM subject renderer, with live-token onboarding verification and positive/negative fixtures for repository transfer, Environment, ref, reusable-workflow SHA, AWS partition/audience, and unauthorized callers.

## Ownership Holes

The spine should also assign Terraform/runtime ownership for these shared edges before implementation:

- CloudWatch Logs subscription filters and Lambda invoke permissions between each job log group and shared Log Ingestor.
- EventBridge ECS task-event rules/filtering and permissions between per-job task definitions and Cell ingress.
- Per-job CloudWatch alarms versus shared metric namespace and Alert Router integration.
- Shared Scheduler DLQ resource policy versus per-job Scheduler execution roles.
- CONFIG retention/garbage collection versus queued messages that still reference old `config_version` values.
- Cell Contract replacement/retention versus existing job state pinned to older manifests.

Without one declared owner per resource and lifecycle, two Terraform roots can both manage the same edge or each assume the other owns it.

## Minimum Compatibility Package

Before teams build modules and runtime components independently, the architecture needs a checked-in compatibility package containing:

1. Cell Contract JSON Schema, path convention, version negotiation, and fixtures.
2. Event-envelope schemas per event type, producer registry, identity test vectors, and processed-event key rules.
3. CONFIG, OCCURRENCE, EVENT, and task-attempt schemas plus DynamoDB key/GSI encodings.
4. Complete commutative occurrence transition table and executable model tests.
5. Exact `RunTask`, task tagging/environment, lifecycle-event, and completion-log correlation contract.
6. IAM principal/resource matrix including CONFIG-versus-ledger mutation enforcement and Cell identity rotation.
7. Queue/Lambda operational parameter contract and replay fixtures.
8. Metric/alarm/alert schema with deterministic occurrence enrichment.
9. Cell/job upgrade, migration, compatibility, and rollback protocol.
10. Exact GitHub OIDC subject-template and AWS trust rendering fixtures.

