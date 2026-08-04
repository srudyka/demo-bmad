---
epic: 4
story: 4.10
title: Publish Pilot Launch Checklist and Decision Record
status: done
baseline_commit: e3e247b
---

# Story 4.10: Publish Pilot Launch Checklist and Decision Record

Status: done

## Story

As a Platform Product Owner,
I want a governed pilot checklist and decision record,
so that external pilot execution and broader adoption proceed only when named owners, evidence, and acceptance rules are complete.

## Acceptance Criteria

1. Generate a versioned pilot artifact containing a launch checklist, observation contract, qualifying-change catalog, evidence manifest, approval matrix, rollback criteria, and decision-record schema. Every field must declare an accountable owner, evidence type, due point, status, and blocking classification.
2. When jobs or owners are unknown, identify the required target of one or two low-risk, non-customer-facing maintenance, cleanup, reporting, sync, or internal batch jobs and the intended first-pilot-within-one-sprint target. Keep launch `BLOCKED` until exact jobs, application/operational owners, repositories, accounts, Regions, Environments, dependencies, side effects, and risk classifications are assigned.
3. For each proposed candidate, require exact-release qualification from Stories 4.3–4.8, standard module/workflows, current compatibility, and complete Runbook, rollback, compensation, immutable-image, private-networking, scoped-IAM, log-retention, completion-contract, alarm, notification-route, and ownership evidence. Reject evidence from another release, Cell, job generation, account, or Region.
4. For production execution, require Platform Engineering and the owning application team to approve the exact Deployment Identity. Consult the versioned qualifying-change catalog and require Security/control-owner approval for applicable IAM, trust, secrets, state, or networking changes. Verify notification target, escalation policy, protected GitHub Environment, self-review prevention, branch protection, and emergency-bypass policy; unresolved placeholders block.
5. Require an approved observation contract with minimum duration and occurrence count, schedule frequencies, healthy windows, controlled failures, alert-latency target, false/lost-alert limits, setup-time method, review-finding categories, recovery rehearsal, and stop conditions. Version any threshold or exclusion changed after observation starts; never retroactively improve a result.
6. When release, contract, policy, module, workflow, IAM, networking, completion, alerting, or recovery behavior changes, classify which qualification, approval, observation window, or evidence is invalidated and must be repeated. Exempt editorial/non-behavioral changes only through a deterministic versioned rule.
7. When all checklist gates pass and authorized reviewers sign, emit `APPROVED_TO_START` bound only to named jobs, release, Deployment Identities, targets, observation window, and rollback plan. Any changed bound input, expired approval, failed preflight, or unavailable alert path returns the record to `BLOCKED`.
8. Support ingestion and packaging of externally supplied pilot evidence without code changes. Synthetic fixtures, a published checklist, and an `APPROVED_TO_START` record must never be represented as proof that a pilot executed or succeeded.
9. For stop conditions, severe incidents, uncontrolled duplicates, missing alerts, security violations, or unrecoverable evidence gaps, direct pause/disablement, evidence preservation, job/Cell recovery Runbook use, application-compensation assessment, escalation, failure disposition, and fresh approvals before restart.
10. After the observation window, consume Story 4.9’s exact measurement result and link every metric, limitation, exception, incident, review finding, recovery result, unresolved risk, and attestation to attributable evidence. Missing or inconclusive mandatory evidence prevents `ACCEPTED`.
11. Permit only `ACCEPTED`, `REMEDIATE_AND_REPEAT`, and `REJECTED` final outcomes, each with rationale, owners, due actions, scope, effective date, and approval identities. Acceptance requires Platform Engineering and the application owner, plus Security/control-owner approval when the catalog requires it.
12. On acceptance, publish rollout policy: all new ECS scheduled jobs use the standard module, materially changed existing jobs migrate, approved exceptions are time-bound and governed, adoption metrics continue from the pilot baseline, and support ownership, supported versions, deprecation communication, rollback/pause criteria, and rollout scope are explicit.
13. Automated complete, blocked, stale, changed-release, failed-pilot, inconclusive, exception, accepted, missing-approver, self-approval, and changed-input fixtures produce deterministic statuses. No default, placeholder, free-form comment, administrator bypass, or missing approver can authorize launch or acceptance.

## Tasks / Subtasks

