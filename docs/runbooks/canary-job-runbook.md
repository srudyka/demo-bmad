# Platform Canary Job Runbook

This is the completed non-production reference for the disabled platform canary.
Use `terraform output canary` from `fixtures/canary` with approved operator role
access. The secret-free object exposes these keys; record values only in the
approved incident system, never in this Runbook:

| Output key | Safe use / handoff |
| --- | --- |
| `job_id`, `config_hash`, `config_lifecycle` | `job_identity`/`config`; require `PUBLISHED` and immutable hash |
| `schedule_arn`, `schedule_generation` | `schedule`; compare generation with Cell acknowledgement |
| `task_definition_arn`, `task_revision` | `task`/`deployment_identity`; verify compatible revision |
| `log_group_name` | `logs`; verify stream and retention |
| `notification_sink_arn` | `alarms`; verify approved notification route |
| `scheduler_dlq_arn`, `scheduler_source_queue_arn` | `operations`; inspect delivery evidence through approved access |
| `scheduler_delivery_role_id` and `roles.*` IDs/ARNs | `deployment_identity`; verify role identity, never assume workload roles |
| `ownership_generation` | `operations`; compare with Cell ownership record |

The fixture does not expose `alarms` or full Cell-health operations as output
values; use the approved operator and Cell recovery procedures for those rows.
Do not copy account identifiers, ARNs, CONFIG contents, or credentials into this file.

## Investigation

## Schedule qualification evidence

Schedule qualification is performed only in the disposable non-production Cell
through the standard workflow. Record the release and Compatibility Package,
Cell/account/Region, schedule generation, policy versions, test clock, and
checksum-bound evidence manifest. Materialize the expectation horizon before
enabling Scheduler delivery, then exercise malformed/DST/anchor/generation,
delivery retry/DLQ, duplicate delivery, deadline, and twenty-window healthy
cases. A passing schedule result does not satisfy launch, completion, security,
or recovery readiness categories. Retain only sanitized evidence and delete
disposable schedules, tasks, roles, logs, and expectations unless an explicit
retention decision is recorded.

Confirm the Cell acknowledgement matches the immutable CONFIG, Scheduler role,
and `MATERIALIZED` horizon before any activation decision. Inspect the occurrence
ledger through the approved operator role: `EXPECTED` is waiting, `STARTED` has
the correlated task ARN, `SUCCEEDED` has one accepted marker and zero
essential-container exit, `FAILED` has a sanitized failure code, `MISSED` has no start by the start
deadline, and `OVERDUE` has no accepted completion by the completion deadline.
`AMBIGUOUS` requires escalation. Late markers, duplicate task ARNs, conflicting
CONFIG, stale CONFIG, or mismatched generations remain non-authoritative and
must be reconciled without terminal overwrite.

## ECS launch and runtime qualification

Run ECS qualification only after schedule qualification passes, using the same
release candidate and an isolated disposable non-production Cell. The protected
workflow is `.github/workflows/ecs-launch-runtime-qualification.yml`; it accepts
sanitized evidence, configuration, and trusted binding artifacts and publishes
only a checksum-bound manifest. The credential-free contract runner is:

```text
python scripts/run_ecs_qualification.py \
  --evidence <sanitized-evidence.json> \
  --configuration <pinned-configuration.json> \
  --bindings <trusted-bindings.json> \
  --output <launch-runtime-manifest.json>
```

Qualify API failure or `RunTask` `failures[]`, response-loss reconciliation,
task-start failures, non-zero or externally stopped tasks, over-runtime
detection, duplicate/foreign evidence, alert timing, and twenty healthy
launch/runtime cases. A zero exit records runtime evidence but does not satisfy
completion without the separate occurrence-bound marker. Inspect task ARN,
`stopCode`, sanitized reason/error code, timestamps, task tags, owner, failure
plane, and Cell/job routing; never copy secrets or brittle free-form error text
into evidence.

On abort, disable launch first, remove injected faults and disposable resources,
and retain only the sanitized immutable evidence explicitly listed in the
manifest. An unresolved launch response or conflicting task identity is
`AMBIGUOUS` and must not be retried blindly. The qualification manifest may mark
only launch/runtime, reconciliation, timing, and healthy-run controls passed;
completion, security, and recovery remain blocked until their dedicated
qualification stories pass.

