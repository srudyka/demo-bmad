---
epic: 4
story: 4.9
title: Automate Pilot Measurement and Evidence Packaging
status: done
baseline_commit: 64fb792
---

# Story 4.9: Automate Pilot Measurement and Evidence Packaging

Status: done

## Story

As a Platform Product Owner,
I want pilot results measured from attributable source evidence,
so that adoption decisions compare the platform with the baseline using reproducible data rather than estimates.

## Acceptance Criteria

1. When versioned pilot measurement definitions are supplied, validation requires every metric to declare its start event, stop event, unit, inclusion rules, exclusions, evidence sources, owner, calculation method, target, and comparability requirements. Setup time must distinguish active engineering effort, review effort, approval wait, deployment wait, and unrelated interruption time.
2. When baseline evidence from recent scheduled-job implementations or pull requests is supplied, ingestion records sample size, repositories, observation period, job-complexity classification, provenance, setup findings, and review findings. Missing baseline data is represented as `UNKNOWN`; the assumed one-to-three-day estimate is never used as measured data.
3. When one or two pilot-job evidence packages are supplied, each package is bound to the Job Owner, risk class, repository, source revision, Deployment Identity, Environment, account, Region, module version, workflow version, pilot window, and approval record. Evidence from another job, revision, generation, or window cannot be combined silently.
4. When delivery workflow evidence is available, the result reports active setup effort, elapsed lead time, review cycles, failed checks, manual interventions, and time to a successful standard deployment. The less-than-four-hour target and at-least-50-percent active-effort reduction are evaluated only when baseline and pilot samples are comparable and complete.
5. When pull-request and policy evidence is available, findings are categorized for IAM scope, tags, alarms, log retention, networking, secrets, image immutability, rollback, and documentation. Each finding is classified as automatically prevented, found during review, governed exception, reopened, or unresolved.
6. When deployed-job evidence is available, control adoption verifies required ownership tags, private networking, immutable images, scoped IAM, explicit log retention, occurrence-aware completion, production alarms, notification routing, Runbook, and rollback evidence for each exact-generation readiness record. A control counts only when its bound readiness evidence passes.
7. When operational observations are available, reliability results include expected, started, successful, failed, overdue, missed, duplicate, and ambiguous occurrences; alert detection and delivery latency; false and lost alerts; reruns; incidents; and recovery rehearsal time. Denominators, windows, exclusions, and unresolved evidence are visible.
8. When survey or interview evidence is supplied, the tool records adoption friction, ECS knowledge required, documentation gaps, operational clarity, and requested improvements with role and collection date, while excluding personal or sensitive data. Qualitative feedback must never be converted into a quantitative success claim.
9. When evidence is incomplete, contradictory, duplicated, stale, outside the declared window, or not comparable, each affected metric is marked `INCOMPLETE`, `INCONCLUSIVE`, or `NOT_COMPARABLE` with an exact reason. The tool never fabricates a pass, drops an unfavorable sample, or treats an assumption as measured fact.
10. When the same validated input package and tool version are processed again, normalized metrics, comparisons, status, and decision inputs are deterministic. Output records schema versions, calculation version, source checksums, generated timestamp, limitations, and auditable links to non-sensitive source records.
11. When pilot data may contain sensitive operational information, access, retention, redaction, and artifact classification follow the evidence policy. Credentials, secret values, raw Terraform plans, unrestricted logs, and unnecessary application data are rejected or excluded before publication.
12. When no real pilot has executed, synthetic complete, incomplete, contradictory, stale, duplicate, and non-comparable fixtures cover every calculation and fail-closed path. Passing fixtures prove measurement capability only; they cannot be represented as an executed or successful external pilot.
13. When a real pilot package is later supplied, the tool emits a versioned machine-readable result and concise reviewer report for Story 4.10, presenting target met, target missed, inconclusive, limitations, and unresolved risks without making the final rollout decision.

## Tasks / Subtasks