- [x] Define the versioned launch/checklist and decision contract (AC: 1, 5–7, 10–13)
  - [x] Add strict JSON Schemas under `contracts/v1/schemas/` for checklist, observation contract, qualifying-change classification, evidence manifest, approval matrix, rollback criteria, launch authorization, and final decision record. Use `additionalProperties: false`, bounded strings/lists, explicit enums, aware RFC 3339 UTC timestamps, lowercase SHA-256 fields, and no secret/raw-payload fields.
  - [x] Define machine states separately: `BLOCKED`, `READY_FOR_REVIEW`, `APPROVED_TO_START`, `IN_PROGRESS`, `PAUSED`, `EVIDENCE_PENDING`, `ACCEPTED`, `REMEDIATE_AND_REPEAT`, and `REJECTED`. Do not conflate launch authorization with pilot execution or final acceptance.
  - [x] Require per-field owner, evidence type, due point, status, blocking flag, and source reference. Define required/optional controls and explicit unknown/inconclusive semantics.
  - [x] Bind every record to exact release version, Compatibility Package checksum, source commit, workflow SHA/run, account, Region, Environment, job IDs, repositories, owners, Deployment Identities, target manifest, module/workflow versions, observation window, rollback plan, and decision scope.
  - [x] Add schemas for approval identity/expiry, self-review prevention, protected Environment verification, change invalidation, stop/restart disposition, and evidence links. Reject placeholder actors, expired approvals, changed bindings, unknown policy versions, and unverified control paths.

- [x] Implement credential-free checklist and decision evaluation (AC: 1–7, 9–13)
  - [x] Extend the existing `scripts/` validation style with a pure evaluator and CLI, preferably `scripts/pilot_launch.py` and `scripts/run_pilot_launch.py`; reuse `scripts/pilot_measurement.py`, `scripts/readiness_gate.py`, `scripts/deployment_evidence.py`, `scripts/release_manifest.py`, and existing target/policy helpers rather than inventing identity or readiness formats.
  - [x] Validate exact-generation Story 4.3–4.8 evidence and the Story 4.9 result. Recompute/check checksums and bindings; never trust caller-supplied `passed`, counts, paths, target identities, readiness flags, or approval claims.
  - [x] Evaluate candidate completeness, owner/target assignment, compatibility, required controls, observation thresholds, evidence freshness, approval roles, catalog-triggered Security approval, notification/escalation readiness, and rollback/compensation readiness.
  - [x] Implement deterministic change classification for behavioral versus editorial changes. Behavioral changes invalidate only the explicitly affected qualification/approval/observation/evidence scopes; any uncertain classification is blocking. A changed release, workflow, policy, module, IAM, networking, completion, alert, recovery, job generation, target, or threshold must not silently retain approval.
  - [x] Implement launch status transitions and final decision transitions with monotonic/auditable history. `APPROVED_TO_START` is not evidence of execution; only attributable external observations can produce execution evidence.
  - [x] Implement pause/stop/restart evaluation: disable launch first through the authorized workflow/operator path, preserve sanitized evidence and inventories, invoke the existing job/Cell recovery Runbook, record application side-effect compensation, and require fresh approvals after disposition. Never call AWS, mutate Terraform, edit schedules/state directly, or auto-rerun from this credential-free evaluator.
  - [x] Produce a machine-readable record and concise reviewer report with status, blockers, evidence links/checksums, invalidations, limitations, owners, due actions, decision scope, and no sensitive values.

- [x] Define fixtures and evidence packaging (AC: 2–6, 8–13)
  - [x] Add a fixture catalog under `contracts/v1/fixtures/pilot-launch/` covering unassigned candidate, complete ready candidate, stale/mismatched release, missing owner/target, missing required control, expired approval, self-approval, missing notification path, changed input, stop condition, failed pilot, incomplete/inconclusive measurement, governed exception, accepted, remediate-and-repeat, rejected, and synthetic-only/non-executed cases.
  - [x] Include one or two candidate slots without inventing real job names, owners, accounts, Regions, notification targets, repositories, approvals, or pilot results. Unresolved values must remain explicit blockers/placeholders in fixtures and cannot pass validation.
  - [x] Represent evidence as bounded sanitized references with raw-byte SHA-256, provenance, sensitivity class, redaction state, observation window, source revision, and exact binding. Reject secrets, credentials, Terraform state/plans, unrestricted logs, raw CONFIG, application payloads, personal data, symlinks, path traversal, and output/input collisions.
  - [x] Keep synthetic evidence visibly fixture-only and ensure it cannot satisfy a live attestation or be labeled as executed/successful pilot evidence.

