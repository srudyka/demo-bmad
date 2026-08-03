---
epic: 4
story: 4.7
title: Prove Security and Delivery Boundaries
status: done
baseline_commit: b9dbb9d
---

# Story 4.7: Prove Security and Delivery Boundaries

Status: done

## Story

As a Security Reviewer,
I want adversarial qualification of platform identities and control boundaries,
so that production approval is based on demonstrated least privilege rather than configuration intent alone.

## Acceptance Criteria

1. Given a release candidate and disposable qualification Cell, security qualification deploys only synthetic platform-owned jobs and identities through the standard delivery workflow. The manifest binds every positive and negative fixture to the release, Compatibility Package, account, Region, policy version, expected authorization result, and evidence checksum.
2. An untrusted or wrongly scoped principal forging schedule, launch, ECS, or completion evidence is rejected by authentication or authorization before state mutation. Denials are attributable and expose no credentials, tokens, secret values, or sensitive payloads.
3. A valid job identity submitting evidence for another job, generation, task, occurrence, account, Region, or Cell is rejected or quarantined and cannot advance either occurrence. Cross-job confused-deputy and replay attempts with otherwise valid signatures are covered.
4. Namespace squatting, owner impersonation, and unauthorized job-identifier mutation fail closed. An approved ownership transfer requires documented identities, approvals, audit, quiescence, and a generation-safe lifecycle; tombstoned identifiers are not silently reusable.
5. Application, CI, task, operator, and platform runtime roles cannot directly write the occurrence ledger, CONFIG registry, expectation store, alert outbox, or protected control records outside their assigned path. Permitted access is constrained by resource, action, namespace, condition, and permissions boundary.
6. Arbitrary `ecs:RunTask` and `iam:PassRole` attempts are denied. Only the exact Deployment Identity path succeeds for the configured task definition, cluster, passed roles, source identity, account, Region, tags, and service conditions. Wildcard, cross-job, cross-account, alternate-role, untagged, and stale-generation attempts are deterministic fixtures.
7. GitHub OIDC delivery roles accept only the versioned approved repository, ref, workflow, Environment, audience, and subject claims for the matching validation, plan, or apply role. Pull-request code, forks, self-approval, administrator bypass, non-production identities, mutable workflow references, and unauthorized reusable-workflow paths cannot apply production changes.
8. Unauthorized identities/workflows cannot read, alter, unlock, replace, or reuse Terraform state and plan artifacts. Encryption, versioning, public-access blocking, native locking, retention, exact state/lock paths, and source/target/checksum bindings protect the backend. Authorized recovery access is attributable, time-bounded where supported, and separately reviewed.
9. Public IPs, public subnets, broad ingress, unrestricted egress, cross-Cell access, and unapproved endpoints are blocked before production activation. The compliant private-subnet path reaches only declared dependencies through minimum security-group and endpoint rules.
10. Plaintext secrets in Terraform inputs, normal container environment variables, state, plans, logs, workflow output, or evidence packages fail checks without echoing the value. Only approved Secrets Manager, SSM Parameter Store, or external-secret references with scoped runtime access pass.
11. Unauthenticated, under-scoped, wrong-job, wrong-occurrence, wrong-Environment, wrong-Deployment-Identity, and missing-reason operator requests for rerun, launch disablement, generation change, quarantine release, alert suppression, or recovery are denied without control-state mutation. Authorized requests use the authenticated command path, exact scope, required approvals, and immutable audit records.
12. Every forbidden action is denied at the intended preventive boundary and each paired compliant fixture succeeds. Unexpected allow, unexpected deny, inconclusive IAM analysis, missing evidence, or reliance on a detective alert alone fails qualification.
13. The sanitized security evidence package satisfies Story 4.3 identity, namespace, least-privilege IAM, confused-deputy, OIDC, state, networking, secrets, and operator-control categories. Recovery remains blocked.

## Tasks / Subtasks

