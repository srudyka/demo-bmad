# Platform Version Lifecycle Runbook

## Purpose and authority

The Cell lifecycle principal is the only automation authority allowed to
physically remove a platform version. Operators may request or approve a
cleanup through the authenticated command path, but the command handler,
runtime processors, Job-root roles, and deployment roles do not receive
destructive lifecycle permissions.

Deprecation is a separate, additive decision. A compatible release publishes a
warn-only notice with the replacement, affected consumers, migration guide,
support status, earliest removal major, owner, review date, deadline, support
contact, and rollback guidance through the GitHub release and internal
engineering channel. It does not remove behavior or compatibility. Record
acknowledgements and exceptions using sanitized identifiers only; do not place
CONFIG, plans, state, task ARNs, credentials, or raw deployment data in a
notice. Retain each publication, acknowledgement, and open-exception artifact
under contracts/retirement-evidence with its raw-byte checksum; the
lifecycle-owned evidence reader, not the submitted handoff, verifies those
immutable bytes.

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
   reference. It first persists a pending deletion intent, so a store failure
   after an external delete remains reconciliable. A partial result stops the
   run; retry only with the same manifest after the failed condition is
   resolved.
6. Verify current consumers, delayed evidence/replay, prior-major replay,
   recovery and rollback
   identities, and audit/tombstone records. Do not resume a run with a missing
   tombstone or an unresolved verification failure.

## Deprecation and retirement handoff

1. Keep the current and previous major supported through the maximum
   queue/replay/retention/investigation/recovery/rollback horizon. A notice
   deadline or release age is not evidence that retirement is safe.
2. Run the Story 3.8 consumer inventory and confirm every Cell, job,
   repository, owner/generation, CONFIG, schedule, workflow/runtime,
   queue/DLQ, occurrence/task attempt, pointer/alias, rollback identity, and
   last-observed-use record is complete. Unknown ownership, telemetry, or
   reference blocks retirement.
3. Require the complete checksum-bound cutover evidence (migration manifest,
   verified phase evidence, current acknowledgement, and plan binding), then a
   fresh passed policy decision and protected approval record. The handoff
   validates the complete records, not caller-provided booleans or a hash-shaped
   reference. A security emergency must name its risk,
   compensating control, migration path, independent approvers, and exact end
   date; it is never a permanent cleanup authorization.
4. Withdraw retired-version advertising only through the approved fresh plan:
   aliases, Cell Contract ranges/pointers, workflow manifests, documentation,
   and support metadata. Keep the artifact and known-good rollback identity
   intact until the lifecycle outcome is complete.
5. Submit the checked-in exact `retirement-handoff` through the protected
   `retire-platform-version` workflow at its full source SHA. It verifies the
   source and replacement release manifests, exact artifact checksum, all
   inventory sources and horizons, cutover completion, policy decision,
   independent platform/job-owner approval, and fresh advertisement withdrawal.
   The workflow publishes the complete validated handoff and its checksum
   envelope; it has no AWS credentials and cannot delete.
   `lifecycle-garbage-collection` alone accepts the complete handoff and
   invokes an exact deletion adapter. Raw lifecycle manifests are rejected.
6. If a recheck detects a changed alias/pointer, stale plan, late reference, or
   incompatible consumer, invalidate the manifest, retain the artifact, update
   support/notices, and fail unsupported launch closed with migration guidance.
   Generate a new inventory and handoff after resolution.

The inventory record is an immutable, checksum-bound object. Each required
source query carries an opaque query ID, query timestamp, explicit completion
flag, result count, and records list; a completed empty list is the only valid
zero-result result. It must enumerate
Cells, jobs, repositories, CONFIG, schedule generations, workflows, runtimes,
queues/DLQs, occurrence/task attempts, aliases/pointers, rollback identities,
and documentation/support records. Each observed record has an owner and
timestamp. Missing fields, unknown owners, mutable identities, future evidence,
or an incomplete horizon record fail closed.

The protected workflow installs the pinned locked Python environment before
validation and publishes the complete validated handoff plus repository/run,
environment, protected-approval, source-commit, workflow, logical-handoff,
and raw-file checksum envelope. The lifecycle principal must retrieve both
from its lifecycle-owned evidence store, verify the raw-file checksum,
protected-approval binding, notice-evidence bytes, and handoff bindings, then
perform its immediate live-reference recheck; a boolean or otherwise
incomplete recheck result is never authorization to delete. The handoff bytes
are strict UTF-8 JSON: duplicate keys, non-finite values, and parse ambiguity
are rejected before validation. A late-surface or late-reference result is
durably recorded and routed to support, communications, and unsupported-launch
handlers before the candidate is rejected.

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

After cleanup, verify the current and previous supported consumers, delayed
queue/DLQ replay, prior-major replay, rollback identities, documentation/support metadata,
monitoring, and canary operation. Persist every verification check and terminal
result; a verifier failure records `POST_DELETE_BLOCKED`. Retain the tombstone
and audit evidence so a version identity cannot be silently reused or made
historically ambiguous.

## Observability

Use bounded dimensions only: Cell, environment, artifact class, and result or
state class. The required signals are inventory completion, blocked cleanup,
manifest staleness, deletion failure, partial cleanup, late reference, and
post-deletion verification. Never emit artifact payloads, secret values,
occurrence IDs, task ARNs, or raw AWS error text as metric dimensions.