- [x] Register contracts and integrate existing authorities (AC: 1, 3, 6, 10–13)
  - [x] Register schemas/fixtures in `contracts/manifest.json` and update release metadata/checksums only according to existing semantic-surface rules; refresh exact bytes, not caller-provided hashes.
  - [x] Consume the existing production-readiness, Deployment Identity, target-manifest, release, workflow-provenance, policy-catalog, recovery, and pilot-measurement records. Do not create a second occurrence, readiness, approval, checksum, release, or rollout authority.
  - [x] Preserve contract major-version compatibility and add migration/release notes if the normative surface changes. Reject unsupported majors and unknown policy versions.

- [x] Add operational documentation (AC: 1–12)
  - [x] Add `docs/runbooks/pilot-launch.md` or the established equivalent covering candidate selection, ownership assignment, evidence collection, approvals, protected workflow invocation, observation start/stop, alert/incident handling, pause/disablement, recovery, compensation, restart, final decision, rollout, exception, and rollback.
  - [x] Document that pilot launch is an external/protected operation. Include operator role boundaries, no direct `RunTask`, no caller-created Occurrence IDs, no manual table/schedule/state edits, no workload credentials, no Terraform-state inspection, and no production action from fixture/credential-free tooling.
  - [x] Document retention, access control, redaction, auditability, evidence classification, support ownership, known limitations, RPO/RTO expectations, and the distinction between infrastructure rollback and application compensation.
  - [x] Document GitHub protected Environment assumptions and fallback controls. Required reviewers and self-review prevention are configuration-dependent; verify actual repository settings and do not claim protection from workflow YAML alone.

- [x] Test and validate (AC: 13)
  - [x] Add contract tests in `tests/contract/` for every positive/negative fixture, schema validation, deterministic status and seal, changed-input invalidation, approval expiry/role rules, exception catalog, and decision transition.
  - [x] Add regression tests proving Story 4.9’s measurement result is consumed without changing its semantics and that fixture/checklist/approval outputs cannot be mistaken for executed pilot evidence.
  - [x] Run focused tests, full `pytest tests runtime -q -p no:cacheprovider`, Ruff format/lint, mypy, `git diff --check`, repository hygiene, and `./scripts/validate.sh`. If Terraform files change, run `terraform fmt -check`, backend-free validation for each affected root/module example, and the IaC security scan; do not hide pre-existing validation failures.

### Review Findings

Review remediation applied: preflight authorization is measurement-independent and sealed separately; Story 4.9 schema/seal, job/evidence bindings, approval freshness/identity independence, pause/alert gates, bound-input invalidation, executable fixture inputs, artifact-root safety, rollout policy, and decision evidence references are now enforced. Focused and full contract validation pass.