- [x] Define and validate the measurement contract (AC: 1, 9-10)
  - [x] Add versioned schemas for measurement definitions, source evidence references, normalized samples, metric results, and the packaged report; use strict JSON, `additionalProperties: false`, RFC 3339 UTC timestamps, bounded strings/lists, and lowercase SHA-256 checksums.
  - [x] Require a definition for every metric with `metric_id`, owner, unit, start/stop event, inclusion/exclusion predicates, evidence-source types, calculation version, target, and comparability dimensions.
  - [x] Define stable statuses: `MEASURED`, `UNKNOWN`, `INCOMPLETE`, `INCONCLUSIVE`, `NOT_COMPARABLE`, and `BLOCKED`; never coerce missing or estimated values into numeric observations.
  - [x] Define canonical source references with source kind, locator, raw-byte checksum, provenance binding, sensitivity class, observation window, and redaction status; reject path traversal, symlinks, plans, state, credentials, secrets, raw payloads, and unrestricted logs.

- [x] Implement deterministic pilot measurement and packaging (AC: 1-10, 13)
  - [x] Add `scripts/pilot_measurement.py` with pure validation, normalization, metric calculation, comparison, status derivation, and RFC 8785 package sealing; do not call AWS or infer unreported values.
  - [x] Add `scripts/run_pilot_measurement.py` as a credential-free CLI that accepts definition, baseline, pilot, and source-artifact roots, validates containment and file policy, emits a machine-readable result plus concise Markdown/JSON reviewer report, and returns nonzero for malformed or unsafe packages.
  - [x] Keep calculations deterministic: sort samples and source references by stable IDs, use decimal-safe integer seconds or explicitly defined decimal precision, define median/percentile behavior for even and small samples, and exclude no sample without recording the rule and reason.
  - [x] Calculate setup metrics from explicit event timestamps: active engineering effort, review effort, approval wait, deployment wait, unrelated interruption, total active effort, elapsed lead time, review cycles, failed checks, manual interventions, and time to first successful standard deployment. Reject naive timestamps, negative durations, overlapping category ownership, and fabricated end events.
  - [x] Calculate control findings, exact-generation adoption, operational reliability, alert latency, recovery time, and qualitative summaries from normalized source records. Preserve denominators and excluded/unresolved sample IDs in the result.
  - [x] Compare pilot and baseline only across matching declared complexity, repository/process class, observation unit, and window rules. Emit `NOT_COMPARABLE` for mismatched populations; emit `UNKNOWN` when a baseline or pilot is absent.
  - [x] Emit only measurement outcomes and limitations. Do not emit `ACCEPTED`, `APPROVED_TO_START`, or any production-readiness authorization; Story 4.10 owns the decision record.

- [x] Reuse existing authority and evidence boundaries (AC: 2-7, 10-11)
  - [x] Reuse existing deployment, readiness, production bundle, release, and checksum conventions instead of creating a second authority model.
  - [x] Validate source package bindings against release, workflow, account, Region, Environment, job, schedule, CONFIG, Deployment Identity, and artifact checksum fields.
  - [x] Require exact-generation readiness evidence for deployed control adoption; caller-supplied non-evidence flags cannot count.
  - [x] Accept external pilot evidence as attributable input without requiring AWS credentials or changing production state. Synthetic fixtures remain visibly fixture-only.

- [x] Add complete fixture and regression coverage (AC: 9, 12)
  - [x] Add the complete comparable, missing, incomplete, contradictory, duplicate, stale, non-comparable, exception, control, sensitive, qualitative, and deterministic fixture catalog.
  - [x] Add engine and CLI regression tests covering metrics, statuses, bindings, checksums, sanitization, comparison, ordering, and report paths.
  - [x] Verify deterministic sealing and fail-closed mutation behavior for definitions, samples, bindings, timestamps, and unsafe inputs.
  - [x] Run the full contract/runtime suite and repository hygiene checks without AWS credentials, state, plans, network-dependent schema retrieval, or generated artifacts.

