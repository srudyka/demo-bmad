# Pilot launch and decision runbook

This runbook governs the transition from a candidate job to a bounded pilot and
from measured evidence to a rollout decision. The credential-free evaluator
does not call AWS, change Terraform, enable schedules, or prove that a pilot
executed.

## Required artifacts

Create a versioned checklist with one or two low-risk, non-customer-facing jobs.
Assign the application owner, operational owner, repository, account, Region,
Environment, dependencies, side effects, risk class, exact Deployment Identity,
release, Compatibility Package, notification route, and observation window.
Unassigned or placeholder values keep the checklist `BLOCKED`.

The checklist must include the Story 4.3–4.8 exact-generation qualification
evidence, the Story 4.9 measurement definition/result handoff, observation
contract, qualifying-change catalog, evidence manifest, approval matrix, and
disable-first rollback criteria. Store only sanitized references and SHA-256
checksums; never publish credentials, secrets, raw CONFIG, Terraform state or
plans, unrestricted logs, or application payloads.

## Review and launch

1. Validate the checklist and every source binding with the credential-free
   runner. A fixture, aggregate workflow result, or `APPROVED_TO_START` record
   is not proof of execution.
2. Verify the exact release, module/workflow pins, target manifest, account,
   Region, Environment, job generation, Deployment Identity, Runbook, alarms,
   notification target, protected GitHub Environment, branch protection, and
   self-review prevention.
3. Obtain Platform Engineering and application-owner approvals. The versioned
   qualifying-change catalog adds Security/control-owner approval for IAM,
   trust, secrets, state, networking, or other configured qualifying classes.
4. Start only the named jobs for the named window and rollback plan. Record the
   launch authorization; do not use direct `RunTask`, caller-created Occurrence
   IDs, manual schedule/table/state edits, workload credentials, or Terraform
   state inspection.

## Observation and stop conditions

The observation contract fixes minimum duration/occurrences, schedule forms,
healthy windows, controlled failures, alert latency, false/lost-alert limits,
setup-time calculation, review categories, recovery rehearsal, and stop
conditions. A changed threshold or exclusion creates a new version and cannot
improve an observation already in progress.

Pause launches immediately for a severe incident, uncontrolled duplicate,
missing alert, security violation, or unrecoverable evidence gap. Preserve
sanitized evidence and task/occurrence/alert/side-effect inventories, follow the
job or Cell recovery Runbook, assess application compensation with the Job
Owner, and notify the declared escalation path. Restart requires failure
disposition, repeat qualification/observation where invalidated, and fresh
approvals.

## Decision and rollout

After the declared window, ingest the exact Story 4.9 result and link metrics,
limitations, exceptions, incidents, review findings, recovery results,
unresolved risks, and attestations to attributable evidence. Missing,
inconclusive, stale, contradictory, or non-comparable mandatory evidence
blocks `ACCEPTED`.

Permitted decisions are `ACCEPTED`, `REMEDIATE_AND_REPEAT`, and `REJECTED`.
Each records rationale, owners, due actions, scope, effective date, and approval
identities. Acceptance applies only to the named scope. It directs new ECS
scheduled jobs to the standard module, migrates existing jobs when materially
changed, keeps exceptions time-bound and governed, and continues adoption
metrics from the pilot baseline.

Infrastructure rollback does not reverse application effects. Roll back by
disabling launch first, retaining the known-good identity and evidence, using a
fresh protected plan, verifying scheduling/execution/logs/alerts, and recording
compensating actions separately.

## Validation

```bash
python -m scripts.run_pilot_launch \
  --checklist artifacts/checklist.json \
  --measurement artifacts/measurement-result.json \
  --artifact-root artifacts \
  --output artifacts/launch-evaluation.json \
  --report artifacts/launch-review.md
```

Run focused contract tests, the full test suite, Ruff, mypy, repository
hygiene, and `./scripts/validate.sh`. If Terraform changes are introduced,
also run format, backend-free validation for each affected root/example, and
the IaC security scan. Protected GitHub Environment settings are repository
configuration and must be verified rather than inferred from workflow YAML.
