---
story_key: 1-12-monitor-cell-health-with-the-canary
baseline_commit: 3ca936fe9675d2c505ceb17453242730c1cef20d
---

# Story 1.12: Monitor Cell Health with the Canary

Status: in-progress

## Story

As a Platform On-call Engineer,
I want bounded health signals and tested alarms for every shared Cell failure plane,
so that platform degradation is detected before scheduled-job failures are misdiagnosed or missed.

## Acceptance Criteria

1. Metrics and alarms cover expectation-horizon freshness, schedule conformance, Scheduler attempts and delivery failures, source/ingress queue age and depth, every DLQ, Lambda errors/throttles/duration/concurrency, DynamoDB throttles and conditional failures, deadline lag, log-subscription delivery, outbox reconciliation, notification delivery, and processed-canary freshness. Each signal has explicit threshold, evaluation period, missing-data behavior, owner, severity, and HTTPS runbook reference.
2. Metric dimensions are bounded to Cell, job, Environment, state, and failure-plane values defined by the Compatibility Package. Never use occurrence IDs, task ARNs, log streams, error text, source ARNs, target ARNs, or other unbounded values as dimensions.
3. A successful canary occurrence emits an exact-Cell processed heartbeat only after Scheduler, normalization, Process Manager launch, ECS evidence, completion logs, and terminal ledger reduction succeed. The heartbeat is not proof for non-canary jobs.
4. Scheduler delivery denial, throttling, dropped delivery, retry exhaustion, or Scheduler DLQ breach produces one actionable Cell incident with Cell/account/Region/Environment/failure-plane/runbook context, while expected occurrences still become per-job MISSED results.
5. Horizon, queue-age, scanner-watermark, outbox, or canary-heartbeat staleness alarms within five minutes without relying solely on Lambda error metrics.
6. Aggregate shared-Cell faults produce one deduplicated Cell incident per policy window through the Alert Router and notification ledger; distinct occurrence failures remain separate Job Owner notifications.
7. Recovery thresholds return alarms to OK without deleting unresolved occurrence failures or delivery evidence; alarm history, receipts, state changes, and recovery timestamps remain attributable for configured retention.
8. Production health alarms/destinations are mandatory; approved non-production routes may use test/low-noise destinations, but disabling optional notifications cannot disable metrics, DLQs, or canary evaluation.
9. Metric cardinality, alarm count, log retention, query frequency, and fixed Cell cost are documented and bounded; invalid dimensions or unsupported retention fail validation.
10. Credential-free tests inject Scheduler denial, horizon staleness, queue backlog, DLQ messages, Lambda failures, DynamoDB throttling, scanner lag, log-subscription failure, stale canary, stranded outbox, and target denial. Each reaches the test destination within five minutes of observability, and 20 accelerated healthy canary windows produce zero false Cell or occurrence alerts.

## Tasks / Subtasks

- [ ] 1. Extend the observability contract/catalogs (AC: 1, 2, 8, 9)
  - [ ] Inventory existing metric names/dimensions and add bounded Cell-health metric, alarm, threshold, severity, owner, missing-data, retention, and runbook metadata without changing prior contract bytes unnecessarily.
  - [ ] Add validation fixtures for unbounded dimensions, unsupported retention, production destination requirements, and aggregate-vs-occurrence routing policy.

- [ ] 2. Implement bounded health metrics and processed heartbeat (AC: 1, 2, 3, 5)
  - [ ] Extend established runtime metric helpers in deadline scanner, Process Manager, normalizer, log ingestor, Alert Router, and materializer only where needed; preserve authoritative writers and existing metric cardinality limits.
  - [ ] Emit the processed-canary heartbeat only after the complete canary path reaches terminal success, with a durable timestamp/checkpoint suitable for freshness alarms.
  - [ ] Ensure stale detection uses bounded Cell/job dimensions and does not treat one component's Lambda success as end-to-end health.

- [ ] 3. Add Cell-health alarms and routing (AC: 1, 4, 5, 6, 7, 8)
  - [ ] Add explicit CloudWatch alarms for freshness, queues/DLQs, Lambda, DynamoDB, Scheduler, deadline, outbox, notification, log subscription, and canary heartbeat signals with bounded evaluation and missing-data behavior.
  - [ ] Route aggregate alarm state changes through the existing Alert Router/notification ledger with deterministic policy-window identity and Cell context; never suppress occurrence alerts.
  - [ ] Add mandatory production destination validation and optional non-production notification controls that do not disable collection, retention, or evaluation.