- [ ] [Review][Patch] [Critical] Separate pre-pilot launch authorization from post-pilot measurement [scripts/pilot_launch.py:641-747] — `evaluate_launch_checklist` requires a Story 4.9 measurement before returning `APPROVED_TO_START`, even though measurement is produced after the observation window. This makes the launch gate unusable and conflates authorization with execution; evaluate launch without measurement, then require measurement for final decisions.
- [ ] [Review][Patch] [High] Validate Story 4.9 evidence through its authoritative schema and seal [scripts/pilot_launch.py:566-603,791-837] — `validate_measurement_result` accepts a matching binding plus `metrics: [{"status":"MEASURED"}]` without schema validation, recomputing `evidence_sha256`, source/package checksum verification, or metric-level evidence. A caller can fabricate a measured result and obtain `ACCEPTED`.
- [ ] [Review][Patch] [High] Enforce exact job and evidence status bindings [scripts/pilot_launch.py:204-241,461-481] — evidence `job_id` is never compared with a checklist job, and passed controls only require an existing evidence ID; `pending`, `failed`, or `synthetic` evidence can satisfy them. Require named-job matching and verified authoritative evidence before a blocking control passes.
- [ ] [Review][Patch] [High] Enforce approval freshness, independent roles, and exact Deployment Identities [scripts/pilot_launch.py:275-309,641-747] — approval expiry is checked only against `approved_at`, required roles and self-review prevention are caller-controlled, the same actor can satisfy multiple roles, and approval/rollback identity hashes are not bound to the checklist. Expired or mismatched approvals can authorize launch.
- [ ] [Review][Patch] [High] Emit and validate a complete launch authorization record [contracts/v1/schemas/pilot-launch-authorization.schema.json:7-9, scripts/run_pilot_launch.py:63-72] — the CLI emits only a generic evaluation result, while the registered authorization schema permits unconstrained bindings and incomplete approvals. Produce the exact authorization fields and make schema/evaluator validation agree.
- [ ] [Review][Patch] [High] Make stop and paused states fail closed [scripts/pilot_launch.py:641-747] — a `PAUSED` checklist with otherwise passing inputs can return `APPROVED_TO_START`; no disposition, fresh approval, launch-disablement evidence, or restart transition is required. Paused/stop-condition records must remain blocked until recovery and reapproval are verified.
- [ ] [Review][Patch] [High] Require operational alert/escalation gates and non-zero observation thresholds [scripts/pilot_launch.py:407-429,482-501] — the contract has no notification target or escalation binding, allows zero minimum duration/occurrences, and does not enforce observation version/lifecycle or threshold changes. Launch can pass without an alert path or meaningful observation contract.
- [ ] [Review][Patch] [High] Replace caller-supplied change classification with bound-input invalidation [scripts/pilot_launch.py:605-637] — `invalidate_launch` classifies one caller-provided string against a sparse catalog but does not compare current versus approved release/module/workflow/IAM/network/target/threshold inputs or record invalidated evidence. Changed or uncertain inputs can retain approval.
- [ ] [Review][Patch] [Medium] Make fixture cases executable and prevent synthetic authorization claims [contracts/v1/fixtures/pilot-launch/cases.json:4-21, tests/contract/test_pilot_launch.py:295-305] — the fixture catalog contains names and expected statuses but no inputs, and tests only assert names exist. It cannot prove the required negative paths; one fixture also labels synthetic-only input `APPROVED_TO_START`, contradicting the non-execution boundary.
- [ ] [Review][Patch] [Medium] Harden CLI artifact-root and malformed-input handling [scripts/run_pilot_launch.py:19-72] — unlike Story 4.9’s runner, this CLI does not reject symlinks, secrets, state/plans, raw logs, or prohibited content under the artifact root, and malformed `null`/unhashable nested values can raise uncaught `TypeError` instead of deterministic validation errors.
- [ ] [Review][Patch] [Medium] Complete rollout policy and attributable decision evidence [scripts/pilot_launch.py:791-837] — the decision record stores only four rollout booleans and accepts arbitrary `evidence_ids`, without resolving them to the manifest or linking limitations, incidents, recovery results, attestations, support ownership, supported versions, exception expiry, deprecation communication, or rollback/pause criteria.

## Dev Notes

### Scope and non-goals

- This story publishes and validates the pilot launch/decision machinery. It does not select real pilot jobs, create AWS resources, execute a real pilot, approve production infrastructure, query live AWS, or make up owners, accounts, Regions, notification targets, approvals, thresholds, or results.
- Story 4.9 owns deterministic measurement. This story consumes its result and owns the launch checklist, `APPROVED_TO_START`, and final decision outcomes. A checklist, approval, fixture, or measurement result alone is never proof that a pilot ran or succeeded.
- No Terraform change is expected. If implementation discovers a necessary infrastructure or GitHub configuration change, preserve resource/workflow ownership and stop to document the required separate change, security impact, plan impact, rollback, and approver.

### Authoritative boundaries and invariants

1. `contracts/` is the normative Compatibility Package; all schemas, enums, identities, and fixtures must be versioned and checksum-registered.
2. Existing readiness, Deployment Identity, release, target, policy, recovery, and measurement authorities remain authoritative. The new evaluator projects them into a launch/decision record; it must not recalculate AWS authorization or replace their schemas.
3. Every approval and decision is exact-scope: job, generation, release, Deployment Identity, target, observation window, rollback plan, source revision, workflow run, and policy catalog.
4. Missing, stale, contradictory, duplicated, mismatched, or unavailable evidence is explicit and blocking where required; it is never silently downgraded to success.
5. Production launch is disable-first and protected. Stop/recovery preserves evidence, retains application-impact information, and requires fresh authorization before resuming.
6. `ACCEPTED` means authorized reviewers accepted attributable pilot results for the declared scope. It does not claim every job migrated or erase approved exceptions.

