---
baseline_commit: 197b6c2
---

# Story 2.9: Expose Job Operations and Optional Views

Status: done

## Story

As an On-call Engineer,
I want stable job outputs and an optional operational view,
So that I can locate resources and assess health without inspecting Terraform state.

## Acceptance Criteria

1. Given a scheduled job has been deployed, when module outputs are inspected, then documented outputs identify the canonical job, Cell, account, Region, Environment, ownership generation, schedule/group, task-definition revision, cluster, log group, job roles, networking, CONFIG hash/generation, acknowledgement, alarms, notification metadata, operations URI, and lifecycle state. Every output has a stable explicit type, description, sensitivity classification, and operational purpose.
2. Given Deployment Identity is requested, when the module constructs it, then it includes image digest, task-definition revision, source revision input, module version, workflow identity when supplied, CONFIG hash, schedule generation, target account/Region/Environment, Cell version, and deployment run reference when available. The same non-sensitive identity is available to task tags, occurrence records, alerts, verification, and rollback evidence.
3. Given an operator uses the outputs, when they follow documented console or CLI references, then they can locate the schedule, current task revision, ECS tasks/events, log group, occurrence state, alarms, notification route, CONFIG acknowledgement, and Cell health. The procedure uses supported operator access and never requires platform or consumer Terraform-state inspection.
4. Given outputs appear in a plan, apply log, automation artifact, or documentation generator, when data-safety checks run, then no secret value, secret payload, raw CONFIG body, binary plan content, unrestricted log text, credential, or sensitive application data is exposed. Secret-reference identifiers are omitted unless their non-sensitive operational use is explicitly documented.
5. Given a consumer enables the optional CloudWatch dashboard, when Terraform creates it, then the view separates Scheduler delivery, ECS launch and runtime outcomes, occurrence completion states, deadline failures, log-delivery health, alert delivery, and linked Cell health. It uses only bounded metrics and approved log queries without occurrence ID, task ARN, error text, or log stream as metric dimensions.
6. Given dashboard cost and scale guardrails are evaluated, when the dashboard is planned, then widget count, metric/query count, time range, refresh assumptions, log-query use, and expected cost remain within documented configurable limits. Invalid unbounded dimensions or unsupported query patterns fail validation.
7. Given a consumer omits or disables the dashboard, when Terraform is applied, then logs, occurrence tracking, deadlines, required alarms, notification routing, and Cell-health collection remain unchanged. No required monitoring or alert action depends on dashboard existence.
8. Given output or dashboard contracts evolve, when compatibility checks run, then snapshots verify output names/types, resource identities, Deployment Identity, lifecycle state, redaction, bounded dimensions, dashboard-enabled behavior, and dashboard-disabled behavior. Breaking output changes require a major release and migration note rather than silent replacement.
9. Given a dashboard change must be rolled back, when the prior compatible view is restored or the dashboard is disabled, then required operational signals and evidence remain intact. Rollback does not alter the job schedule, task revision, CONFIG, occurrence state, or alarms.

## Tasks / Subtasks

- [x] Define and document a stable, explicitly typed output contract in `modules/ecs-scheduled-job/outputs.tf` (AC: 1, 4, 8)
  - [x] Group outputs into canonical identity, Cell contract, schedule, task, logs, CONFIG/acknowledgement, operations/notification, alarms, networking, lifecycle, and optional dashboard objects.
  - [x] Give every output an explicit Terraform type, description, sensitivity decision, and operational purpose; avoid inferred maps and unstable implementation-only fields.
  - [x] Expose resource identifiers owned by this module and validated Cell-contract references without introducing remote-state reads or direct Cell data-store access.
  - [x] Ensure secret payloads, raw CONFIG, validation evidence, binary plans, log contents, credentials, and sensitive application data are never returned. Expose only a safe hash or bounded reference where an operator needs correlation.
  - [x] Include schedule ARN/group, target queue/DLQ, retry and age settings, task-definition family/revision, cluster, log group/subscription, role identifiers, networking identifiers, CONFIG version/hash/key, owner generation, acknowledgement state, notification metadata, operations/runbook URI, and alarm ownership/reference.

- [x] Complete the canonical Deployment Identity and lifecycle contract (AC: 1, 2, 3, 4, 8)
  - [x] Extend bounded optional inputs for workflow identity and deployment run reference; reject newlines, raw JSON/plans, secret-like values, and values exceeding documented limits.
  - [x] Include image digest, task-definition family/revision, source revision, module version, platform/Cell version, CONFIG hash, schedule generation, account, Region, Environment, job ID, and optional workflow/run references in one deterministic identity.
  - [x] Propagate the same non-sensitive identity to task tags, CONFIG metadata, occurrence/completion records, alert metadata, verification evidence, and rollback evidence; do not create parallel identity formats.
  - [x] Distinguish declared/requested lifecycle from authoritative CONFIG acknowledgement and schedule state. Do not label a schedule as enabled merely because an input requests activation.
  - [x] Expose the source of each lifecycle assertion and preserve the `VALIDATED`/`MATERIALIZED` acknowledgement semantics already established by the Cell contract.

