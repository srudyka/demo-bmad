# Compatibility Package

This directory is the normative, language-neutral contract for every Platform
Cell module, runtime producer, processor, workflow, and operational projection.
Consumers must load `manifest.json`, select a supported major, and validate all
inputs before side effects. Remote schema retrieval is prohibited.

## Layout

- `manifest.json` declares package identity, compatibility ranges, artifact
  roots, and exact raw-byte checksums.
- `v1/schemas/` contains Draft 2020-12 boundary and payload schemas.
- `v1/catalogs/` owns authority, lifecycle, metrics, alarms, limits, and keys.
- `v1/catalogs/production-policy.json` owns the versioned production policy,
  qualifying-change categories, severity posture, and exception fields.
- `v1/schemas/production-approval.schema.json` and
  `v1/schemas/production-readiness-decision.schema.json` bind protected apply
  approvals and exact-generation readiness to the deployment plan.
- `v1/schemas/readiness-evidence.schema.json` defines the separate, additive
  evidence envelope for category results, tool versions, sensitivity,
  attestations, bounded remediation, and freshness. It never replaces the
  strict apply-facing readiness decision.
- `v1/fixtures/` contains language-neutral positive and negative vectors.
- `releases/` records immutable release snapshots.
- `migrations/` contains the actionable note for each release.

## Consumer Workflow

1. Load JSON as strict UTF-8 and reject duplicate keys and non-finite numbers.
2. Verify the package major and component compatibility matrix.
3. Verify artifact checksums and resolve every schema from the local registry.
4. Validate syntax, canonical forms, authority assertions, and semantic rules.
5. Reject unsupported input with the stable error code and migration reference.

## Versioning And Migration

The package uses SemVer 2.0.0. Patch releases change documentation or correct
compatible fixtures. Minor releases add optional compatible fields, event
types, or catalog entries. Removing fields, adding required fields, changing
identity bytes, authority, state reduction, or behavior requires a new major.
Every change is compared with the checked-in predecessor snapshot. Breaking
changes require a major bump and migration note. The initial `1.0.0` release
has no predecessor and declares `previous_major` as null.

The current major and previous major remain supported for at least 14 days and
longer while referenced by CONFIG, occurrences, queues, DLQs, investigations,
or rollback. Old artifacts are never removed merely because a newer release
exists.

## Deprecation and retirement

A deprecation record is additive: it is `warn-only`, names a replacement,
affected consumers, migration guide, support owner/review date, earliest
removal major, and sanitized GitHub/internal notice details. Security-emergency
exceptions require a risk, compensating control, migration path, independent
approvers, and an exact end date. Notice tracking names immutable
contracts/retirement-evidence artifacts and their raw-byte checksums for both
publication channels, every acknowledgement, and each open exception; the
lifecycle-owned evidence reader verifies those bytes without retaining
sensitive deployment data.

Only a complete checksum-bound retirement handoff can enter lifecycle cleanup.
It binds completed migration evidence, exact release and artifact identities,
inventory/reference proof, all recovery horizons, a fresh reviewed plan, and
protected approval. Unknown owners/telemetry/references, active aliases, an
unexpired horizon, or current/previous-major support block retirement. The
dedicated lifecycle principal alone deletes the exact artifact and records the
tombstone; no release/deployment/workflow/operator role gets deletion authority.
The principal accepts only strict-JSON handoff bytes accompanied by the
protected workflow's raw-byte checksum envelope from its lifecycle-owned
evidence store, and it durably records deletion intent, invalidation
remediation, tombstones, and post-cleanup verification results.

## Security

Contracts and fixtures contain identifiers and approved secret references only,
never secret values. Use unmistakably fake structural sentinels in isolated
fixtures. Producer identity comes from registered AWS metadata, not message
body assertions. Wildcard IAM authority is invalid unless the catalog records
the AWS requirement, narrowing conditions, owner, and review justification.

## Occurrence Materialization

The occurrence materializer owns only `occurrence.expected.v1`. Its producer
event ID is the SHA-256 of the exact ASCII bytes
`materializer/v1\n<job_id>\n<schedule_generation>\n<scheduled_time>\n<config_version>\n<owner_generation>`.
It reads one immutable CONFIG, materializes an at-least-24-hour horizon, and
creates conditional CONFIG snapshots. It does not create Scheduler schedules,
write occurrence ledger state, or produce `occurrence.launch.v1`.

## Validation

Run the same credential-free command used by pull-request CI:

```bash
./scripts/validate.sh
```

Conformance tests use only checked-in data, perform no schema network retrieval,
open no AWS session, and require no deployment-specific environment values.

The readiness gate accepts only exact-generation evidence. Every item is bound
to the repository/source, workflow run, target, plan, Cell, job, CONFIG,
schedule generation, Deployment Identity, policy version, and artifact checksum.
Missing categories, stale or contradictory items, fixture evidence in
production, secrets/raw CONFIG, and free-form remediation fail closed. The gate
publishes a sanitized summary; binary plans, credentials, and unrestricted logs
remain in controlled protected artifacts only.

## Rollback

This package creates no AWS resources. Revert the package, tests, dependency
lock, and documentation together, then rerun `./scripts/validate.sh`. Never
remove a contract version still referenced by a queue, DLQ, CONFIG, occurrence,
investigation, or rollback window.

## Immutable platform releases

Platform releases use `release-manifest.schema.json`. The source commit, builder
workflow, qualification evidence, policy bundle, artifact checksums, and
immutable references are bound in one manifest. Defective releases receive a
new corrected version; original evidence is retained and never overwritten for
the 30-day rollback horizon. The immutable GitHub release/tag is the release
registry; publication notices are sent through the GitHub release and the
internal engineering channel. An affected release is recorded without deleting
or overwriting the original, and a correction points to both the affected and
replacement versions. Rollback uses the exact replacement/known-good release
identity recorded in the release notes; migration actions remain two-phase.
