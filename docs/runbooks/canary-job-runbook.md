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

Confirm the Cell acknowledgement matches the immutable CONFIG, Scheduler role,
and `MATERIALIZED` horizon before any activation decision. Inspect the occurrence
ledger through the approved operator role: `EXPECTED` is waiting, `STARTED` has
the correlated task ARN, `SUCCEEDED` has one accepted marker and zero
essential-container exit, `FAILED` has a sanitized failure code, `MISSED` has no start by the start
deadline, and `OVERDUE` has no accepted completion by the completion deadline.
`AMBIGUOUS` requires escalation. Late markers, duplicate task ARNs, conflicting
CONFIG, stale CONFIG, or mismatched generations remain non-authoritative and
must be reconciled without terminal overwrite.

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