- [x] Add the optional per-job CloudWatch dashboard owned by the job module (AC: 5, 6, 7, 9)
  - [x] Add an explicit dashboard configuration object with safe defaults and bounded validation for enabled state, time range, refresh interval, widget count, metric count, query count, log-query use, and documented cost budget.
  - [x] Generate a fixed dashboard body; do not accept arbitrary widget JSON, metric namespaces, dimensions, expressions, log groups, or query text from consumers.
  - [x] Provide separate bounded widgets for Scheduler delivery/DLQ, ECS launch/runtime, occurrence terminal states, deadline failures, log-delivery health, alert delivery, and linked Cell health, plus a scope/runbook text widget.
  - [x] Allow only approved dimensions such as `job_id`, `environment`, `state`, `cell_id`, and `component`. Reject `occurrence_id`, task ARN, log stream, error text, source/target ARN, credential, and other unbounded or high-cardinality dimensions.
  - [x] Use only approved metrics and, if a Logs Insights widget is supported, a fixed safe query with bounded time/results and projected fields. Do not use unrestricted log text, `SEARCH`, arbitrary Metrics Insights, or wildcard cross-account/cross-job queries.
  - [x] Treat Story 2.8 `DeliveryErrors` carefully: use an authoritative source-log-group dimension or a validated bounded Cell aggregate; do not assume an empty-dimension metric is an aggregate without a live contract/test proving it.
  - [x] Expose dashboard enabled/name/ARN/body checksum/widget and query counts, or an explicit disabled/null shape. Dashboard failure must not suppress or mutate required alarms, routing, logs, deadlines, tracking, or Cell health.
  - [x] Keep dashboard permissions in the Terraform deployment path; do not add CloudWatch dashboard mutation, Cell data-store, or notification-publication permissions to workload roles.

- [x] Provide supported operator references and example outputs (AC: 1, 3, 4, 7, 9)
  - [x] Update `modules/ecs-scheduled-job/README.md` and the relevant runbook/example to show how output values locate Scheduler, ECS, CloudWatch Logs, alarms, notification route, CONFIG acknowledgement, occurrence state, and Cell health.
  - [x] Use supported AWS console/CLI procedures and approved short-lived, CloudTrail-attributed operator access; never instruct operators to inspect platform or consumer Terraform state or use workload roles.
  - [x] Document redaction rules, the difference between desired and acknowledged state, dashboard limitations, estimated cost assumptions, and dashboard disable/restore rollback.
  - [x] Keep examples free of real account IDs, credentials, secret values, raw CONFIG, unrestricted log output, and sensitive application data.

- [x] Add contract, security, and compatibility tests (AC: 1-9)
  - [x] Add output snapshots/contract tests for names, explicit types, descriptions, sensitivity, operational purpose, resource identity, Deployment Identity, CONFIG acknowledgement, lifecycle source, and redaction.
  - [x] Test identity determinism, optional workflow/run fields, image digest and revision propagation, stale/missing/cross-Cell acknowledgement, and mismatch between output resources and the validated Cell contract.
  - [x] Test dashboard enabled, disabled, repeated, empty-data, one-job, and many-job cases; validate widget/metric/query/time/refresh/cost limits and forbidden dimensions/query patterns.
  - [x] Test that dashboard omission or failure leaves alarms, notification routing, logs, deadlines, occurrence tracking, and Cell health unchanged.
  - [x] Add IAM-negative checks proving workload roles cannot mutate dashboards, publish arbitrary notifications, read Cell stores, or access secrets beyond their existing references.
  - [x] Add compatibility fixtures for a breaking output/dashboard change and require a major-release/migration-note signal.

## Dev Notes

### Existing implementation to extend

Story 2.8 is the baseline for this work (`197b6c2`). The job module currently exposes separate `job_id`, `cell`, `reservation`, `protected_tags`, `normalized_schedule`, `job_iam`, `networking`, `task_definition`, `log_group`, `completion_policy`, `deployment_identity`, `phase_one`, and `phase_two` outputs. Several are inferred maps, and `phase_two.lifecycle`/`schedule_state` are largely derived from activation inputs rather than an observed acknowledgement. Preserve existing consumers through additive, compatibility-conscious changes and make any rename/removal a major-release change with a migration note.