- [ ] 4. Add cost, retention, and IAM/Terraform integration (AC: 1, 8, 9)
  - [ ] Preserve stable resource addresses, Cell KMS encryption, PITR/deletion protection, tags, log retention, and least-privilege boundaries. Do not grant alarm components occurrence/config mutation, ECS, IAM, STS, or Scheduler mutation authority.
  - [ ] Add module inputs/outputs and example coverage for thresholds, schedules, retention, alarm actions, runbooks, and explicit enable/disable behavior. Document expected fixed Cell cost and query/cardinality bounds.

- [ ] 5. Prove failure and recovery behavior (AC: 1-10)
  - [ ] Add runtime/contract tests for bounded dimensions, heartbeat ordering, aggregate deduplication, recovery, missing data, and occurrence-alert independence.
  - [ ] Add credential-free disposable-Cell or deterministic simulator tests for every injected failure in AC 10 and 20 healthy accelerated windows; record live-AWS limitations.
  - [ ] Run strict mypy, Ruff, all tests, Terraform fmt/backend-free validate, Checkov/hygiene checks, and git diff --check.

## Dev Notes

### Architecture and scope guardrails

- The Cell owns shared observability and health alarms. Process Manager remains the only occurrence-state writer; health monitoring must never mutate occurrence state or stop/relaunch tasks.
- Reuse `runtime/alert_router` and its notification ledger for aggregate Cell incidents, but use a distinct deterministic aggregate policy-window identity. Occurrence alerts from Story 1.11 remain independent.
- Metrics must be projections of bounded state. Never put occurrence ID, task ARN, log stream, raw error, source ARN, target ARN, or arbitrary CONFIG values in dimensions.
- Stale/freshness alarms must be independent of Lambda error metrics so silent stalls are detected. Recovery changes must retain alarm history and delivery evidence.
- Production destination requirements must fail at Terraform validation time; non-production opt-out must affect notifications only, not metrics, DLQs, or heartbeat evaluation.

### Existing components to reuse

- `runtime/deadline_scanner`, `runtime/evidence_normalizer`, `runtime/log_ingestor`, `runtime/process_manager`, `runtime/occurrence_materializer`, and `runtime/alert_router` contain established structured metric and identity patterns. Read each current metric helper before editing.
- `contracts/v1/catalogs/metrics-alerts.json`, `contracts/v1/catalogs/iam.json`, `contracts/v1/catalogs/keys-and-correlation.json`, `contracts/v1/catalogs/queue-lambda-constraints.json`, and existing metric/secret-safety fixtures are normative.
- `modules/ecs-scheduled-job-platform/main.tf`, `variables.tf`, `outputs.tf`, `README.md`, and `examples/basic/*` contain the stable Cell resources, KMS, retention, EventBridge, Lambda, queue/DLQ, and Cell Contract patterns. Extend stable addresses; do not create a parallel platform module.
- Story 1.11 review fixes are mandatory precedent: avoid package import cycles, scope IAM conditions to the actual key used, paginate bounded reconciliation, use atomic delivery leases, validate authoritative CONFIG, expose enable/disable controls, and keep metrics failure-independent.

### Testing and operational requirements

