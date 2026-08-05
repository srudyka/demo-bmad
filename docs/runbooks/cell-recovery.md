# Cell Recovery Runbook

## Scope and authority

Cell recovery is an account/Region-local, approved operation for the Cell
recovery role. The operator submits an authenticated `RECOVER` command with an
independent approval, reason, restore point, expected RPO, and expected RTO.
Acceptance of the command records evidence; it does not mean that restore,
cutover, replay, or verification completed.

Do not use workload roles, direct DynamoDB writes, direct ECS launch, or manual
queue identity changes. Automatic cross-Region failover is not supported.

## Recovery order

1. Confirm the Cell, account, Region, current Deployment Identity, incident,
   approval, source-version compatibility, and PITR availability for every
   source table. Choose one restore point available to all tables.
2. Submit the command through the operator role. Confirm the recovery manifest
   records the actor, session, approval, reason, generation, restore point,
   expected RPO/RTO, and source identity.
3. Confirm launch is disabled before any table or pointer changes. Confirm
   schedules and affected event-source mappings are paused. Do not delete or
   drain evidence irreversibly.
4. Restore namespace, CONFIG, occurrence/checkpoint, outbox, and notification
   tables to new encrypted tables. Apply tags, PITR, deletion protection,
   streams, TTL, and the expected indexes before access is granted.
5. Review the integrity digest. It must cover keys, indexes, CONFIG hashes,
   ownership generations, task mappings, processed-event deduplication,
   deadlines, outbox references, notification identities, and Deployment
   Identity.
6. Cut over the single recovery-generation pointer. A mixed source/recovery
   generation is a blocking failure.
7. Replay retained evidence through the normalizer and Process Manager. An
   unresolved launch beyond its safe retry deadline must become `AMBIGUOUS`,
   never a new `RunTask` call.
8. Rebuild expectations, reconcile nonterminal occurrences and pending
   notifications, then run the canary and pre-resume verification. Keep launch
   disabled until every blocking check and approval succeeds.

## Rehearsal evidence

Run the credential-free evaluator against a controlled artifact root containing
only sanitized evidence and binding files:

```bash
python scripts/run_recovery_qualification.py \
  --evidence /path/to/recovery-evidence.json \
  --bindings /path/to/recovery-bindings.json \
  --artifact-root /path/to/controlled-artifacts \
  --output /path/to/controlled-artifacts/recovery-readiness.json \
  --expected-source-commit "$GITHUB_SHA" \
  --expected-workflow-run-id "$GITHUB_RUN_ID"
```

The evaluator derives results from unique task, occurrence, alert, resource,
phase, and cleanup records. It rejects caller-provided result flags, aggregate
counts, mutable image references, mixed-generation cutovers, unknown tasks that
are not `AMBIGUOUS`, forbidden artifacts, and mismatched release/target
bindings. Credential-free evidence does not authorize live recovery; protected
disposable-Cell evidence requires the approved live qualification and
access-controlled attestation path.

Record restore, replay, reconciliation, alert-verification, and total recovery
durations separately. RPO is recovered event/data watermark loss, not handler
duration. RTO runs from containment start through successful canary
verification. Compare both with job and Cell objectives; an exceeded objective,
lost alert, duplicate launch, unreconciled occurrence, broken audit chain, or
untested application compensation blocks readiness.

## Rollback and escalation

If containment, restore, integrity, cutover, replay, reconciliation, or
verification fails, the controller records a stable failure code, leaves launch
disabled, restores the prior known-good pointer, and retains source/recovery
tables and all evidence. Do not delete restored tables until the incident
review and Job Owner side-effect compensation decision are complete.

If the prior pointer cannot be proven, backout fails closed and does not invent
an `INITIAL` pointer. Escalate for the next authorized restore point or forward
fix while retaining both isolated resource sets and the recovery manifest.

Record actual data loss, restore/replay/reconciliation/alert-verification
durations, and total RPO/RTO in the incident evidence. Escalate mixed-generation,
CONFIG-hash, Deployment-Identity, duplicate-launch, or terminal-overwrite
findings to Platform on-call and the owning Job Owner.