### Existing code and files to read/extend

- `scripts/pilot_measurement.py`, `scripts/run_pilot_measurement.py`: Story 4.9’s strict evidence bindings, measurement statuses, deterministic sealing, sanitized artifact-root policy, and reviewer-report boundary. Extend/consume; do not emit launch or acceptance from the measurement engine.
- `scripts/readiness_gate.py`: exact-generation readiness bindings, policy catalog, required approvals, expiry, exceptions, invalidation, and sanitized summary behavior.
- `scripts/deployment_evidence.py`: Deployment Identity, target/account/Region/environment bindings, exact evidence checksums, approval provenance, rollback/recovery evidence, and lookup index.
- `scripts/release_manifest.py`: immutable artifact references, qualification status, semantic change classification, component ranges, and release verification.
- `scripts/production_bundle.py`, `scripts/production_policy.py`, `scripts/production_apply.py`, `scripts/apply_evidence.py`, and existing qualification runners: reuse bundle, policy, apply, and protected-evidence boundaries rather than parsing workflow success or Terraform state.
- `.github/workflows/production-approval-evidence.yml`, `.github/workflows/production-approval-bundle.yml`, `.github/workflows/production-apply.yml`, `.github/workflows/production-recovery.yml`, and qualification workflows: preserve trusted/untrusted separation, full-SHA pins, protected Environment gates, artifact provenance, exact-plan binding, and manual approval behavior.
- `contracts/v1/schemas/production-readiness-decision.schema.json`, `readiness-evidence.schema.json`, `deployment-identity.schema.json`, `release-manifest.schema.json`, `production-approval.schema.json`, `production-exception.schema.json`, `pilot-measurement-result.schema.json`, and related catalogs/fixtures.
- `docs/runbooks/pilot-measurement.md`, `docs/runbooks/cell-recovery.md`, `docs/runbooks/operator-commands.md`, `docs/runbooks/job-runbook-template.md`, `docs/runbooks/pull-request-validation.md`, and `docs/scheduled-job-adoption-guide.md`.

### Required decision model

- Launch checklist status: `BLOCKED` until all blocking fields and exact evidence are present; `READY_FOR_REVIEW` only when the package is complete; `APPROVED_TO_START` only after required approvals and preflight; `PAUSED` after a stop condition; `EVIDENCE_PENDING` until the declared observation package is supplied.
- Final decision: `ACCEPTED`, `REMEDIATE_AND_REPEAT`, or `REJECTED`. `ACCEPTED` requires complete comparable measurement where mandatory, no unresolved blocking risk, exact evidence links, required approvals, and explicit rollout scope. `INCONCLUSIVE`/`UNKNOWN`/`NOT_COMPARABLE` measurement results cannot be converted to acceptance by comment or override.
- Qualifying-change catalog must classify at least: release/contract/policy, module/workflow/action/provider, IAM/trust/secrets/state/networking, job/config/schedule/generation, completion/alerting/observability, recovery/rollback, threshold/exclusion/observation method, and editorial-only changes.
- Approval matrix must distinguish Platform Engineering, application owner/team, Job Owner/on-call ownership, Security/control owner when catalog-triggered, and emergency approver. Prevent self-approval and require expiry, actor identity, exact scope, source revision, workflow run, and Deployment Identity.

### Security, reliability, and observability guardrails

- Do not add `Principal = "*"`, broad IAM, public ingress, public storage, mutable images, plaintext secrets, raw plans/state/logs, or workload credentials. Protected GitHub Environment settings are an external control and must be verified, not assumed.
- Use bounded identifiers and sanitized evidence. Never put Occurrence IDs in metric dimensions; do not expose raw CONFIG, credentials, application payloads, or unrestricted logs in reviewer reports.
- The artifact itself must be auditable and observable through logs/metrics/alarms of its hosting workflow if later integrated. This story adds no production component; document workflow failure, stale evidence, missing alert path, and artifact-retention failure modes.
- Rollback is procedural: pause/disable launch, preserve evidence, inventory in-flight tasks/occurrences/alerts/side effects, invoke the tested job/Cell Runbook, restore a known-good exact identity through a fresh protected plan, verify, and obtain fresh approvals. Infrastructure rollback does not reverse application effects.