- [x] Register and document the package (AC: 10-13)
  - [x] Register every new schema and fixture in `contracts/manifest.json`, refresh exact raw-byte checksums and the release semantic-surface checksum.
  - [x] Add `docs/runbooks/pilot-measurement.md` covering inputs, ownership, redaction, retention, reruns, statuses, limitations, and Story 4.10 handoff.
  - [x] Document external launch-checklist gates without inventing jobs, owners, accounts, Regions, targets, windows, baselines, RPO/RTO, or approvers.
  - [x] Include rollback notes; this story creates no AWS resources.

### Review Findings

- [x] [Review][Patch] Define strict normalized evidence schemas [contracts/v1/schemas/pilot-measurement-evidence.schema.json:7-10] — `samples` accepts arbitrary objects, so consumers can accept malformed or unsafe evidence outside the Python validator.
- [x] [Review][Patch] Bind every source to the declared job and deployment context [scripts/pilot_measurement.py:244-297] — provenance omits job, workflow/run, account, Region, Environment, Deployment Identity, CONFIG, target manifest, and schedule-generation bindings.
- [x] [Review][Patch] Enforce baseline and pilot package roles [scripts/pilot_measurement.py:554-590] — a pilot sample can be supplied in the baseline package or a baseline sample in the pilot package.
- [x] [Review][Patch] Restrict inline evidence to explicit synthetic fixtures [scripts/pilot_measurement.py:266-269] — ordinary pilot packages can use `inline://` references with caller-asserted checksums and no source-byte verification.
- [x] [Review][Patch] Validate exact-generation readiness evidence [scripts/pilot_measurement.py:494-513] — control adoption trusts `result: "passed"` and a hash without validating generation, required controls, Deployment Identity, CONFIG, target manifest, or existing readiness evidence.
- [x] [Review][Patch] Honor declared metric event definitions and first-success semantics [scripts/pilot_measurement.py:610-618,660-664] — calculations hard-code event kinds and select the latest success, ignoring each metric’s declared start/stop events and the first successful deployment requirement.
- [x] [Review][Patch] Emit all required setup-effort categories [scripts/pilot_measurement.py:650-658] — only active engineering effort is calculated; review, approval wait, deployment wait, unrelated interruption, and total active effort are not emitted as metrics.
- [x] [Review][Patch] Preserve all reliability outcomes and denominators [scripts/pilot_measurement.py:722-749] — false/lost alerts, reruns, incidents, exclusions, and unresolved evidence are accepted but discarded from the result.
- [x] [Review][Patch] Preserve incomplete baseline status [scripts/pilot_measurement.py:819-826] — an incomplete baseline is downgraded to `UNKNOWN`, conflating absent evidence with incomplete evidence.
- [x] [Review][Patch] Return metric-level statuses for contradictory or stale evidence [scripts/pilot_measurement.py:545-594] — duplicate, contradictory, stale, and outside-window packages hard-fail before emitting the required `INCOMPLETE`, `INCONCLUSIVE`, or exact limitation result.
- [x] [Review][Patch] Enforce event, effort, qualitative, and provenance window containment [scripts/pilot_measurement.py:300-340,514-532,584-587] — only sample windows are checked, allowing out-of-window records to affect measurements.
- [x] [Review][Patch] Seal input package and source-reference checksums [scripts/pilot_measurement.py:860-880] — output contains only the definition checksum and sample IDs, so reviewers cannot identify the exact baseline, pilot, or source bytes used.
- [x] [Review][Patch] Evaluate baseline-to-pilot reduction targets [scripts/pilot_measurement.py:766-779,819-823] — comparison checks only the pilot value against its target and never evaluates the required baseline reduction.
- [x] [Review][Patch] Enforce supported comparability dimensions and population weighting [scripts/pilot_measurement.py:205-213,782-796] — unknown dimensions raise `KeyError`, while unequal stratum multiplicities can pass comparability without a weighting rule.
- [x] [Review][Patch] Reject unsafe artifact content and path classes [scripts/run_pilot_measurement.py:47-83] — policy checks narrow filenames only and does not reject unsafe directory components, common plan/log names, or prohibited content in generically named source files.
- [x] [Review][Patch] Prevent CLI input/output collisions [scripts/run_pilot_measurement.py:102-107] — output or report paths can overwrite input evidence or collide with each other, destroying rerun inputs or producing mixed-format output.
- [x] [Review][Patch] Escape reviewer-report Markdown fields [scripts/pilot_measurement.py:80-85,883-897] — metric identifiers permit newlines and table delimiters that can inject rows or arbitrary report content.
- [x] [Review][Patch] Canonicalize nested evidence collections [scripts/pilot_measurement.py:805-808,523-535] — source references and other nested records are not normalized by stable IDs before sealing or reporting.

