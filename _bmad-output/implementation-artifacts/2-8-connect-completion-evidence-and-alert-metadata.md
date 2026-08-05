---
baseline_commit: 04e32f9
---

# Story 2.8: Connect Completion Evidence and Alert Metadata

Status: done

## Story

As a Job Owner,
I want my job's completion records and operational ownership connected to the Platform Cell,
so that non-production failures are correlated and routed with enough context to diagnose them.

## Acceptance Criteria

1. **Occurrence-aware log subscription.** Given a job has a retained log group and validated CONFIG, when occurrence-aware completion is enabled, the job root creates the exact CloudWatch Logs subscription defined by the Cell Contract for its registered log group. Cell delivery accepts only the expected source account, log-group ARN, stream mapping, job ownership generation, and permitted completion schema.

2. **Structured completion contract.** Given the application emits structured start, success, or failure records, when the Cell log ingestor processes them, each record asserts job ID, Occurrence ID, CONFIG version, attempt, timestamp, status, exit code when available, and sanitized error reason. AWS-generated log-group/stream metadata and task-ARN mapping remain authoritative over application assertions.

3. **Success requires correlated evidence.** Given an occurrence reports success, when completion is reduced, exactly one accepted success record for attempt zero must correlate with a zero essential-container exit. An uncorrelated marker, adjacent-window marker, log count, Scheduler success metric, duplicate marker, or zero exit alone cannot satisfy completion.

4. **Operational metadata.** Given job operational metadata is declared, when CONFIG validation runs, it records Job Owner, Runbook URI, completion deadline, log retention, detection mode, configured notification target, and escalation classification. Production declarations require a non-placeholder owner, completed Runbook location, occurrence-aware mode, and production notification target even though Epic 2 cannot activate production.

5. **Cell-routed non-production alerts.** Given a non-production notification target is supplied, when a job failure or completion-contract alert is emitted, it routes through the Cell Alert Router to the registered low-noise/test destination with job, Occurrence ID, Environment, account, Region, failure plane, state, detection time, Deployment Identity, owner, and Runbook URI. The job role and module cannot publish directly to arbitrary destinations.

6. **Explicit reduced routing.** Given non-production alarms are disabled by approved policy, when the module is planned, logs, occurrence tracking, Cell-health signals, deadline state, and alert-delivery capability remain enabled. The reduced routing choice is explicit in outputs and cannot be promoted to production.

7. **Best-effort completion mode.** Given a non-production job selects best-effort completion detection during MVP, when configuration is validated, the module labels the reduced coverage and may create a bounded success-pattern metric filter and low-noise alarm tied to the job. Production policy rejects this mode because it cannot prove each expected occurrence completed.

8. **Subscription failure.** Given CloudWatch Logs cannot deliver completion evidence due to subscription errors, disabled filters, permission changes, or sustained delivery failures, a job or Cell health alarm reaches the configured operational path and affected occurrences remain eligible for `OVERDUE`, never being considered successful.

9. **Secret-safe exposure.** Given completion or alert metadata is exposed in plans, outputs, logs, or alert payloads, only non-sensitive identifiers and sanitized reasons are present. Secret values, raw CONFIG, unrestricted log text, credentials, saved-plan contents, and sensitive application data are excluded.

10. **Least-privilege integration.** Given integration permissions are analyzed, IAM-positive and IAM-negative tests prove the registered log subscription and Cell components can perform only their exact delivery, parsing, correlation, and registered-notification actions. Cross-job log delivery, forged completion, arbitrary target publication, direct occurrence writes, and role/resource-policy mutation fail.

11. **Failure-path qualification.** Given completion integration is tested, valid success, non-zero exit, missing marker, marker without zero exit, wrong occurrence, duplicate marker, delayed prior completion, subscription failure, missing target, reduced-coverage mode, and consecutive failures produce the canonical state and required test alerts within five minutes. Healthy occurrence-aware runs produce no false failure notification.

## Tasks / Subtasks

- [x] 1. Define the completion and operational metadata contract (AC: 2, 4, 6, 7, 9)
  - [x] Reuse the existing completion schema, CONFIG contract, Deployment Identity, log-ingestor normalization, Process Manager reducer, metric/alarm catalog, and Cell Contract; do not create a second completion ledger or alert route.
  - [x] Add validated inputs for detection mode, escalation classification, Runbook URI, notification policy, and explicit non-production alarm/routing state with production fail-closed validation.
  - [x] Ensure completion metadata is secret-free, bounded, versioned, and available to the existing normalizer/reducer/router without accepting raw CONFIG or unrestricted log text.