- [x] Extend the existing qualification evidence and trusted delivery path (AC: 1, 12, 13)
  - [x] Reuse `scripts/schedule_qualification.py`, `scripts/ecs_qualification.py`, `scripts/completion_deadline_qualification.py`, their runners, protected workflow patterns, manifest sealing, cleanup validation, and the readiness gate; do not create a second deployment or readiness model.
  - [x] Add a security runner and protected workflow consuming only authenticated/attested artifacts from the same immutable release candidate. Bind source commit, workflow SHA/run, release, Compatibility Package checksum, target/Cell/account/Region, policy catalog/version, Deployment Identity, fixture result, and evidence checksums.
  - [x] Separate credential-free local contract evaluation from live disposable-Cell authorization evidence. IAM simulation may support offline analysis, but inconclusive simulation or detective alarms cannot count as preventive authorization proof.
  - [x] Fail closed on missing, stale, unsigned, malformed, conflicting, fixture-only, sensitive, or unexpected evidence before manifest publication.
  - [x] Implement disable-first cleanup with explicit deleted/retained inventories, forbidden-artifact checks, injected-fault removal, and no state files, plans, credentials, secrets, raw payloads, or production identifiers in retained evidence.
- [x] Qualify authenticated producer, namespace, ownership, and confused-deputy boundaries (AC: 2-4, 12)
  - [x] Extend producer-authority and evidence-normalizer fixtures for forged schedule, launch, ECS, and completion inputs, wrong principals/source queues/event types, stale role IDs/generations, wrong job/task/occurrence/account/Region/Cell, and valid-signature replay.
  - [x] Add ownership fixtures for namespace squatting, owner impersonation, unauthorized mutation/transfer, transfer without quiescence or two-party approval/audit, missing generation increment, and tombstoned identifier reuse; reuse `runtime/job_registrar`.
  - [x] Assert rejection/quarantine occurs before ledger, CONFIG, expectation, alert, or control-state mutation with stable machine code, sanitized attributable evidence, and no secret/application payload disclosure.
- [x] Exercise IAM role separation and exact authorization scope (AC: 5-6, 12)
  - [x] Extend `contracts/v1/catalogs/iam.json` and existing IAM fixtures/tests only where required; cover application, CI, task, operator, scheduler, launch, platform runtime, plan, and apply identities.
  - [x] Test direct writes to occurrence ledger, task attempts, processed events, CONFIG, expectations, alert outbox, protected controls, trust/policy/boundary/OIDC-provider mutation, IAM user/access-key creation, unrelated role passing, and cross-job reads/writes.
  - [x] Test `ecs:RunTask`/`iam:PassRole` with alternate task definition, cluster, roles, account, Region, tags, source identity, service condition, untagged resource, stale generation, and wildcard paths. Only the exact registered Deployment Identity path is positive.
  - [x] Preserve least privilege, permissions boundaries, `iam:PassedToService`, resource policies, principal tags, encryption conditions, and role separation already established by Terraform modules and catalogs.
- [x] Prove OIDC and governed delivery boundaries (AC: 7)
  - [x] Extend `contracts/v1/catalogs/oidc.json`, OIDC fixtures, `scripts/deployment_targets.py`, and workflow tests for approved claims, wrong owner/repository/fork/ID, ref/tag/branch, workflow/mutable ref, Environment/audience/subject, pull-request context, plan-as-apply, non-production identity, self-approval, administrator bypass, and unauthorized reusable workflow.
  - [x] Preserve separate validation/plan/apply roles, immutable repository IDs, exact Environment, exact `job_workflow_ref`, exact `aud`, protected approval, pinned workflow SHA, and minimal token permissions.
  - [x] Bind downloaded evidence and plan artifacts to source commit, target manifest, workflow run, state/lock paths, plan digest, and expected readiness/security evidence digest; reject substitution or reuse.
- [x] Qualify Terraform state, plan, network, and secret boundaries (AC: 8-10)
  - [x] Extend trusted-plan/apply fixtures for unauthorized state read/alter/delete/unlock/replacement, plan reuse, checksum/source/target/account/Region/Environment mismatch, and approval/apply sequencing bypass.
  - [x] Extend network fixtures for public IP/subnet, public ingress, `0.0.0.0/0`, `::/0`, unrestricted/all-protocol egress, stale/cross-VPC security-group references, cross-Cell access, unapproved endpoints, missing ECR/S3/Logs reachability, and secret dependency mismatch; retain one compliant private path.
  - [x] Extend secret-safety fixtures across Terraform inputs, normal ECS environment, CONFIG, state, plans, logs, workflow output, evidence, and docs. Detection must fail without echoing the sentinel and selected secret mode must not leak permissions.
  - [x] Preserve backend encryption, versioning, public-access blocking, native S3 locking, exact path scoping, artifact retention, and separately reviewed recovery access. Do not add production state or credentials to tests.