## Dev Notes

### Scope and non-goals

- This story automates measurement and evidence packaging. It does not select pilot jobs, execute a real pilot, deploy AWS resources, query live AWS, decide rollout acceptance, or publish an `ACCEPTED` decision.
- Story 4.10 consumes the machine-readable result and reviewer report. The report may say target met/missed/inconclusive, but it must not approve launch or standardization.
- The external baseline estimate of one-to-three engineering days is an assumption to be replaced by measured data; it is never a fallback numeric sample.
- No Terraform change is expected. If implementation discovers a necessary infrastructure change, preserve resource addresses, add explicit owner/tags/logs/alarms/rollback notes, and stop to document the deviation before expanding scope.

### Metric contract and calculation guardrails

- Every duration uses aware UTC RFC 3339 timestamps and explicit start/stop event IDs. Use Python 3.14 timezone-aware datetimes; reject naive local time and future timestamps outside the declared clock-skew policy.
- Active effort categories are mutually exclusive by event interval. Review effort, approval wait, deployment wait, and unrelated interruption are reported separately from active setup effort and total elapsed lead time; overlapping intervals must be rejected or explicitly attributed once.
- Define median and any percentile behavior in the measurement definition. For small samples, publish sample size and uncertainty/limitation rather than implying statistical confidence.
- Control adoption is a per-pilot/per-generation matrix, not a count of passing fields. Missing exact-generation readiness evidence is `UNKNOWN` or `BLOCKED`, never a failed control silently omitted from the denominator.
- Reliability rates require visible denominator and exclusion lists. A zero-occurrence window, duplicate record, contradictory terminal state, lost alert, or unresolved recovery item must not disappear through aggregation.
- Qualitative data is summarized only as attributed categorical evidence with collection date and role; do not store names, free-form sensitive text, application payloads, or personal identifiers.

### Evidence and provenance guardrails

- Use the existing RFC 8785 canonicalization and SHA-256 conventions. Seal the normalized definition, source-reference manifest, normalized samples, metric results, limitations, and tool/calculation versions; preserve raw source checksums without copying unsafe raw artifacts into the published package.
- A source checksum proves bytes, not truth. Every source must also carry provenance: owner, repository/job, source revision, workflow/run or approved external record, environment/account/Region, observation window, and sensitivity classification.
- Source records must be bound to one declared pilot/job/generation/window. Cross-job, cross-revision, cross-account, cross-Region, or cross-window mixing is a hard failure unless the definition explicitly declares a comparable population and records the join rule.
- Use the prior stories’ fail-closed lessons: never trust caller-supplied result flags, counts, paths, timestamps, or “complete” claims without validating their typed evidence and bindings. Do not treat synthetic fixtures as live attestation.
- If evidence is stored or transported through S3 in a future integration, use object SHA-256 checksums and verify them on read; do not rely on ETags for whole-object identity, especially for multipart objects. See the AWS S3 integrity guidance in References.

### Existing code and file boundaries

- Extend the existing `scripts/` contract-validation style and `tests/contract/` fixture-driven style. Keep the measurement engine pure and credential-free so it can run in pull-request CI.
- Reuse identity and readiness validators rather than parsing Terraform state or inventing a second deployment model. Read source evidence through bounded, allowlisted artifact roots.
- Normative contracts belong in `contracts/v1/schemas/`; scenario vectors belong in `contracts/v1/fixtures/`; package registration belongs in `contracts/manifest.json` and, if semantic surface changes, `contracts/releases/1.0.0.json`/release notes according to existing release rules.
- Documentation belongs under `docs/runbooks/` or the existing project documentation structure. Do not place generated reports, raw plans, state, credentials, or local caches in the repository.