## Completion, deadline, and alert qualification

Run `.github/workflows/completion-deadline-alert-qualification.yml` only after
launch/runtime qualification, using the same immutable release candidate and a
disposable non-production Cell. Supply the completed protected workflow run ID
and artifact names containing exactly `evidence.json`, `configuration.json`,
and `bindings.json`; the workflow downloads those artifacts and verifies the
signed evidence before projection. The credential-free projection is:

```text
python scripts/run_completion_deadline_qualification.py \
  --evidence <sanitized-evidence.json> \
  --configuration <pinned-configuration.json> \
  --bindings <trusted-bindings.json> \
  --output <completion-deadline-manifest.json>
```

Verify that accepted completion evidence has the authenticated source context,
registered occurrence/task/configuration identity, success marker, and zero
essential-container exit. Verify `MISSED` versus `OVERDUE`, duplicate/replay
idempotency, late-evidence terminal-state preservation, partial-batch retry or
quarantine, transactional alert outbox obligations, notification-ledger
deduplication, and the independent alert-pipeline health check. Keep metric
dimensions bounded and retain only sanitized evidence.

On completion or abort, disable the qualification path first, remove injected
faults, delete disposable schedules/tasks/roles/logs/expectations/resources,
and verify the cleanup inventory. Cleanup failure is fail-closed and must not
publish readiness evidence. Rollback is the disable-first path followed by the
approved Cell recovery procedure; security and recovery readiness remain
blocked until their dedicated qualifications pass.

## Response

For a failure, classify the eight alert planes using the mapping in the [job
Runbook template](job-runbook-template.md), then record the output key, evidence,
decision, owner/escalation, response, and fixture exercise result. Preserve
evidence, disable launch when containment is required, and use the approved
rerun/recovery path. Reruns require the canonical occurrence selector, Job Owner
and independent Platform approval, compensation acknowledgement, fresh CONFIG,
and marker-plus-zero-essential-exit verification. Never use direct ECS launch,
caller occurrence IDs, schedule edits, workload roles, or edit Cell state.

The canary remains disabled and non-production. A tabletop record must include
Runbook version, source revision, fixture generation, exercise date, pass/fail,
and evidence link before any proposal to enable it.

## Security and delivery-boundary qualification

Run `.github/workflows/security-boundary-qualification.yml` only from the
immutable release candidate after the protected qualification workflow has
published `evidence.json` and `bindings.json`. The workflow requires the exact
source commit and run ID, downloads artifacts into an isolated temporary root,
and projects only sanitized Story 4.7 security controls:

```text
python scripts/run_security_qualification.py \
  --evidence <sanitized-evidence.json> \
  --bindings <trusted-bindings.json> \
  --artifact-root <isolated-artifact-root> \
  --output <security-manifest.json>
```

Interpret every fixture as a preventive authorization result. Forged producers,
cross-job or stale-generation evidence, namespace squatting, broad IAM actions,
alternate `RunTask`/`PassRole` paths, unapproved OIDC claims, state/plan
substitution, public networking, plaintext secrets, and under-scoped operator
commands must be denied before mutation. Each paired compliant fixture must use
the exact registered identity and scope. Offline IAM analysis is supporting
evidence only; an inconclusive simulation or detective alarm does not pass a
boundary.

Investigate failures using the fixture ID, stable denial code, preventive
boundary, policy/catalog version, source/workflow/run binding, and checksum.
Do not copy raw payloads, state, plans, logs, credentials, tokens, secret
values, or production identifiers into tickets or retained artifacts. Escalate
ownership, OIDC, state, and operator failures to the Platform and Security
reviewers; keep recovery blocked until the separate recovery story passes.

Rollback is disable-first: stop qualification launch, remove injected faults,
delete synthetic jobs, identities, policies, queues, state/plan artifacts,
logs, and disposable Cell resources, then verify deleted and retained
inventories plus forbidden-artifact checks. Retain only the checksum-bound
sanitized manifest. Any cleanup or sanitization failure blocks publication.
