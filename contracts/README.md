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

## Rollback

This package creates no AWS resources. Revert the package, tests, dependency
lock, and documentation together, then rerun `./scripts/validate.sh`. Never
remove a contract version still referenced by a queue, DLQ, CONFIG, occurrence,
investigation, or rollback window.