### AWS/Terraform implementation standard acceptance criteria

- No new AWS resource is authorized by this story. Any proposed AWS/Terraform addition must use the existing module ownership boundary, predictable names, required tags, encryption, least-privilege IAM, explicit validation, and stable resource addresses.
- Any artifact-store integration must define retention, access control, redaction, checksum verification, failure handling, and rollback; it must not publish secrets, raw plans, state, unrestricted logs, or unnecessary application data.
- CI validation must cover affected roots/examples with `terraform fmt -check`, `terraform validate`, and the repository IaC security scan if Terraform changes are introduced. Existing provider/deprecation warnings must not be reclassified as successful validation failures.
- Operational documentation must state logs/metrics/alarms and ownership for any production component added. This story’s default is no production component and no live measurement side effect.

### Previous story intelligence

Story 4.8 (`64fb792`) hardened recovery evidence and introduced strict fixture-only recovery qualification. Reuse its patterns: exact bindings, source-run provenance, explicit inventory records, per-control evidence, sanitization allowlists, freshness, immutable image references, and separation between credential-free evaluation and protected/live qualification. Do not create another checksum or readiness projection format.

Story 4.7 and Stories 4.4–4.6 established protected qualification workflows, release/target bindings, negative fixtures, cleanup inventories, and readiness category projections. Measurement must consume those outputs, not re-evaluate AWS authorization or infer control success from aggregate workflow status.

### Git and toolchain intelligence

- Current baseline commit: `64fb792` (`Harden recovery and security qualification`).
- Recent implementation uses Python 3.14.6, uv `0.11.29`, Terraform `1.15.8`, AWS provider `6.54.0`, Ruff `0.15.21`, mypy `2.3.0`, pytest `9.1.1`, and Checkov `3.3.8`; preserve the pinned matrix.
- Recent validation pattern: focused contract tests first, then `pytest tests runtime -q -p no:cacheprovider`, Ruff format/lint, mypy, `git diff --check`, Terraform formatting/validation for affected roots, security scan, and `./scripts/validate.sh`.

### Latest technical specifics

