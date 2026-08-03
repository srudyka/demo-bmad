# Pilot measurement runbook

This package measures a supplied baseline and pilot evidence set. It does not run AWS queries, deploy resources, approve rollout, or emit a production-readiness decision.

## Inputs and ownership

The measurement definition is owned by the platform/product metric owner. Baseline and pilot packages are owned by the evidence producers and must contain only normalized, sanitized records. Every source reference binds a source kind, repository, source revision, owner, observation window, sensitivity class, redaction state, and SHA-256 digest. Pilot records additionally bind the Deployment Identity, target manifest, CONFIG hash, and schedule generation.

Run the credential-free CLI from the repository root:

```bash
python -m scripts.run_pilot_measurement \
  --definition artifacts/definition.json \
  --baseline artifacts/baseline.json \
  --pilot artifacts/pilot.json \
  --artifact-root artifacts \
  --output artifacts/result.json \
  --report artifacts/reviewer-report.md
```

The artifact root must not contain symlinks, Terraform state or plans, credentials, secrets, raw logs, or payloads. Non-inline source locators are read as bounded files and their raw-byte SHA-256 is checked before calculation. Inline locators are reserved for visibly synthetic fixtures.

## Statuses and reruns

`MEASURED` means the declared calculation had complete evidence. `UNKNOWN` means a required population, such as the baseline, is absent. `INCOMPLETE` means required event evidence is missing. `INCONCLUSIVE` is reserved for an explicitly unresolved calculation outcome. `NOT_COMPARABLE` means baseline and pilot populations differ on declared dimensions. `BLOCKED` means a governed boundary prevented measurement. None of these statuses is a rollout approval.

Results are deterministic: samples are sorted by stable ID and the normalized result is sealed with RFC 8785 plus SHA-256. Rerun using the same inputs and calculation version; a changed source byte, definition, binding, timestamp, or tool version must produce a changed seal or a fail-closed validation error. Preserve the result and report with their input checksums according to the evidence retention policy, and do not retain rejected raw material.

## Redaction and retention

Do not include credentials, secret values, Terraform state or plans, unrestricted logs, application payloads, personal identifiers, or free-form sensitive text. Store only sanitized references and checksums in the published package. The evidence owner is responsible for retention, access control, and deletion of source material under the existing evidence policy; this story adds no artifact store or AWS resource.

## Handoff to Story 4.10

Give Story 4.10 the machine-readable result, reviewer report, definition checksum, source/package checksums, and any limitations or excluded sample IDs. Story 4.10 must independently review exact pilot jobs, owners, account/Region, notification target, GitHub controls, observation window, baseline, RPO/RTO, and approvers. Those external launch-checklist gates are never invented by this tool or its fixtures.

## Rollback

This story creates no AWS resources and has no production side effect. To roll back, revert the measurement scripts, schemas, fixtures, manifest/release updates, tests, and this runbook together, then rerun the repository validation entry point. Existing protected qualification artifacts remain governed by their owning workflows.