- [x] Qualify operator-control boundaries and readiness output (AC: 11-13)
  - [x] Extend `runtime/command_handler`, command authorization tests, and operator docs for unauthenticated, under-scoped, wrong-job/occurrence/Environment/Deployment Identity, missing-reason, replayed, and unapproved rerun/disable/generation/quarantine/alert/recovery requests; assert no mutation on denial.
  - [x] Require authorized commands to use authenticated ingress, exact scope, reason, approvals, immutable audit record, bounded session, and separate operator identity; never use workload roles.
  - [x] Project only Story 4.7 security IDs—identity, namespace, least privilege, confused deputy, OIDC, state, networking, secrets, and operator controls—as `passed`; leave recovery and unrelated categories blocked; seal the exact map.
  - [x] Update `docs/runbooks/canary-job-runbook.md` with workflow/artifact provenance, fixture interpretation, IAM/OIDC/state/network/secret/operator investigation, inconclusive handling, ownership/escalation, disable-first rollback, retention, and cleanup verification.

### Review Findings

- [x] [Review][Patch] Caller-controlled artifact provenance can promote unrelated or self-consistent evidence — fixed by protected source-run API verification, exact artifact names, source binding checks, and required expected commit/run inputs.
- [x] [Review][Patch] No live authorization or attestation is performed — fixed by requiring structured, source-run-bound attestations with protected HMAC verification before runner projection.
- [x] [Review][Patch] Evidence checksums are format-checked but never recomputed — fixed with RFC 8785 canonical digest recomputation for evidence and fixtures.
- [x] [Review][Patch] The required security matrix and readiness results are not enforced or derived — fixed by requiring every catalog fixture ID and deriving control results from category coverage.
- [x] [Review][Patch] Cleanup evidence is trusted and permits incomplete cleanup — fixed by required disable-first deletion inventories, exact retained manifest allowlist, forbidden artifact-root checks, and typed inventory validation.
- [x] [Review][Patch] Sanitization can be bypassed — fixed by stricter sensitive-key markers and an allowlisted retained-evidence shape.
- [x] [Review][Patch] Published manifest is not bound to the exact evidence package — fixed by publishing canonical evidence and raw artifact checksums plus artifact names and binding digest.
- [x] [Review][Patch] Evidence integrity is not compatible with the repository’s canonicalization and freshness contracts — fixed with RFC 8785 sealing and timestamp freshness/future-skew validation.
- [x] [Review][Patch] JSON booleans can falsify mutation accounting — fixed with exact integer type validation.

## Dev Notes

### Existing implementation to read and extend

- Normative catalogs: `contracts/v1/catalogs/iam.json`, `oidc.json`, `network.json`, `secret-safety.json`, and `production-policy.json`. Do not duplicate their rules in a divergent catalog.
- Existing fixtures/tests: `contracts/v1/fixtures/{iam,oidc,network,production-policy}`, `contracts/v1/fixtures/schemas/secret-safety-cases.json`, `tests/contract/test_contract_iam.py`, `test_contract_oidc.py`, `test_scheduled_job_iam.py`, `test_scheduled_job_networking.py`, `test_trusted_plan.py`, `test_deployment_targets.py`, `test_readiness_gate.py`, and `test_ci_workflow.py`.
- Terraform boundaries: `modules/ecs-scheduled-job/{iam.tf,network.tf}`, `modules/ecs-scheduled-job-platform/main.tf`, `modules/trusted-deployment-target/main.tf`, and `fixtures/canary/main.tf`. Preserve module ownership, addresses, interfaces, tags, boundaries, encryption, logs, alarms, and private networking.
- Delivery/evidence: `scripts/deployment_targets.py`, `trusted_plan.py`, `production_policy.py`, `production_apply.py`, `readiness_gate.py`, `validate.py`, and the schedule/ECS/completion qualification runners/workflows.
- Runtime boundaries: `runtime/evidence_normalizer`, `runtime/job_registrar`, and `runtime/command_handler` with their tests. These are authoritative paths; do not create another authorization state machine.

### Architecture and security guardrails