- [x] 2. Connect the job log group to the Cell completion path (AC: 1, 8, 10)
  - [x] Create the exact `aws_cloudwatch_log_subscription_filter` only when occurrence-aware completion is enabled, targeting the Cell Contract's completion destination and filter pattern.
  - [x] Preserve log retention, KMS encryption, stable resource addresses, and job ownership-generation bindings; do not let the job role write occurrence state or publish arbitrary notifications.
  - [x] Add the required Cell-side source/resource policy and subscription failure alarm only within the existing platform ownership boundary, with exact account, log-group, stream, and job bindings.
  - [x] Verify CloudWatch Logs delivery is base64/gzip decoded by the existing ingestion path and that subscription failures flow to the existing health/DLQ/reconciliation controls.

- [x] 3. Enforce completion correlation and alert enrichment (AC: 2, 3, 5, 9)
  - [x] Preserve AWS metadata as authority: map log group/stream to registered job/task and compare application assertions instead of trusting them.
  - [x] Require one accepted attempt-zero success marker plus zero essential-container exit before `SUCCEEDED`; retain duplicate/conflicting/wrong-window evidence and reduce it deterministically.
  - [x] Route occurrence failures through the existing transactional alert outbox and Alert Router, including bounded identifiers, failure plane, state, detection time, Deployment Identity, owner, and Runbook URI.
  - [x] Reject missing, malformed, cross-job, stale-generation, secret-bearing, or non-sanitized completion records with stable codes and safe evidence.

- [x] 4. Preserve policy boundaries and operational controls (AC: 4, 6, 7, 8, 10)
  - [x] Keep production completion mode, notification requirements, and alarm/routing policy fail-closed; Epic 2 remains non-production-only.
  - [x] Keep best-effort mode explicitly labeled and non-promotable; do not let a success-pattern metric or alarm declare occurrence completion.
  - [x] Expose only operational identifiers and configured metadata, with sensitivity classifications and no secrets in Terraform state, plans, outputs, logs, or alerts.
  - [x] Document subscription failure diagnosis, `OVERDUE` behavior, alert routing, disablement, rollback, log retention, and owner escalation in the existing README/runbook boundary.

- [x] 5. Add contract, IAM, Terraform, runtime, and failure-path tests (AC: 1–11)
  - [x] Add valid/invalid completion contract fixtures for occurrence-aware and best-effort modes, production rejection, missing targets, placeholder owners, Runbook validation, and secret safety.
  - [x] Add Terraform/module tests for subscription filter destination/pattern, exact log-group ownership, disabled routing behavior, alarms, outputs, stable addresses, and no direct notification/ledger writes.
  - [x] Add log-ingestor/process-manager tests for success correlation, non-zero exit, missing marker, duplicate/wrong occurrence, delayed evidence, conflicting evidence, and secret sanitization.
  - [x] Add IAM-negative tests for cross-job log delivery, forged source metadata, arbitrary SNS/SQS publication, direct occurrence writes, and role/resource-policy mutation.
  - [x] Run the pinned credential-free validation/security gate and keep live AWS delivery qualification explicit and disposable.

### Review Findings

- [x] [Review][Patch] Shared log ingestor cannot correlate non-canary jobs — broadened the read to the exact Cell-owned occurrence table while retaining read-only access and runtime source/task/occurrence authentication. [modules/ecs-scheduled-job-platform/main.tf:2555-2569]
- [x] [Review][Patch] Subscription delivery alarm observes the wrong log group — changed the Cell health metric to aggregate `AWS/Logs DeliveryErrors` across source log groups in the account/Region. [modules/ecs-scheduled-job-platform/main.tf:363-367]
- [x] [Review][Patch] Completion routing and alarm controls have no operational effect — occurrence-aware mode now fails closed unless routing and alarms are enabled, and the policy is exposed explicitly as an output. [modules/ecs-scheduled-job/variables.tf:615-635; modules/ecs-scheduled-job/outputs.tf:106-118]
- [x] [Review][Patch] Subscription destination and filter are insufficiently constrained — the filter is an exact approved pattern, the destination is contract-validated, and creation depends on declaration validation. [modules/ecs-scheduled-job/main.tf:278-286; modules/ecs-scheduled-job/completion.tf:11-18]
- [x] [Review][Patch] Operational ownership and notification metadata can diverge — Alert Router now rejects duplicate target/Runbook contradictions and materializer validation binds operational owner/target/Runbook to authoritative registration/config coordinates. [runtime/alert_router/src/alert_router/domain.py:128-152; runtime/occurrence_materializer/src/occurrence_materializer/materializer.py:150-183]
- [x] [Review][Patch] Best-effort mode has no bounded evidence path — best-effort mode now creates a bounded success-marker metric filter with job/environment/state dimensions and exposes its resource name. [modules/ecs-scheduled-job/completion.tf:21-40; modules/ecs-scheduled-job/outputs.tf:106-118]
- [x] [Review][Patch] Required completion/IAM failure-path qualification is not covered — added contract assertions for the exact subscription, policy gating, aggregate delivery metric, validation dependency, and best-effort metric path; the full contract/runtime suite passes. [tests/contract/test_scheduled_job_declaration.py:83-99]

