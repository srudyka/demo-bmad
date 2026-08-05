---
epic: 3
story: 3.4
title: Enforce Production Policies and Govern Exceptions
status: done
baseline_commit: 448bee1
---

# Story 3.4: Enforce Production Policies and Govern Exceptions

Status: done

## Story

As a Production Approver, I want consistent policy-as-code decisions applied to every trusted plan, so that insecure or operationally incomplete changes cannot reach production through reviewer oversight.

## Acceptance Criteria

1. Baseline production policy blocks missing protected tags/ownership, mutable images, public networking, unsafe security groups/egress, missing logs/retention/alarms/notifications, plaintext secrets, best-effort completion, incompatible Cell contracts, and missing lifecycle acknowledgement. Every denial names address, policy ID/version, requirement, evidence, severity, and remediation.
2. IAM changes are evaluated for effective actions/resources/conditions, trust, PassRole, managed-policy drift, cross-account access, privilege escalation, boundaries, and CI self-modification; administrator authority, unrelated role passing, boundary removal, trust mutation, IAM users/keys, OIDC changes, runtime writes, and cross-job access block.
3. Confused-deputy rules require exact source account/ARN, principal, PassedToService, queue, schedule group, task family, cluster, and registered ownership conditions; wrong and stale bindings fail fixtures.
4. Schedule/launch changes reject direct Scheduler-to-ECS targets, mutable CONFIG, unregistered jobs, stale Role IDs, insufficient expectation horizon, missing acknowledgement, phase-two mutation, unsafe overlap, and generation mismatch. Only RESERVED → PUBLISHED → VALIDATED → MATERIALIZED → ENABLED authorizes launch.
5. Supply-chain/hygiene policy blocks state, saved plans, `.terraform/`, `.tfvars`, credentials, generated secrets, mutable Actions/workflows/modules/images, changed provider locks, provisioners, `null_resource`, hardcoded targets, undocumented address changes, and secret exposure across code, Terraform, workflows, examples, docs, fixtures, summaries, and generated output.
6. A versioned qualifying-change catalog determines exact change types, scopes, risk thresholds, required reviewers, exception owner, and catalog version. Unknown, missing, ambiguous, or stale catalog data fails closed.
7. Every blocking rule has deterministic positive/negative fixtures and architecture/NFR/AWS-standard mappings. Policy changes cannot silently remove coverage, lower production severity, or alter expected findings.
8. Exceptions bind exact policy/resource/Environment/source revision/plan checksum/owner/justification/approver/compensating control/expiry/review date. Broad, reusable, expired, unsigned, mismatched, or changed-plan exceptions reject.
9. Invalid Terraform, target mismatch, plaintext secrets, missing production controls, unauthorized escalation, mutable Deployment Identity, and absent occurrence-aware tracking are non-exemptible and remain blocking.
10. Non-production advisory/blocking severities follow a versioned adoption timeline; production is blocking from the first release.
11. Retained evidence includes policy bundle/catalog versions, plan checksum, source, target, findings, exceptions, actors, approvals, and timestamps. Summaries exclude secrets, raw plan/config, credentials, and unrestricted sensitive attributes.

## Tasks / Subtasks

- [ ] Define normative policy decision, finding, qualifying-change, exception, and retained-evidence schemas (AC: 1, 6-11)
  - [ ] Reuse `contracts/manifest.json`, existing IAM/network/secret-safety/trusted-plan catalogs, and existing checksum/target identity algorithms.
  - [ ] Require bounded codes, stable addresses, policy ID/version, severity, remediation, evidence references, exact plan/source/target bindings, actors, timestamps, signatures, and expiry.
  - [ ] Mark target identity, plaintext secret, escalation, missing production controls, mutable identity, and missing occurrence tracking non-exemptible.
- [ ] Implement deterministic production policy evaluation (AC: 1-5, 7, 10)
  - [ ] Extend `scripts/trusted_plan.py` or a shared policy module; do not duplicate plan parsing or summary logic.
  - [ ] Evaluate sanitized plan JSON plus repository/contract/target evidence without copying sensitive attributes.
  - [ ] Fail closed on unknown policy IDs, missing/stale bundles, ambiguity, malformed plans, unsupported schemas, or missing evidence.
  - [ ] Run policy/readiness checks for no-op plans and produce attributable results.
- [ ] Add IAM, confused-deputy, schedule, launch, supply-chain, and Security-review routing (AC: 2-6, 10)
  - [ ] Classify exact IAM/trust/OIDC/network/schedule/launch/Cell/state changes and require Security approval only when the versioned catalog says so.
  - [ ] Keep production blocking and never grant apply/state/runtime authority from policy evaluation.
