# Platform Version Migration Runbook

This runbook governs Story 3.8 expand–migrate–contract migrations. It applies
only to an immutable source commit and release manifest; it does not publish a
release or retire an old version.

## Preconditions

1. Build the migration manifest from the Story 3.7 release identities and
   checksums.
2. Inventory every consumer, job, ownership generation, CONFIG version,
   occurrence/task attempt, queue/DLQ, state address, policy, operator
   procedure, rollback identity, and horizon. Unknown values block the run.
3. Calculate the maximum queue, replay, runtime, retention, investigation,
   recovery, and rollback horizon. Preserve every old identity until it expires.
4. Confirm each consumer has an owner, target version, validation result,
   required code/config change, due point, and rollback identity.
5. Prepare sanitized source and target snapshots containing records, schema and
   access-pattern checksums, reducer-invariant success, and launch-disabled
   state. The credential-free executor derives counts and checksums from these
   snapshots; callers never supply phase checksums as evidence.
6. Supply both immutable release-manifest paths. The workflow verifies their
   raw-byte SHA-256 values and release versions against the migration manifest;
   arbitrary caller-supplied release metadata is rejected.

## Execution

Run the protected `Migrate compatible platform release` workflow from the exact
source commit. Supply a fresh phase-state record, operation/checkpoint identity,
snapshots, and the verified predecessor envelope for every transition after
`expand`. A successful run means the bounded executor derived matching
source/target observations and safety invariants; metadata validation alone is
never reported as migration completion. The phases are ordered:

1. **Expand:** publish additive schemas/ranges, indexes, permissions,
   readers/writers, runtime support, workflow support, and policy support.
2. **Migrate:** run bounded, resumable, idempotent data/index work. Compare
   source/target counts, checksums, schemas, access patterns, and reducer
   invariants. Keep launch disabled until all evidence is complete.
3. **Cutover:** use a fresh reviewed plan and protected approvals. The exact
   plan evidence must bind plan/policy/target checksums and an unexpired approval;
   the acknowledgement binds migration ID, target release/checksum, and horizon
   watermark before aliases, Cell Contract pointers, workflow manifests, and
   policy catalogs switch.
4. **Verify:** check occurrence state, exactly-one launch, completion
   correlation, delayed/DLQ replay, logs, deadlines, alarms, notifications,
   and recovery. Do not proceed with mixed unsupported versions.

## Rollback

Disable launch first. Restore the prior compatible aliases and Contract
pointers, preserve old schemas/CONFIG/runtimes/modules/task definitions and
evidence, and replay retained evidence only through supported canonical paths.
Record rollback identity, verification, remaining horizon, limitations, and
Job Owner application compensation. A migration rollback does not delete or
deprecate artifacts; Story 3.9 owns retirement and the lifecycle principal owns
physical cleanup after exact evidence proves no references remain.

The workflow retains the complete sanitized evidence envelope for 90 days. A
manifest whose maximum compatibility horizon exceeds that retention limit is
rejected and requires a longer-lived evidence store before execution.

## Validation

```bash
python -m pytest tests/contract/test_migration_contract.py -q -p no:cacheprovider
PATH=/private/tmp/demo-bmad-uv-01129:$PATH UV_CACHE_DIR=/private/tmp/demo-bmad-uv-cache ./scripts/validate.sh
git diff --check
```

Never use live AWS credentials, production state, binary plans, raw CONFIG, or
secrets for credential-free migration qualification.