The current Deployment Identity contains source revision, module version, image, account, Region, Environment, job ID, and platform version. Add workflow/run references only as bounded non-sensitive values and include the final task-definition revision, CONFIG hash, schedule generation, Cell contract version/checksum, and image digest. Reuse this identity everywhere; do not introduce a second correlation ID.

The Cell platform already exposes contract-derived references for scheduler ingress, occurrence ledger, deadline scanner, alert router, log ingestor, and Cell health. The job module must consume the validated Cell Contract and expose safe references; it must not read platform Terraform state or directly access Cell registries, ledgers, queues, or notification stores.

### Output contract guidance

Use stable objects with explicit schemas rather than broad `map(string)` values. A reasonable shape is:

- `job_identity`: job ID, application, environment, account, Region, Cell ID, owner, owner generation, Cell contract version/checksum, module/platform version, and lifecycle.
- `schedule`: expression, timezone, activation window, flexible window, generation, schedule ARN/group, target queue/DLQ, retry/max-age policy, scheduler role ID, and declared/acknowledged state.
- `task`: task-definition ARN/family/revision, image digest, cluster ARN, execution/task role IDs, runtime platform, and network mode.
- `logs`: log group name/ARN, retention/KMS metadata, subscription destination/filter/protocol, and delivery-health reference; never log text.
- `config`: version/hash, object key only when safe and operationally needed, contract version/checksum, owner generation, acknowledgement lifecycle/result, and a safe evidence reference/hash.
- `operations`: owner, runbook/operations URI, approved notification target reference, escalation class, route/coverage metadata, and supported operator access profile.
- `alarms`: job-owned alarm references and Cell-health/alert-router references with explicit ownership. Do not fabricate ARNs or duplicate Cell alarms merely to populate the output.
- `dashboard`: enabled, stable name/ARN, body checksum, bounded widget/metric/query counts, and disabled/null semantics.

Mark secret-bearing or sensitive values sensitive, but do not rely on Terraform sensitivity alone: plan and apply logs, generated docs, snapshots, and automation artifacts must also be safe. A secret reference is not automatically safe; omit it unless the contract documents its non-sensitive purpose.

### Dashboard guardrails

The dashboard is an optional job-root resource, consistent with the single-Terraform-owner rule. It is not a replacement for alarms or the Cell operational view. Use a stable generated name and body checksum. Suggested initial defaults are no more than 8 widgets, 40 metrics, 2 log queries, a 24-hour time range, and a 300-second refresh, with hard upper bounds documented in variables and tests. Adjust only when the implementation can prove the resulting body remains bounded and cost assumptions are explicit.

The generated body should contain a text scope/caveat/runbook widget and fixed widgets for each required health plane. Prefer named metric references and explicit dimensions. If the current metric catalog cannot support a safe log query, omit the query widget and provide a bounded log-group navigation reference rather than exposing arbitrary logs. Dashboard data may be absent for a newly deployed job; this must not make Terraform validation or required alerting depend on historical data.

### Ownership and security

The job root owns its schedule, task definition, roles, log group/subscription, job alarms, and optional dashboard. The Cell owns shared queues, ledgers, processors, alert routing, metric namespace, and Cell-health contract. Notification targets must be approved/Cell-registered; the module must not publish directly to arbitrary SNS/SQS/HTTP destinations. Workload IAM roles must not gain dashboard mutation or Cell datastore permissions.

### Testing and validation

Add runtime/contract/IAM tests rather than relying only on source-text assertions. Exercise valid and invalid output contracts, stale or mismatched acknowledgements, forbidden dashboard dimensions, unsupported query forms, disabled-dashboard preservation, and resource-reference mismatches. Run the repository validation script with the pinned `uv` version (`0.11.29`) where available. Terraform changes require `terraform fmt -check` and `terraform validate`; the custom Cell provider may require the repository's documented cache/bootstrap procedure in CI.

### Rollback

Rollback is limited to restoring the previous dashboard body or setting the dashboard option to disabled. It must preserve schedule/task/CONFIG/occurrence/alarms/logs/DLQs/notification routing/Cell health. If an output contract change is breaking, release the major version and publish the migration note before consumers upgrade.

### References