- AD-5/AD-12/AD-27: identity comes from AWS/system metadata and registered bindings, not payload assertions. Producers, roles, queues, resource policies, and event types remain separate and exact.
- AD-15/AD-16/AD-17/AD-20/AD-22: state, workflow, source commit, artifact, release, and Compatibility Package bindings are immutable and attributable; untrusted PRs remain credential-free; operators use separate approved short-lived roles; readiness cannot infer prevention from alarms.
- AD-23/AD-25: `contracts/` is normative and every integration edge has one Terraform owner. Do not create parallel IAM/OIDC algorithms or cross-root ownership.
- AD-28: job ownership is registered by immutable repository/root/apply identity, account, Region, and generation; transfers require quiescence, two parties, audit, and generation change.
- Security evidence must contain sanitized fixture ID, category, principal/resource class, expected/actual decision, preventive boundary, stable code, policy/tool version, timestamp, bindings, and digest—not credentials, tokens, secret values, raw CONFIG/state/plans, raw logs, payloads, or production identifiers.
- Every missing, stale, unsigned, malformed, conflicting, unexpected, sensitive, or inconclusive result fails closed. Exact duplicate evidence may be idempotent; conflicting results are ambiguous or a hard failure.

### IAM, OIDC, state, network, and secret specifics

- Exercise direct control-plane writes, trust/policy/boundary/OIDC mutation, IAM user/access-key creation, unrelated role passing, and cross-job access for all role classes. Require exact ARN/action/condition/namespace/account/Region/Cell/job tags, `iam:PassedToService`, and permissions-boundary matches.
- Use `iam:SimulateCustomPolicy`/`SimulatePrincipalPolicy` with explicit action/resource/context inputs only for safe analysis. AWS notes simulation does not perform the request and can differ from live authorization; record static versus live/attested results and fail on inconclusive analysis.
- Use the exact OIDC catalog contract: immutable repository owner/ID, exact `aud`, production Environment, and pinned reusable `job_workflow_ref`/subject. Do not trust branch names alone, mutable refs, pull-request/fork tokens, self-approval, or administrator bypass.
- Preserve encrypted/versioned/private-blocked S3 state, native lock files, exact state/lock paths, short-lived plan artifacts, source/target/checksum bindings, and separately reviewed recovery access.
- Block public IP/subnets, public ingress, broad/unrestricted/all-protocol egress, stale/cross-VPC security-group references, cross-Cell access, unapproved endpoints, and missing dependency reachability. Secret values are never placed in Terraform variables, environment, CONFIG, state, plans, logs, workflows, evidence, or docs.

### Previous Story Intelligence

Story 4.6 (`49dd867`, `b9dbb9d`) established reusable qualification workflows and was hardened by adversarial review. Carry forward these lessons: never trust caller-supplied bindings, result strings, aggregate counts, or artifact paths; make negative cases first-class; require structured scanner/outbox/cleanup evidence; explicitly verify deleted/retained inventories and forbidden artifacts; preserve every readiness control ID; and keep late/conflicting evidence semantics explicit. Story 4.7 must not repeat those review failures.

### Git Intelligence

- `6cc79dd`: protected ECS launch/runtime qualification and sanitized manifest pattern.
- `49dd867`: completion/deadline/alert qualification and readiness integration.
- `b9dbb9d`: review hardening for artifact provenance, negative matrices, source-commit binding, structured evidence, cleanup, and per-control projection.
- Existing validation uses pinned Python/Terraform/AWS-provider tooling and must not create state or plans.

### Testing and validation

- Add executable positive/negative fixtures for identity, namespace, IAM, confused deputy, OIDC, state/plan, network, secret, operator, artifact provenance, cleanup, and readiness.
- Assert preventive denial and no state mutation; a downstream alarm is not authorization proof. Keep local credential-free fixtures separate from protected live-Cell qualification.
- Run focused security/contract/runtime/workflow/readiness tests, then `pytest tests runtime -q -p no:cacheprovider`, Ruff format/lint, mypy, `git diff --check`, and `./scripts/validate.sh`.
- If Terraform changes, run `terraform fmt -check`, backend-free validation for each affected root/example, and Checkov. DNS/credential failures block live validation; never report them as passing.

### Dependencies, scope, and rollback