## Dev Notes

### Existing implementation to extend

- `modules/ecs-scheduled-job/main.tf` already owns the per-job log group, explicit retention, structured runtime metadata, completion deadline, notification target/runbook inputs, and Deployment Identity. Extend these locals and CONFIG fields; do not duplicate identity or deadline derivation.
- `modules/ecs-scheduled-job/phase_one.tf` owns the job-side Scheduler/task resources and provider-backed Cell handoffs. The completion subscription must preserve phase-two activation boundaries and must not become a direct launch or occurrence-state writer.
- `modules/ecs-scheduled-job-platform/main.tf` already owns the Cell completion source queue/DLQ, log-ingestor Lambda, Alert Router, alarm catalog, KMS, queue policies, and platform-owned notification target. Use its contract outputs and resource-policy patterns.
- `runtime/evidence_normalizer`, `runtime/log_ingestor`, `runtime/process_manager`, and `runtime/alert_router` are existing ownership boundaries. Extend their contracts/reducers only where required; do not create a parallel completion processor, ledger, or notification publisher.
- `contracts/v1/schemas`, `contracts/v1/catalogs/metrics-alerts.json`, `contracts/v1/catalogs/lifecycle.json`, and `contracts/manifest.json` are normative. Any schema/catalog change requires fixtures, compatibility review, and manifest/checksum updates.

### Non-negotiable invariants

- AWS-generated CloudWatch log-group/stream and ECS task metadata are authoritative. Application IDs are assertions to compare, never authority.
- The Process Manager remains the only runtime occurrence-state writer. Job Terraform, task roles, log ingestor, and Alert Router must not write occurrence state directly.
- `SUCCEEDED` requires exactly one accepted attempt-zero completion marker correlated to the task ARN and a zero essential-container exit. Duplicate or conflicting evidence remains durable and can produce `AMBIGUOUS`.
- Occurrence IDs never appear as metric dimensions. Custom metrics use bounded job/environment/state dimensions; alert payloads may include the occurrence ID.
- Notification targets are Cell-registered and exact. The job module and job role cannot publish directly to arbitrary destinations.
- Completion, alert, and log metadata must exclude secret values, raw CONFIG, credentials, unrestricted log text, and sensitive application data.
- Production remains blocked in Epic 2. Best-effort mode and disabled alarms must be explicit non-production choices and cannot be relabeled for production.

### Terraform/AWS implementation guardrails

- Use the maintained `hashicorp/aws` `aws_cloudwatch_log_subscription_filter` resource and preserve stable names/resource addresses. CloudWatch Logs subscription payloads are base64/gzip encoded; the existing Cell ingestion path owns decoding and normalization.
- The subscription destination, role/resource policy, filter pattern, log group ARN, and ownership generation must come from the validated Cell Contract and exact registrar binding. Do not hardcode account IDs, ARNs, destinations, or job names.
- Configure subscription failure visibility through existing platform metrics, queue/DLQ, Lambda error/throttle, and log-ingestion health controls. Alarms must be actionable and linked to the configured Runbook URI.
- Follow `_bmad/custom/standards/aws-terraform-implementation.md`: least privilege, confused-deputy protections, explicit retention, encrypted queues/logs, bounded retries/age, documented rollback, and module/example validation.

### Testing and rollback

- Test both disabled and enabled occurrence-aware paths; disabled routing must retain logs, occurrence tracking, deadline state, Cell health, and alert capability.
- Failure tests must prove completion evidence is commutative under duplicates/reordering, that a marker without zero exit cannot succeed, and that missing delivery leaves occurrences eligible for `OVERDUE`.
- Rollback disables the schedule/launch first, preserves log/evidence/ledger/alert records, restores a compatible prior CONFIG/runtime/generation, revalidates, and only then re-enables. No historical evidence is deleted.

## Previous Story Intelligence