- Epic requirements: `_bmad-output/planning-artifacts/epics.md`, Story 2.9.
- Project rules: `_bmad-output/project-context.md`.
- AWS Terraform standards: `_bmad/custom/standards/aws-terraform-implementation.md`.
- Architecture spine: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md` (especially AD-14, AD-15, AD-18, AD-19, AD-20, AD-22, AD-25).
- Previous implementation: `_bmad-output/implementation-artifacts/2-8-connect-completion-evidence-and-alert-metadata.md`.
- [AWS CloudWatch dashboard widgets](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/create-and-work-with-widgets.html).
- [AWS CloudWatch service quotas](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_limits.html).
- [AWS PutDashboard API](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutDashboard.html).
- [AWS CloudWatch dashboard body structure](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Dashboard-Body-Structure.html).
- [Terraform AWS `cloudwatch_dashboard` resource](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_dashboard).

## Previous Story Intelligence

Story 2.8 added occurrence-aware completion evidence, a log subscription to the Cell log ingestor, completion policy validation, CONFIG completion metadata, and completion-policy outputs. Carry forward these constraints:

- Normal-job log-ingestor permissions and subscription behavior must be tested; canary-only coverage is insufficient.
- Completion and alert metadata must be behaviorally authoritative, not merely copied from serialized policy text.
- Notification targets must be exact approved/Cell-registered destinations.
- Delivery-error metrics must be verified against the actual CloudWatch dimension contract before being placed on a dashboard.
- Custom Cell provider behavior may not be fully available from a local provider cache; record CI/bootstrap limitations rather than weakening checksum or provider validation.

## Git Intelligence

Recent work completed Stories 2.7 and 2.8 in small commits. The story baseline is `197b6c2`, the Story 2.8 completion commit. Preserve the clean baseline and keep this story's implementation focused on the output/dashboard contract; do not fold Story 2.10's controlled rerun behavior into this work.

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

- Focused RED/GREEN tests: `tests/contract/test_scheduled_job_operations.py` (initially failed before implementation; passed after implementation).
- Terraform module validation through repository provider-development override: module validation is intentionally skipped because the module has aliased Cell providers; the basic example validated successfully.
- Direct local module validation without the repository override was blocked because `demo-bmad/cell` is not published/cached in the local registry.
- Full repository validation passed with the pinned toolchain: Terraform/provider-aware validation, formatting, lint, type checks, 240 tests, Checkov, and repository hygiene.

### Completion Notes List

- Added typed operational output groups for identity, schedule, task, logs, CONFIG acknowledgement, operations, alarms, and dashboard metadata.
- Added bounded workflow/deployment run references and propagated the canonical Deployment Identity into CONFIG, outputs, alerts/evidence metadata, and runtime metadata; ECS pre-create tags retain the documented seed because the provider assigns the final revision after resource creation.
- Replaced raw phase-two validation evidence output with a correlation hash.
- Added an optional fixed eight-widget CloudWatch dashboard with bounded dimensions, time range/refresh/cost limits, and disabled-dashboard isolation.
- Updated operator documentation with supported AWS CLI references, redaction guidance, lifecycle semantics, and rollback.
- Added contract tests and updated resource-boundary tests for the job-owned dashboard.

### File List

- `_bmad-output/implementation-artifacts/2-9-expose-job-operations-and-optional-views.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `modules/ecs-scheduled-job/README.md`
- `modules/ecs-scheduled-job/dashboard.tf`
- `modules/ecs-scheduled-job/main.tf`
- `modules/ecs-scheduled-job/outputs.tf`
- `modules/ecs-scheduled-job/task.tf`
- `modules/ecs-scheduled-job/variables.tf`
- `tests/contract/test_repository_structure.py`
- `tests/contract/test_scheduled_job_operations.py`
- `tests/contract/test_scheduled_job_task.py`

### Change Log

- 2026-07-27: Implemented Story 2.9 operational outputs, Deployment Identity hardening, optional dashboard, operator documentation, and contract coverage.
- 2026-07-27: Applied all 13 review patches; added authoritative dashboard/notification contract checks, compatibility-preserving evidence hashing, disabled-dashboard semantics, fail-closed integration availability, and release metadata updates.

### Review Findings

- [x] [Review][Patch] Preserve the compatible `phase_two.validation_evidence` output shape with a safe hash value.
- [x] [Review][Patch] Establish and consume authoritative dashboard and notification contracts.
- [x] [Review][Patch] Make Deployment Identity canonical, including the CONFIG hash, schedule generation, task revision, and Cell contract identity; document the unavoidable pre-create ECS tag seed.
- [x] [Review][Patch] Stop legacy lifecycle outputs from claiming authorization from input alone.
- [x] [Review][Patch] Replace invented dashboard metrics with catalog-approved metric/dimension tuples.
- [x] [Review][Patch] Remove the dead `include_log_query` option.
- [x] [Review][Patch] Make disabled dashboard metadata consistently disabled.
- [x] [Review][Patch] Fail closed for missing operational integrations.
- [x] [Review][Patch] Type and classify all exposed outputs.
- [x] [Review][Patch] Complete operator navigation references.
- [x] [Review][Patch] Remove contradictory dashboard documentation.
- [x] [Review][Patch] Replace source-text tests with contract and behavior-oriented coverage.
- [x] [Review][Patch] Derive dashboard cost metadata from bounded shape.