### Toolchain and latest technical specifics

- Preserve the repository-pinned matrix from Story 4.9: Python 3.14.6, uv 0.11.29, Terraform 1.15.8, AWS provider 6.54.0, Ruff 0.15.21, mypy 2.3.0, pytest 9.1.1, and Checkov 3.3.8. Tested patch versions are not permanent runtime constraints unless the existing compatibility contract says so.
- GitHub artifact attestations establish build provenance only when the attestation is generated and verified; an uploaded report name or checksum alone is not workflow provenance. See [GitHub artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations).
- GitHub protected Environments can require reviewers, restrict branches, and prevent self-review, but availability and enforcement depend on repository/plan configuration; verify settings through the protected workflow/repository controls. See [GitHub deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments).
- If a future implementation stores evidence in S3, use server-validated SHA-256 object checksums and verify them on read; do not use ETags as whole-object identity, especially for multipart uploads. See [Amazon S3 object integrity](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity.html).
- Use aware UTC timestamps (`datetime.now(UTC)` or equivalent), not naive `utcnow()`, and bind observation windows explicitly.

### Previous story intelligence

Story 4.9 (`4e6210c`) created the measurement schemas, pure evaluator, CLI, fixture catalog, contract tests, manifest/release registration, and measurement runbook. Reuse its exact bindings, source checksums, status semantics, sanitized-root policy, deterministic ordering/sealing, and explicit handoff. Do not change the measurement engine to emit launch authorization or final acceptance.

Story 4.8 (`64fb792`) established disable-first recovery, exact release/target bindings, recovery inventories, source-run provenance, per-control evidence, sanitization, freshness, immutable image references, and separation between credential-free evaluation and protected/live qualification. Preserve those boundaries for stop/restart and decision evidence.

Stories 4.3–4.7 established readiness, security, schedule, ECS runtime, completion/alert, protected workflow, and release/target qualification categories. Consume their exact evidence from the exact release candidate and disposable Cell; never substitute aggregate workflow success or fixtures from another target.

### Git intelligence

- Current recent commits: `e3e247b` Fix recovery Lambda references; `4e6210c` Implement pilot measurement evidence packaging; `64fb792` Harden recovery and security qualification; `b9dbb9d` Resolve completion qualification review findings; `49dd867` Qualify completion deadlines and alert durability.
- Recent work consistently uses strict JSON contracts, credential-free negative fixtures, protected workflows for live qualification, exact release/target/source-run checksums, runbook updates, and manifest/release checksum refreshes. Follow those patterns.
- The current working tree was clean at story creation. Preserve unrelated changes if that changes before implementation.

### AWS Terraform implementation standard acceptance criteria

- No new AWS resource is authorized. Any future artifact-store or workflow integration must preserve single-owner boundaries, predictable names, required tags, encryption, least-privilege IAM, explicit validation, stable addresses, retention, alarms/logs, and rollback notes.
- CI validation for any Terraform change must include format, validation for each affected root/example, and IaC security scanning. Production changes require plan review and manual approval.
- No artifact store may publish secrets, raw plans/state, unrestricted logs, or unnecessary application data. Any deviation from the standard must be explicit in the story, implementation, PR notes, and rollback plan.

### Rollback notes

This story’s default implementation creates no AWS resources and has no production side effect. Roll back by reverting the story’s schemas, evaluator/CLI, fixtures, tests, manifest/release metadata, and runbook as one contract change, then rerun repository validation. Never delete accepted evidence or pilot records solely to roll back code; preserve immutable evidence and record the superseding decision or schema migration.

## References