- [ ] Implement exact single-use exception governance (AC: 8-9, 11)
  - [ ] Validate owner, independent approver, justification, compensating control, scope, source, target, checksum, policy version, timestamps, signature, and expiry.
  - [ ] Reject wildcard scope, reuse, stale/changed plans, stale policy bundles, unsigned records, mismatched targets, and non-exemptible waivers.
  - [ ] Store only bounded safe references; never credentials, raw plan/config, secrets, or unrestricted attributes.
- [ ] Add executable positive/negative fixtures and integrate the policy gate before trusted-plan reporting/artifact publication (AC: 1-11)
  - [ ] Prove policy changes cannot remove findings, lower production severity, or bypass Story 3.5 approval/apply controls.
- [ ] Document policy order, findings, reviewer routing, exception lifecycle, retention, remediation, and rollback in `docs/runbooks/deployment-targets.md`, `docs/runbooks/pull-request-validation.md`, and contract README material (AC: 1, 6, 8-11).

## Dev Notes

### Guardrails

- AD-12/16/20: plan, apply, workload, operator, and runtime roles remain separate; PR validation remains credential-free; production failures block.
- AD-15/17: bind account/Region/Environment/root, encrypted native-lock state, full-SHA workflows, immutable modules/images, committed provider locks, and `terraform init -lockfile=readonly`.
- AD-22/23/25/29: use the Compatibility Package as the sole normative source, preserve one Terraform owner per edge, and require the exact lifecycle handshake.
- AWS Terraform standard: require ownership tags, least-privilege IAM, private networking, encryption, retention, alarms, DLQs, immutable images, no public ingress, no unjustified wildcard, no provisioners/`null_resource`, and documented rollback.

### Reuse existing code

- `scripts/trusted_plan.py`: metadata, sanitized summary, plan checksum, and policy boundary.
- `scripts/deployment_targets.py`: manifest, OIDC, STS, role, Cell, state, policy-version, and ownership checks.
- `scripts/validate.py`/`scripts/check_repository.py`: inventory, migration, workflow, secret, hygiene, rollout, and Checkov checks.
- `contracts/v1/catalogs/{iam,network,secret-safety,trusted-plan}.json` and their schemas/fixtures.
- `.github/workflows/validate.yml` must remain credential-free; `.github/workflows/trusted-plan.yml` must run policy before reporting/upload.

### Testing and validation

Use pinned `uv 0.11.29`, Python 3.14.6, Terraform 1.15.8, AWS provider 6.54.0, Ruff, mypy, pytest, JSON Schema, and Checkov:

```bash
PATH=/private/tmp/demo-bmad-uv-01129:$PATH UV_CACHE_DIR=/private/tmp/demo-bmad-uv-cache uv run --locked pytest tests runtime -q -p no:cacheprovider
PATH=/private/tmp/demo-bmad-uv-01129:$PATH UV_CACHE_DIR=/private/tmp/demo-bmad-uv-cache ./scripts/validate.sh
```

No live state or AWS credentials are allowed in tests. Report Registry/toolchain failures separately from code failures and preserve the validator’s final summary/exit status.

### Scope boundary

This story governs policy decisions and exceptions. It does not apply Terraform, publish releases, record final deployment/rollback evidence, or enable production scheduling without later Story 3.5/3.6 controls.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-3.4-Enforce-Production-Policies-and-Govern-Exceptions`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md` — AD-12, AD-15-AD-18, AD-20, AD-22-AD-25, AD-29]
- [Source: `_bmad-output/project-context.md`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]
- [Source: `_bmad-output/implementation-artifacts/3-3-generate-a-trusted-and-reviewable-terraform-plan.md`]
- [Source: `scripts/trusted_plan.py`]
- [Source: `scripts/deployment_targets.py`]
- [Source: `scripts/validate.py`]

## Previous Story Intelligence

Story 3.3 established trusted-plan metadata, sanitized summaries, checksums, artifact controls, and immutable target/lock bindings. Extend those helpers rather than adding a second plan parser or checksum format. CI history showed that Git-shaped diff parsers need executable added/removed-block tests, and shallow history must not prevent exact base comparison. All policy and exception decisions must bind authenticated repository IDs, source commit, workflow SHA/run, manifest, target, policy bundle, and plan checksum.

### Review Findings