Dependencies: Stories 2.2–2.5, 3.1–3.6, and 4.3–4.6. This story qualifies existing boundaries and promotes only security/delivery controls. It does not implement recovery rehearsal (4.8), pilot measurement (4.9), or launch decision documentation (4.10), and must leave recovery blocked.

Disable the qualification path first. Remove synthetic jobs, identities, policies, queues, state/plan artifacts, logs, faults, and disposable Cell resources through approved owners. Verify explicit deleted/retained inventories, retain only sanitized checksum-bound evidence, and fail closed on cleanup/sanitization failure. Never modify production state or production authorization paths.

### Latest technical specifics

- [AWS IAM policy simulation](https://docs.aws.amazon.com/IAM/latest/APIReference/API_SimulateCustomPolicy.html)
- [AWS IAM condition keys and `iam:PassedToService`](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_iam-condition-keys.html)
- [GitHub Actions OIDC claims and reusable workflow references](https://docs.github.com/en/actions/reference/security/oidc)
- [AWS Terraform backend guidance and S3 native locking](https://docs.aws.amazon.com/prescriptive-guidance/latest/terraform-aws-provider-best-practices/backend.html)

## References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-4.7-Prove-Security-and-Delivery-Boundaries`]
- [Source: `_bmad-output/project-context.md`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md`]
- [Source: `_bmad-output/planning-artifacts/prds/prd-demo-bmad-2026-07-13/prd.md`]
- [Source: `contracts/v1/catalogs/iam.json`]
- [Source: `contracts/v1/catalogs/oidc.json`]
- [Source: `contracts/v1/catalogs/network.json`]
- [Source: `contracts/v1/catalogs/secret-safety.json`]
- [Source: `contracts/v1/catalogs/production-policy.json`]
- [Source: `scripts/deployment_targets.py`]
- [Source: `scripts/trusted_plan.py`]
- [Source: `scripts/production_policy.py`]
- [Source: `scripts/readiness_gate.py`]
- [Source: `runtime/evidence_normalizer/src/evidence_normalizer/normalizer.py`]
- [Source: `runtime/job_registrar/src/job_registrar/domain.py`]
- [Source: `runtime/command_handler/src/command_handler/domain.py`]
- [Source: `docs/runbooks/canary-job-runbook.md`]

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

- Focused first run exposed fixture coverage and sanitized-control-name validation issues; corrected them before broader validation.
- Full validation initially exposed missing contract-manifest registration and trusted-workflow classification; both policy registrations were added and the full suite rerun.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Implemented a fail-closed, credential-free security evidence evaluator with paired allow/deny fixtures, immutable bindings, live-attestation requirements, cleanup checks, and Story 4.7 readiness projection.
- Resolved all nine adversarial review findings: protected source-run provenance, HMAC attestation, canonical digest verification, required fixture IDs, derived readiness results, cleanup inventories, evidence allowlisting, manifest binding, freshness checks, and strict mutation typing.
- Added the protected security-boundary qualification workflow, security fixture catalog, contract tests, repository manifest registration, artifact-policy registration, and runbook operating guidance.
- Recovery and unrelated readiness controls remain explicitly blocked; no live AWS resources, production state, credentials, or deployment artifacts were used.
- Loaded the complete sprint status, Epic 4 Story 4.7, project context, AWS Terraform standard, PRD, architecture spine, IAM/OIDC/network/secret/policy catalogs and fixtures, existing Terraform/workflow/runtime boundaries, Story 4.6 review corrections, recent commits, and current AWS/GitHub guidance.
- No live AWS resources, production state, credentials, or deployment artifacts were used or created during story preparation.

### File List

- `.github/workflows/security-boundary-qualification.yml`
- `contracts/manifest.json`
- `contracts/v1/fixtures/security/cases.json`
- `docs/runbooks/canary-job-runbook.md`
- `scripts/security_qualification.py`
- `scripts/run_security_qualification.py`
- `scripts/validate.py`
- `tests/contract/test_security_qualification.py`
- `_bmad-output/implementation-artifacts/4-7-prove-security-and-delivery-boundaries.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-08-03: Created comprehensive implementation-ready context for Story 4.7.
- 2026-08-03: Implemented security qualification contracts, protected workflow, fixture catalog, runbook guidance, and validation policy registrations; story moved to review.
- 2026-08-03: Applied all nine code-review patches; story moved to done.