- GitHub artifact attestations establish provenance but must be verified to provide security value; do not treat an uploaded report name or checksum alone as proof of workflow provenance. See [GitHub artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations).
- If future evidence packaging uses S3, SHA-256 checksums can be supplied and verified for object integrity; ETags are not a reliable whole-object checksum for multipart objects. See [Amazon S3 object integrity](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity.html).
- Use aware UTC timestamps and `datetime.now(UTC)`/equivalent rather than naive `utcnow()`; see [Python 3.14 datetime guidance](https://docs.python.org/3.14/library/datetime.html).

## References

- [Epic 4 Story 4.9](/Users/srudyka/slower/demo-bmad/_bmad-output/planning-artifacts/epics.md:2882)
- [Epic 4 context and implementation notes](/Users/srudyka/slower/demo-bmad/_bmad-output/planning-artifacts/epics.md:2344)
- [PRD success metrics](/Users/srudyka/slower/demo-bmad/_bmad-output/planning-artifacts/prds/prd-demo-bmad-2026-07-13/prd.md:432)
- [PRD rollout and pilot gates](/Users/srudyka/slower/demo-bmad/_bmad-output/planning-artifacts/prds/prd-demo-bmad-2026-07-13/prd.md:455)
- [Architecture production evidence gate, AD-22](/Users/srudyka/slower/demo-bmad/_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md:198)
- [Architecture immutable supply chain, AD-17](/Users/srudyka/slower/demo-bmad/_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md:168)
- [Architecture conventions and toolchain](/Users/srudyka/slower/demo-bmad/_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md:246)
- [Project context](/Users/srudyka/slower/demo-bmad/_bmad-output/project-context.md)
- [AWS Terraform implementation standard](/Users/srudyka/slower/demo-bmad/_bmad/custom/standards/aws-terraform-implementation.md)
- [Compatibility Package README](/Users/srudyka/slower/demo-bmad/contracts/README.md)
- [Production readiness schema](/Users/srudyka/slower/demo-bmad/contracts/v1/schemas/production-readiness-decision.schema.json)
- [Deployment Identity schema](/Users/srudyka/slower/demo-bmad/contracts/v1/schemas/deployment-identity.schema.json)
- [Readiness gate](/Users/srudyka/slower/demo-bmad/scripts/readiness_gate.py)
- [Deployment evidence and identity helpers](/Users/srudyka/slower/demo-bmad/scripts/deployment_evidence.py)
- [Release manifest and checksum rules](/Users/srudyka/slower/demo-bmad/scripts/release_manifest.py)
- [Story 4.8 implementation context](/Users/srudyka/slower/demo-bmad/_bmad-output/implementation-artifacts/4-8-rehearse-job-and-cell-recovery.md)
- [Story 4.7 implementation context](/Users/srudyka/slower/demo-bmad/_bmad-output/implementation-artifacts/4-7-prove-security-and-delivery-boundaries.md)
- [GitHub artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)
- [Amazon S3 object integrity and SHA-256 checksums](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity.html)
- [Python 3.14 aware datetime guidance](https://docs.python.org/3.14/library/datetime.html)

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

- Focused and full tests passed; repository validation reached the existing `modules/ecs-scheduled-job-platform` Terraform validation failure caused by undeclared `evidence_normalizer_ecs`, `evidence_normalizer_deadline`, and `materializer_normalizer` Lambda references. No Terraform files were changed by Story 4.9.

### Implementation Plan

- Define a strict, credential-free pilot measurement input/output contract with exact bindings, typed source references, deterministic status semantics, and RFC 8785 sealing.
- Implement pure normalization and calculations for setup effort, control adoption, reliability, alert latency, recovery, qualitative findings, and baseline comparison.
- Add the CLI, sanitized artifact-root handling, machine-readable result, reviewer report, synthetic fixture catalog, contract tests, package registration, and runbook.
- Validate focused tests, full tests/runtime, Ruff, mypy, repository hygiene, and the existing repository validation path.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Loaded project context, AWS Terraform standard, full sprint status, Epic 4, Story 4.8, Story 4.7, architecture spine, PRD pilot metrics/rollout sections, existing evidence/readiness/release helpers, recent commits, and current official artifact/checksum/time guidance.
- No real pilot jobs, owners, accounts, Regions, notification targets, observation windows, approvals, AWS resources, credentials, Terraform state, plans, or production evidence were invented or used.
- Implemented strict credential-free measurement schemas, deterministic RFC 8785/SHA-256 sealing, typed metric/status handling, comparability checks, deployment/source bindings, unsafe artifact rejection, CLI output, fixture catalog, contract tests, manifest/release registration, and operational runbook.
- Validation: 420 tests and 373 subtests passed after review patches; focused contract checks (32 tests), Ruff, mypy, and `git diff --check` passed. `./scripts/validate.sh` passed through earlier checks but remains red only on the pre-existing Terraform undeclared-resource errors above.

### File List

- `_bmad-output/implementation-artifacts/4-9-automate-pilot-measurement-and-evidence-packaging.md`
- `scripts/pilot_measurement.py`
- `scripts/run_pilot_measurement.py`
- `contracts/v1/schemas/pilot-measurement-definition.schema.json`
- `contracts/v1/schemas/pilot-measurement-evidence.schema.json`
- `contracts/v1/schemas/pilot-measurement-result.schema.json`
- `contracts/v1/fixtures/pilot-measurement/cases.json`
- `tests/contract/test_pilot_measurement.py`
- `tests/contract/test_contract_schemas.py`
- `contracts/manifest.json`
- `contracts/releases/1.0.0.json`
- `docs/runbooks/pilot-measurement.md`

### Change Log

- 2026-08-03: Implemented deterministic pilot measurement, evidence packaging, contract registration, tests, and runbook; moved story to review.
- 2026-08-03: Applied all code-review patches and moved story to done.