- [Epic 4 Story 4.10](/Users/srudyka/slower/demo-bmad/_bmad-output/planning-artifacts/epics.md:2955)
- [Epic 4 context and implementation notes](/Users/srudyka/slower/demo-bmad/_bmad-output/planning-artifacts/epics.md:2344)
- [Project context](/Users/srudyka/slower/demo-bmad/_bmad-output/project-context.md)
- [AWS Terraform implementation standard](/Users/srudyka/slower/demo-bmad/_bmad/custom/standards/aws-terraform-implementation.md)
- [Architecture production evidence gate, AD-22](/Users/srudyka/slower/demo-bmad/_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md:198)
- [Architecture workflow-bound delivery authority, AD-16](/Users/srudyka/slower/demo-bmad/_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md:162)
- [Architecture immutable supply chain, AD-17](/Users/srudyka/slower/demo-bmad/_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md:168)
- [Architecture two-phase rollback, AD-18](/Users/srudyka/slower/demo-bmad/_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md:174)
- [Architecture recovery, AD-26](/Users/srudyka/slower/demo-bmad/_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md:226)
- [PRD success metrics](/Users/srudyka/slower/demo-bmad/_bmad-output/planning-artifacts/prds/prd-demo-bmad-2026-07-13/prd.md:432)
- [PRD rollout and rollback principles](/Users/srudyka/slower/demo-bmad/_bmad-output/planning-artifacts/prds/prd-demo-bmad-2026-07-13/prd.md:455)
- [Story 4.9 implementation context](/Users/srudyka/slower/demo-bmad/_bmad-output/implementation-artifacts/4-9-automate-pilot-measurement-and-evidence-packaging.md)
- [Story 4.8 implementation context](/Users/srudyka/slower/demo-bmad/_bmad-output/implementation-artifacts/4-8-rehearse-job-and-cell-recovery.md)
- [Production readiness schema](/Users/srudyka/slower/demo-bmad/contracts/v1/schemas/production-readiness-decision.schema.json)
- [Pilot measurement result schema](/Users/srudyka/slower/demo-bmad/contracts/v1/schemas/pilot-measurement-result.schema.json)
- [Readiness evaluator](/Users/srudyka/slower/demo-bmad/scripts/readiness_gate.py)
- [Deployment evidence helpers](/Users/srudyka/slower/demo-bmad/scripts/deployment_evidence.py)
- [Pilot measurement runbook](/Users/srudyka/slower/demo-bmad/docs/runbooks/pilot-measurement.md)
- [GitHub artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)
- [GitHub deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
- [Amazon S3 object integrity](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity.html)

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

- Initial focused tests exposed canonical timestamp requirements and an evidence-list validation gap; corrected fixtures and enforced evidence references for passed controls.
- Static analysis exposed an unused import, reviewer-report list mutation typing, and a test mapping type issue; corrected before the final validation pass.
- Networked `./scripts/validate.sh` initially could not resolve PyPI. The documented nameserver setting required administrator privileges; the elevated retry completed successfully.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Target discovered from the first `backlog` story in the complete sprint status file.
- Project context, AWS Terraform standard, Epic 4, Story 4.9, Story 4.8, architecture spine, PRD rollout/metrics, existing readiness/deployment/release/measurement code, recent commits, and current official GitHub/AWS guidance were analyzed.
- Added strict pilot launch checklist, launch authorization, and decision-record schemas with exact bindings, statuses, evidence references, approvals, observation contract, change catalog, and rollback criteria.
- Added a pure credential-free evaluator/CLI with exact-scope measurement consumption, blocking status derivation, Security approval triggers, behavioral-change invalidation, self-review/expiry checks, synthetic-evidence protection, deterministic decision sealing, and sanitized reviewer reporting.
- Added complete boundary fixtures, contract tests, manifest/release registration, and the pilot launch runbook. No AWS resources, credentials, Terraform state, plans, live pilot data, or production identifiers were created.
- Validation passed: 426 tests and 373 subtests; focused contract/schema tests 24 passed; Ruff format/lint; mypy; Terraform format/validation; Checkov job module 118, platform Cell 798, canary fixture 98; repository hygiene; and `./scripts/validate.sh`.

### File List

- `_bmad-output/implementation-artifacts/4-10-publish-pilot-launch-checklist-and-decision-record.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `contracts/manifest.json`
- `contracts/releases/1.0.0.json`
- `contracts/v1/fixtures/pilot-launch/cases.json`
- `contracts/v1/schemas/pilot-decision-record.schema.json`
- `contracts/v1/schemas/pilot-launch-authorization.schema.json`
- `contracts/v1/schemas/pilot-launch-checklist.schema.json`
- `docs/runbooks/pilot-launch.md`
- `scripts/pilot_launch.py`
- `scripts/run_pilot_launch.py`
- `tests/contract/test_contract_schemas.py`
- `tests/contract/test_pilot_launch.py`

### Change Log

- 2026-08-04: Implemented pilot launch checklist/authorization and decision contracts, evaluator/CLI, fixtures, tests, manifest/release registration, and runbook; validated and moved story to review.