- Story 2.7 introduced the explicit phase-two activation contract and provider-backed `MATERIALIZED` acknowledgement. Preserve its exact identity, 24-hour horizon, production boundary, and disabled-first generation sequencing.
- Story 2.7 review found that caller-supplied acknowledgement fields must be bound to authoritative Cell state; do not repeat that pattern for completion or alert metadata.
- Story 2.7 used targeted contract tests plus the repository gate. The full gate requires pinned `uv` 0.11.29 and can be blocked by external package/provider DNS; report that separately from local test results.
- Earlier stories established conditional CONFIG publication, private task networking, structured logs, deterministic occurrence state, exactly-one task launch, completion reduction, deadline detection, alert outbox/routing, and Cell health alarms. Reuse those contracts rather than replacing them.

## Latest Technical Notes

- AWS CloudWatch Logs subscription filters deliver matching log events to Lambda/Kinesis/Firehose/OpenSearch and encode the delivered payload as base64 plus gzip; the Cell log-ingestor path must own decoding and source metadata handling. [Source: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/SubscriptionFilters.html]
- `PutSubscriptionFilter` supports system fields such as `@aws.account`, `@aws.region`, and `@source.log`; use only fields supported by the Cell Contract and do not treat application payload identity as authoritative. [Source: https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_PutSubscriptionFilter.html]
- Terraform's `aws_cloudwatch_log_subscription_filter` resource manages the destination ARN, log group, filter pattern, distribution, and optional role; preserve the provider lock and existing module address conventions. [Source: https://registry.terraform.io/providers/-/aws/latest/docs/resources/cloudwatch_log_subscription_filter]

## References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-2.8-Connect-Completion-Evidence-and-Alert-Metadata`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-9-Correlated-Completion-Truth`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-14-Bounded-Metrics-and-Enriched-Alerts`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-19-Cell-Health-Is-a-Production-Contract`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-27-Authenticated-Evidence-and-Command-Ingress`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-29-Publish-Validate-Materialize-Enable-Handshake`]
- [Source: `_bmad-output/implementation-artifacts/2-7-activate-the-non-production-schedule-safely.md`]
- [Source: `_bmad-output/project-context.md`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]
- [Source: `contracts/v1/catalogs/metrics-alerts.json`]
- [Source: `contracts/v1/catalogs/lifecycle.json`]
- [Source: `modules/ecs-scheduled-job/main.tf`]
- [Source: `modules/ecs-scheduled-job-platform/main.tf`]
- [Source: `runtime/evidence_normalizer`]
- [Source: `runtime/log_ingestor`]
- [Source: `runtime/process_manager`]
- [Source: `runtime/alert_router`]

## Dev Agent Record

### Agent Model Used

GPT-5

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Activation steps completed: customization resolved, project context and AWS Terraform standards loaded, and the AWS Terraform acceptance guidance was incorporated.
- Added a Cell-contract-bound occurrence-aware CloudWatch Logs subscription with exact source-account permission and gzip/base64 ingestion reuse.
- Added bounded completion policy and operational metadata to CONFIG, with non-production best-effort labeling and production fail-closed validation.
- Alert projection now uses authoritative job owner and Runbook metadata while preserving the existing outbox/ledger route.
- Updated contract schemas, manifest digests, Cell outputs, delivery health metric binding, and repository boundary tests.

### Debug Log References

### File List

- `_bmad-output/implementation-artifacts/2-8-connect-completion-evidence-and-alert-metadata.md`
- `modules/ecs-scheduled-job/completion.tf`
- `modules/ecs-scheduled-job/main.tf`
- `modules/ecs-scheduled-job/outputs.tf`
- `modules/ecs-scheduled-job/variables.tf`
- `modules/ecs-scheduled-job-platform/main.tf`
- `modules/ecs-scheduled-job-platform/outputs.tf`
- `runtime/alert_router/src/alert_router/domain.py`
- `runtime/occurrence_materializer/src/occurrence_materializer/materializer.py`
- `runtime/config_publisher/src/config_publisher/schemas/config.schema.json`
- `contracts/v1/schemas/config.schema.json`
- `contracts/manifest.json`
- `contracts/releases/1.0.0.json`
- `tests/contract/test_repository_structure.py`
- `tests/contract/test_scheduled_job_declaration.py`
- `docs/runbooks/README.md`
- `modules/ecs-scheduled-job/README.md`

### Change Log

- 2026-07-27: Created context-filled Story 2.8 for completion evidence and alert metadata integration.
- 2026-07-27: Implemented completion policy metadata, Cell-bound log subscription, alert enrichment, and contract validation updates; moved story to review.
- 2026-07-27: Applied all code-review patches; strengthened Cell correlation/IAM boundaries, delivery observability, policy gating, metadata validation, best-effort signaling, and regression coverage; marked story done.
