# Job Runbook Template

## Production readiness record

Record canonical job ID, Job Owner, Platform on-call escalation, Cell ID and
Cell contract/generation, account, Region, Environment, schedule and IANA time
zone, expected runtime/deadline, overlap policy, idempotency key/locking,
dependencies, notification target, Deployment Identity location, recovery
objective/RTO, and support hours. Any unresolved owner, Cell binding,
placeholder, TODO, missing prerequisite, or unapproved external evidence blocks
production readiness.

## Evidence and occurrence states

Record structured start, success, and failure evidence with authoritative job,
occurrence, CONFIG, attempt, task, timestamp, and Deployment Identity fields.
Success requires an accepted marker and zero essential-container exit; Scheduler
delivery, logs, a marker, or an exit code alone do not prove completion. Treat
late, duplicate, and conflicting evidence as evidence for reconciliation, never
as permission to overwrite state. States are `EXPECTED`, `STARTED`,
`SUCCEEDED`, `FAILED`, `OVERDUE`, `MISSED`, and `AMBIGUOUS`.

At the start deadline, an occurrence without a correlated start is `MISSED`.
After a task starts, an occurrence without accepted completion by its completion
deadline is `OVERDUE`; preserve the task and evidence for reconciliation. Late
markers, duplicate task ARNs, and conflicting CONFIG/Deployment Identity remain
non-authoritative until the Process Manager reconciles them; escalate an
`AMBIGUOUS` result and never overwrite a terminal record.

## Alert and investigation map

Complete this mapping for every job (the canary supplies the fixture example):

| Alert plane | First query/output | Expected evidence and decision | Owner/escalation and response | Tested procedure evidence |
| --- | --- | --- | --- | --- |
| schedule-delivery | `schedule` + `operations` | delivery timestamp and `EXPECTED`; missing delivery → `MISSED` at start deadline | Job Owner; Platform on-call if deadline is reached; verify Cell acknowledgement | fixture exercise ID/date/result |
| launch | `task` + `deployment_identity` | one correlated task and compatible identity; none/duplicates → reconcile or `AMBIGUOUS` | Platform on-call; contain launch and preserve evidence | fixture exercise ID/date/result |
| runtime | `task` + `logs` | essential-container exit and sanitized failure code; non-zero → `FAILED` | Job Owner; Platform on-call for infrastructure signals | fixture exercise ID/date/result |
| completion | `logs` + `operations` | accepted marker plus zero essential exit; otherwise not complete | Job Owner; escalate conflicting evidence | fixture exercise ID/date/result |
| deadline | `operations` + occurrence record | start deadline → `MISSED`; completion deadline → `OVERDUE` | Platform on-call; reconcile late evidence | fixture exercise ID/date/result |
| log-delivery | `logs` + `alarms` | expected log stream/retention and delivery alarm; absent logs never prove success | Platform on-call; preserve task/evidence | fixture exercise ID/date/result |
| alert-routing | `alarms` + `notification` output | alarm delivered to approved route; missing notification → escalate | Platform on-call; validate route without secrets | fixture exercise ID/date/result |
| Cell-health | `config` + `operations` + Cell recovery runbook | immutable CONFIG, `MATERIALIZED` horizon, and Cell health agree; mismatch → fail closed | Platform on-call; disable launch and use Cell recovery | fixture exercise ID/date/result |

Use approved short-lived MFA operator access and the output groups above. Where
an output is not exposed by the fixture, record the approved query/runbook
reference in the job-specific row; never invent an identifier. Never use
workload roles, raw CONFIG/secret output, Terraform-state inspection, or direct
table/state mutation.

## Rerun, rollback, and recovery

Use [operator commands](operator-commands.md) for authorized non-production
reruns only. Production reruns are not an automatic path: stop, preserve
evidence, and obtain the documented Job Owner/Platform escalation decision.
For an approved non-production rerun, review the original occurrence and
Deployment Identity, assess overlap and duplicates, acknowledge compensation,
obtain independent approval, use authenticated command execution, and verify
marker plus essential-container exit. direct `RunTask`, caller-created
Occurrence IDs, schedule edits, stale CONFIG, workload roles, and automatic
cancellation are prohibited.

For rollback/forward-fix, identify the known-good compatible identity; disable
launch first; retain/quarantine evidence; use a fresh approved plan; verify
scheduling, task, logs, occurrence, deadlines, alerts, dependencies, and
compensation before resuming. Infrastructure rollback never undoes application
side effects. Use [Cell recovery](cell-recovery.md) for account/Region-local
restore; automatic cross-Region recovery is not supported.

Record a pass/fail result and evidence reference for each verification: schedule
generation, correlated task/Deployment Identity, log stream and retention,
occurrence terminal state, deadline state, alarm notification, dependency
health, and compensation owner acknowledgement. Any failed check keeps launch
disabled and escalates to Platform on-call.

## Tabletop record

Record Runbook version, reviewed source revision, non-production fixture and
generation, exercise date, non-author responder, scenario, elapsed time, missing
access, stale commands, ambiguous decisions, correction owner, pass/fail result,
and completion evidence link. Missing tabletop evidence blocks production.

## Change control

Bind this Runbook version and reviewed source revision to the proposed
generation. Broken links, secrets, unsafe commands, missing alarm mappings,
missing tabletop evidence, or unresolved readiness fields block production.