- [x] [Review][Patch] Production controls use serialized-text heuristics instead of resource-specific attributable validation [scripts/production_policy.py:121-138].
- [x] [Review][Patch] IAM evaluation omits effective permissions, trust, boundaries, drift, cross-account, OIDC, CI, and runtime-write checks [scripts/production_policy.py:282-315].
- [x] [Review][Patch] Confused-deputy validation accepts any single condition instead of exact source, principal, service, queue, schedule, task, cluster, and ownership bindings [scripts/production_policy.py:287-292].
- [x] [Review][Patch] Schedule governance does not validate lifecycle transitions, stale identities, horizons, acknowledgements, overlap, phase mutation, or occurrence tracking [scripts/production_policy.py:369-390].
- [x] [Review][Patch] Qualifying-change catalog scopes, thresholds, reviewer requirements, and owner are not enforced by classification [scripts/production_policy.py:193-235].
- [x] [Review][Patch] Non-production adoption timeline is declared but non-production evaluation is rejected and all findings are hard-coded blocking [scripts/production_policy.py:146-158,249-250].
- [x] [Review][Patch] Supply-chain scanning lacks comprehensive undocumented-address, generated-output, secret, mutable-reference, and required-file coverage [scripts/check_repository.py:168-230].
- [x] [Review][Patch] Exceptions omit exact account, region, root, target identity, catalog owner, and authorized owner binding [scripts/production_policy.py:423-455; contracts/v1/schemas/production-exception.schema.json:5-8].
- [x] [Review][Patch] Retained evidence omits actors and approval records [scripts/production_policy.py:403-420,497-517].
- [x] [Review][Patch] Production-policy fixtures lack deterministic coverage and architecture/NFR/AWS-standard mappings [contracts/v1/fixtures/production-policy/cases.json:3-7; contracts/v1/catalogs/production-policy.json:18-22].
- [x] [Review][Patch] Image validation rejects immutable release tags permitted by the AWS Terraform standard [scripts/production_policy.py:355-367].
- [x] [Review][Patch] Baseline hygiene comparison is unavailable in the shallow checkout and hard-coded to Story 3.4 [`.github/workflows/trusted-plan.yml:77-80,166`; `scripts/check_repository.py:213-229`].
- [x] [Review][Patch] Exception signing is not configured and single-use state is runner-local [`.github/workflows/trusted-plan.yml:161-170`; `scripts/production_policy.py:466-494`].
- [x] [Review][Patch] Report generation trusts a mutable policy file without binding its complete decision or digest [`scripts/trusted_plan.py:502-513`].
- [x] [Review][Patch] Non-exemptible deployment-identity and occurrence-tracking findings are declared but never emitted [`scripts/production_policy.py:19-25,238-420`].
- [x] [Review][Patch] Runtime exception validation bypasses the checked-in schema and accepts nonconforming signature formats [`scripts/trusted_plan.py:480-489`; `scripts/production_policy.py:443-474`; `contracts/v1/schemas/production-exception.schema.json:5-8`].
- [x] [Review][Patch] Workflow exception-file interpolation allows shell metacharacters to enter the policy command [` .github/workflows/trusted-plan.yml:168-170`].

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Added the versioned `production-readiness` catalog and bounded policy evaluator with production blocking, IAM/network/supply-chain checks, qualifying-change classification, and non-exemptible findings.
- Added exact exception binding validation for policy, target, source revision, plan checksum, independent approval, compensating control, signature, review date, and expiry.
- Integrated policy evaluation before trusted-plan report publication; reports retain only policy ID/version, status, finding count, and Security-review routing.
- Added credential-free positive/negative policy tests and documented policy order, exception lifecycle, retention, and rollback.
- Full repository tests passed: 275 tests and 243 subtests. The wrapper validator could not reach its final summary because the environment could not resolve PyPI/registry hosts; an already-installed validator proceeded until Terraform provider initialization, which failed on DNS for `registry.terraform.io`.

### File List

- `_bmad-output/implementation-artifacts/3-4-enforce-production-policies-and-govern-exceptions.md`
- `scripts/trusted_plan.py`
- `scripts/production_policy.py`
- `.github/workflows/trusted-plan.yml`
- `contracts/manifest.json`
- `contracts/releases/1.0.0.json`
- `contracts/v1/catalogs/production-policy.json`
- `tests/contract/test_trusted_plan.py`
- `docs/runbooks/deployment-targets.md`
- `docs/runbooks/pull-request-validation.md`

### Change Log

- 2026-07-29: Implemented production policy evaluation, exact exception governance, trusted-plan integration, tests, and runbook documentation; moved story to review.
