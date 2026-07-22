# Platform Version Lifecycle Runbook

## Purpose and authority

The Cell lifecycle principal is the only automation authority allowed to
physically remove a platform version. Operators may request or approve a
cleanup through the authenticated command path, but the command handler,
runtime processors, Job-root roles, and deployment roles do not receive
destructive lifecycle permissions.

Cleanup is fail-closed. An unknown owner, incomplete inventory, active alias or
pointer, queued or DLQ evidence, active task or occurrence, recovery generation,
audit requirement, or unexpired replay/investigation/rollback horizon blocks
the candidate.

## Procedure

1. Run inventory in dry-run mode for one Cell and record the exact artifact
   identity, checksum, owner, references, and maximum applicable horizon.
2. Review the generated retirement manifest. It must contain exact resource and
   version identifiers, the inventory checksum, preservation requirements,
   rollback limitations, owner, approval, and an expiry time.
3. Confirm the Cell Contract, Lambda aliases, recovery pointer, active and
   previous supported major, queues/DLQs, occurrences, task mappings, outbox,
   notification ledger, audit evidence, and deployment identities still match
   the manifest. Any change invalidates the manifest.
4. Approve the exact manifest through the protected workflow. Do not approve a
   wildcard, tag-only selection, mutable alias, or age-only cleanup.
5. Execute one bounded batch. The lifecycle controller revalidates immediately
   before each deletion and records every success, skip, failure, and late
   reference. A partial result stops the run; retry only with the same manifest
   after the failed condition is resolved.
6. Verify current consumers, delayed evidence/replay, recovery and rollback
   identities, and audit/tombstone records. Do not resume a run with a missing
   tombstone or an unresolved verification failure.

## AWS-specific cautions

- For versioned S3 objects, permanently deleting a version requires its exact
  `versionId`; a simple delete creates a delete marker. Preserve current,
  audit, recovery, and replay-required versions.
- Lambda aliases point to published versions. Recheck all aliases before
  deleting a published version and retain the current and previous supported
  major.
- ECS task-definition revisions are exact family/revision identities. A
  deregistered revision's historical task and occurrence evidence is still
  retained until its horizons expire.
- Do not delete a shared SSM Cell Contract or recovery parameter. Deleting a
  parameter removes all versions and cannot be restored.

## Blocked and failed cleanup

For `LIFECYCLE_*` denial codes, retain the candidate and attach the sanitized
code to the lifecycle audit record. For a late reference, changed checksum,
throttle, authorization failure, or adapter error, disable further cleanup,
page the Platform owner, and generate a new inventory after the issue is
resolved. There is no rollback for a successfully permanently deleted AWS
version; rollback uses a retained compatible artifact and a new deployment
identity.

## Observability

Use bounded dimensions only: Cell, environment, artifact class, and result or
state class. The required signals are inventory completion, blocked cleanup,
manifest staleness, deletion failure, partial cleanup, late reference, and
post-deletion verification. Never emit artifact payloads, secret values,
occurrence IDs, task ARNs, or raw AWS error text as metric dimensions.
