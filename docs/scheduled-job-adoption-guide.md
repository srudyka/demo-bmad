# Scheduled Job Adoption Guide

The supported control path is **Scheduler → Cell → ECS**. Scheduler must never target ECS directly: the Cell determines whether a validated occurrence may launch.

## Adoption path

1. **Prerequisites:** Terraform `>= 1.10, < 2.0` (tested seed 1.15.8), AWS provider 6.54.0, Python 3.14.6, an immutable image digest, and the existing Cell Contract. Examples are backend-free and contain no `tfvars`, credentials, or production identifiers.
2. **Discover the Cell** through its contract; never use `terraform_remote_state` or inspect another root’s state.
3. **Reserve the job** through the approved platform Registrar integration and
   supply its authoritative receipt to the job module. There is no consumer
   general-Registrar API: never create a receipt, edit Cell state, or infer a
   reservation from Terraform state.
4. **Prepare IAM/networking:** separate Process Manager, Scheduler, execution, and task roles; review effective policy, exact `PassRole`, confused-deputy source conditions, secret mode, private subnet evidence, and bounded egress.
5. **Integrate the task** with retained structured logs and an immutable image. The application consumes platform-supplied job, Occurrence ID, CONFIG version, attempt, task, and Deployment Identity; it never generates occurrence IDs.
6. **Publish phase one**, obtain an exact accepted Cell acknowledgement, and
   confirm the required future horizon is `MATERIALIZED`. A missing, rejected,
   stale, or mismatched acknowledgement blocks activation. Only then make the
   separate two-phase non-production activation decision.
7. **Verify and hand off** using outputs, alarms, and [runbooks](runbooks/README.md). direct `RunTask`, direct table/state edits, out-of-Terraform schedule mutation, and automatic cancellation are prohibited.
8. **Promote** only through protected OIDC Environments and isolated state with exact-plan, readiness, owner, notification, and approval evidence. Unresolved launch-checklist values fail closed.

## Completion records

```json
{"event":"start","job_id":"<platform-supplied>","occurrence_id":"<platform-supplied>","config_version":"<platform-supplied>","attempt_no":0,"task_arn":"<platform-supplied>","deployment_identity":"<platform-supplied>","timestamp":"2026-07-31T00:00:00Z","status":"started"}
{"event":"success","job_id":"<platform-supplied>","occurrence_id":"<platform-supplied>","config_version":"<platform-supplied>","attempt_no":0,"task_arn":"<platform-supplied>","deployment_identity":"<platform-supplied>","timestamp":"2026-07-31T00:01:00Z","status":"succeeded","exit_code":0}
{"event":"failure","job_id":"<platform-supplied>","occurrence_id":"<platform-supplied>","config_version":"<platform-supplied>","attempt_no":0,"task_arn":"<platform-supplied>","deployment_identity":"<platform-supplied>","timestamp":"2026-07-31T00:01:00Z","status":"failed","exit_code":1,"error_reason":"sanitized_failure_code"}
```

Emit start, success, and failure records with only sanitized errors. Success requires an accepted Cell marker plus zero essential-container exit; a marker alone is not completion. Jobs are idempotent; overlap and deadlines are governed, reruns require approval and compensation, and evidence is retained.

## Change and recovery

Classify schedule, image, IAM, network, secret, module-version, and address changes. Preserve stable addresses or use reviewed `moved` blocks; record plan impact, Deployment Identity, verification, and rollback. Rollback disables launch first, preserves references/evidence, restores a compatible generation through the protected workflow, and uses application compensation. Never move references, destructively replace resources, or clean up evidence during rollback. See [operator commands](runbooks/operator-commands.md), [Cell recovery](runbooks/cell-recovery.md), the [job Runbook template](runbooks/job-runbook-template.md), and the [canary Runbook](runbooks/canary-job-runbook.md).

## Production reference — non-deployable

This reference is intentionally launch-blocked; it is not a deployable root.

```hcl
production_launch_checklist = {
  private_network_evidence = "<externally-approved-evidence>"
  immutable_image          = "<digest-only-image-reference>"
  completion_routing       = "<occurrence-aware-cell-route>"
  notification_route       = "<approved-notification-route>"
  required_alarm_evidence  = "<approved-alarm-evidence>"
  runbook_and_readiness    = "<approved-runbook-and-readiness>"
  protected_workflow       = "<protected-oidc-environment>"
  isolated_state           = "<approved-state-boundary>"
  phase_two_acknowledgement = "<exact-materialized-acknowledgement>"
}
# Any unresolved value blocks launch; do not substitute a real identifier here.
```

Production requires every checklist field, private networking, immutable image,
occurrence-aware completion, notification routing, required alarms, Runbook and
readiness references, protected workflow, isolated state, and exact two-phase
activation evidence. Terraform's permanent compatibility constraint is `>=
1.10, < 2.0`; dated tested seeds are Terraform 1.15.8, AWS provider 6.54.0,
Python 3.14.6, and the repository's pinned Fargate platform/runtime values.
Select only a mutually supported Cell Contract major, scheduled-job module
version, contract package, and protected workflow version.

Documentation CI checks local links, formatting, generated references, contract
versions, Terraform examples, immutable pins, prohibited artifacts, security
assertions, and secret safety; stale or insecure guidance blocks release.