- Use credential-free fakes/simulators for normal and failure paths; no live AWS credentials, Terraform state, plans, secrets, or generated artifacts in the repository.
- Verify alarm `TreatMissingData`, evaluation periods, threshold units, action routing, runbook URI, owner/severity metadata, and production/non-production behavior in contract tests.
- Document rollback: disable optional alarm actions or the health-alarm rule set while retaining metrics, DLQs, logs, heartbeat evidence, occurrence outbox, notification ledger, and alarm history.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-1.12-Monitor-Cell-Health-with-the-Canary`]
- [Source: `_bmad-output/implementation-artifacts/1-11-deliver-occurrence-alerts-reliably.md`]
- [Source: `_bmad-output/project-context.md`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]
- [Source: `contracts/v1/catalogs/metrics-alerts.json`]
- [Source: `modules/ecs-scheduled-job-platform/main.tf`]

## Dev Agent Record

### Review Findings

- [x] [Review][Patch] Alert Router cannot acknowledge delivered outbox items [modules/ecs-scheduled-job-platform/main.tf:1014-1022; runtime/alert_router/src/alert_router/handler.py:221-239] — `UpdateItem` now uses a base-table permission; successful notifications can complete the outbox.
- [x] [Review][Patch] Non-canary occurrence alerts are blocked by canary-only IAM conditions [modules/ecs-scheduled-job-platform/main.tf:1003-1033; runtime/alert_router/src/alert_router/handler.py:331-345] — occurrence/config reads now allow the shared Cell job-key namespace.
- [x] [Review][Patch] Most declared Cell-health metrics have no authoritative producers [modules/ecs-scheduled-job-platform/main.tf:203-213,1217-1234] — alarms now use AWS service metrics or existing bounded platform metrics for the declared resources.
- [x] [Review][Patch] Retry alarm listens to a metric name the router never emits [modules/ecs-scheduled-job-platform/main.tf:1199-1213; runtime/alert_router/src/alert_router/handler.py:353-363] — the alarm now listens to `Retry`, matching the router producer.
- [x] [Review][Patch] Recovery transitions are emitted as failed Cell incidents [modules/ecs-scheduled-job-platform/main.tf:1217-1234; runtime/alert_router/src/alert_router/handler.py:242-303] — alarm OK actions and explicit `RECOVERED` payload state are implemented.
- [x] [Review][Patch] Cell-health alarm dimensions and missing-data policy can mask or mix Cells [modules/ecs-scheduled-job-platform/main.tf:1217-1233] — custom metrics include Cell/environment dimensions, service metrics bind to exact AWS resources, and health alarms breach on missing data.
- [x] [Review][Patch] Notification lease ownership is stale on retry and absent in Cell-alarm completion [runtime/alert_router/src/alert_router/ledger.py:88-107; runtime/alert_router/src/alert_router/handler.py:293-303] — retries rotate the lease token and Cell-alarm completion uses token-bound delivered/ambiguous transitions.
- [x] [Review][Patch] Stream consumption processes unrelated ledger writes with unnecessary image exposure [modules/ecs-scheduled-job-platform/main.tf:593-601,1128-1144] — the stream now uses `NEW_IMAGE` and filters to ALERT_OUTBOX inserts/modifications.
- [x] [Review][Patch] Alert Router alarm permission is broader than the alarm set [modules/ecs-scheduled-job-platform/main.tf:1236-1242] — each alarm permission now has an exact `source_arn` and source account.
- [x] [Review][Patch] AC10 qualification and operational bounds are absent [tests/contract/test_cell_health_catalog.py:1-27; modules/ecs-scheduled-job-platform/README.md] — bounded cost/cardinality/query documentation and credential-free failure/recovery plus 20-window qualification fixtures are now present.

### Agent Model Used

GPT-5

### Debug Log References

- Context assembled from Epic 1 Story 1.12, the completed Story 1.11 implementation/review findings, project context, AWS/Terraform standards, existing runtime metric implementations, and Cell Terraform patterns.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Initial implementation slice completed: bounded Cell-health catalog metadata, post-commit canary heartbeat, canary freshness and Alert Router retry alarms, and updated Terraform boundary/manifest tests.
- Validation: 150 tests and 192 contract subtests passed; mypy, Terraform formatting, and diff hygiene pass. Terraform provider validation remains environment-blocked by registry DNS.
- Review follow-up validation: 151 tests and 193 contract subtests pass after restoring Deadline Scanner IAM, making Alert Router packaging self-contained, adding Cell-scoped heartbeat/lease ownership, isolating reconciliation failures, and routing alarm actions to the router Lambda. Mypy, Terraform formatting, and diff checks also pass. Story remains in progress because health metric producers, full alarm metadata/policy controls, and AC 10 failure/cost qualification are incomplete.
- Development continuation: concrete review regressions and the declared credential-free qualification matrix are implemented; the story remains in progress pending final acceptance sign-off and live-AWS rollout qualification.
- Code-review remediation: all ten patch findings were applied. Validation now passes with 152 tests and 193 contract subtests; the Terraform validator also passes with only existing AWS provider deprecation warnings. The qualification suite is credential-free and deterministic; live-AWS delivery timing remains an operational rollout check.

### File List

- `_bmad-output/implementation-artifacts/1-12-monitor-cell-health-with-the-canary.md`
- `contracts/v1/catalogs/metrics-alerts.json`, `contracts/manifest.json`, `contracts/releases/1.0.0.json`
- `runtime/process_manager/src/process_manager/handler.py`
- `runtime/process_manager/src/process_manager/ledger.py`
- `runtime/alert_router/src/alert_router/domain.py`, `handler.py`, `ledger.py`, `storage.py`
- `runtime/alert_router/tests/test_alert_router.py`, `test_domain.py`, `test_handler.py`
- `modules/ecs-scheduled-job-platform/main.tf`, `modules/ecs-scheduled-job-platform/outputs.tf`
- `modules/ecs-scheduled-job-platform/variables.tf`, `README.md`, `examples/basic/*`
- `tests/contract/test_cell_foundation.py`, `tests/contract/test_repository_structure.py`, `tests/contract/test_cell_health_catalog.py`
- `tests/contract/test_cell_health_qualification.py`

### Change Log

- 2026-07-21: Created implementation-ready Story 1.12 with bounded observability, alarm, heartbeat, routing, cost, and failure-qualification guardrails.
- 2026-07-21: Started Story 1.12 implementation with heartbeat and initial health alarms.
- 2026-07-21: Expanded the Cell-health alarm matrix and added bounded catalog contract coverage.
