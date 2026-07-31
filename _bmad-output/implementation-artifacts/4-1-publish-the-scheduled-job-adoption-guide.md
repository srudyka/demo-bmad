---
epic: 4
story: 4.1
title: Publish the Scheduled Job Adoption Guide
status: done
baseline_commit: d4b5096a6dddf61f6b9f1bdf53732af7a9f5416b
---

# Story 4.1: Publish the Scheduled Job Adoption Guide

## Story

As an Application Engineer,
I want a complete adoption guide and executable examples,
so that I can configure the platform without modifying module internals or reconstructing ECS operational controls.

## Acceptance Criteria

1. The repository README presents the adoption path in execution order: prerequisites, Cell discovery, reservation, IAM/network preparation, task integration, phase-one publication, Cell acknowledgement, materialization, activation, verification, ownership handoff, and production promotion. It describes Scheduler → Cell → ECS, never a direct Scheduler → ECS path.
2. Module documentation describes every required and optional input/output with type, default, validation, sensitivity, operational purpose, security implication, and an example. Required behavior must not depend on undocumented defaults or Terraform-state inspection.
3. Application guidance shows consumption of supplied job, Occurrence ID, CONFIG, attempt, task, and Deployment Identity values and structured start/success/failure records. It states that jobs never generate occurrence IDs and success requires an accepted marker plus zero essential-container exit.
4. Security and operations guidance covers separate roles, boundaries, effective-policy review, confused-deputy conditions, exact PassRole, secret modes, private networking, immutable images, OIDC, state isolation, protected Environments, idempotency, deadlines, overlap, alarms, reruns, disablement, two-phase schedule changes, evidence preservation, compensation, and Cell recovery. It prohibits direct RunTask, direct table/state edits, out-of-Terraform schedule mutation, and automatic cancellation.
5. The scheduled-job basic example remains a secret-free, backend-free non-production example using existing infrastructure inputs, immutable image references, required protected tags, retained logs, and documented outputs; it independently initializes and validates with no committed tfvars.
6. A clearly non-deployable production reference demonstrates private networking, immutable image, occurrence-aware completion, notification routing, required alarms, Runbook/readiness references, protected workflow, state isolation, and two-phase activation. It uses only placeholders for external identifiers and fails closed while launch-checklist values are unresolved.
7. Compatibility documentation distinguishes the permanent Terraform constraint (>= 1.10, < 2.0) from the dated tested Terraform 1.15.8, AWS provider 6.54.0, Python 3.14.6, and Fargate seeds, and explains supported Cell/module/contract/workflow compatibility.
8. Change guidance covers review classification, stable addresses or explicit moved migration, generation replacement, expected plan impact, Deployment Identity, verification, rollback, and application compensation for schedule, image, IAM, networking, secret, module-version, and address changes. It prohibits moving references, destructive replacement, or cleanup during rollback.
9. Documentation CI validates links, formatting, generated references, each example's Terraform validation, contract versions, policy scans, immutable pins, prohibited artifacts, and security assertions; insecure, contradictory, stale, non-executable, or secret-bearing guidance blocks release.

## Tasks / Subtasks

- [x] Create the adoption guide and repository navigation (AC: 1, 3-4, 7-8)
  - [x] Extend [README.md](../../README.md) with a concise, ordered adoption path and links to module references and Runbooks.
  - [x] Add an adoption guide under docs using the existing runbook/documentation structure; include application completion-record examples that are secret-safe and show values supplied by the platform.
  - [x] Cross-link [docs/runbooks/README.md](../../docs/runbooks/README.md), [docs/runbooks/operator-commands.md](../../docs/runbooks/operator-commands.md), and [docs/runbooks/cell-recovery.md](../../docs/runbooks/cell-recovery.md); do not duplicate operational procedures.

- [x] Complete module interfaces and example guidance (AC: 2, 5-7)
  - [x] Update [modules/ecs-scheduled-job/README.md](../../modules/ecs-scheduled-job/README.md) and [modules/ecs-scheduled-job-platform/README.md](../../modules/ecs-scheduled-job-platform/README.md) from their actual variables and outputs; document defaults, validation, sensitivity, ownership, and security implications.
  - [x] Update both basic examples with backend-free validation, synthetic identifiers, no tfvars, immutable references, and outputs operators may use.
  - [x] Add a production-reference document/example that is explicitly non-deployable and launch-blocked until externally supplied checklist evidence is resolved; never invent account IDs, Regions, notification targets, pilot jobs, owners, or approvals.

- [x] Automate documentation and example qualification (AC: 9)
  - [x] Extend existing validation/hygiene tests rather than creating a parallel documentation checker. Cover required guide sections, valid local links, Terraform examples, immutable pins, no secret-bearing content, and prohibited direct-control guidance.
  - [x] Keep scripts/validate.py as the single full-repository entry point. Add only deterministic, credential-free checks.

- [x] Verify the guide is operationally accurate (AC: 1-9)
  - [x] Run focused documentation/contract tests and backend-free Terraform initialization/validation for every touched example.
  - [x] Run scripts/validate.sh with the pinned uv toolchain; if Terraform Registry or PyPI lookup is required, use nameserver 192.168.1.1 and report network failures separately from code failures.
  - [x] Run git diff --check; record validation and rollback/forward-fix notes in the changed documentation.

### Review Findings

- [x] [Review][Patch] Document every module interface [modules/ecs-scheduled-job/README.md:44]
- [x] [Review][Patch] Provide canonical completion-record examples [docs/scheduled-job-adoption-guide.md:19]
- [x] [Review][Patch] Add a fail-closed production reference [docs/scheduled-job-adoption-guide.md:28]
- [x] [Review][Patch] Complete compatibility guidance [docs/scheduled-job-adoption-guide.md:7]
- [x] [Review][Patch] Make documentation qualification match its claim [tests/contract/test_documentation.py:102]
- [x] [Review][Patch] Clarify the supported reservation handoff [docs/scheduled-job-adoption-guide.md:9]

## Dev Notes

### Existing boundaries to preserve

- Reuse the existing module READMEs, basic examples, outputs, Compatibility Package, and Runbooks. This story documents the production standard; it does not introduce a new runtime, Scheduler target, Terraform ownership model, or live pilot.
- The platform module owns Cell state and discovery. The scheduled-job module owns per-job resources and consumes the Cell Contract. Never add terraform_remote_state, cross-root mutation, direct ledger writes, or direct Scheduler-to-ECS wiring.
- Preserve AD-3 through AD-12: independent expectation and launch clocks, Cell-derived occurrence IDs, immutable CONFIG, Process Manager as the sole state writer, marker-plus-zero-exit completion, deadline detection without automatic cancellation, at-least-once/replay semantics, and role separation.
- Production activation remains fail-closed. Documentation must distinguish a credential-free fixture from production evidence and name unresolved external launch inputs as blockers, not placeholders that imply approval.

### AWS Terraform documentation standard

- Retain Terraform >= 1.10, < 2.0; explain the tested seeds separately. Keep provider/module examples pinned and backend-free.
- Require private subnets, bounded egress, scoped IAM/PassRole, source-account/source-ARN protections where AWS supports them, immutable images, secret references rather than values, explicit log retention, alarms, and Runbook/rollback links.
- No public ingress, broad IAM, latest, state, plans, tfvars, credentials, secrets, generated artifacts, or fictional production-ready identifiers in examples.

### Previous-story intelligence

- Story 3.9 established strict immutable release, migration, deprecation, and retirement evidence with protected workflow validation. Describe those capabilities accurately, but do not represent documentation examples or synthetic fixtures as deployment, approval, or pilot evidence.
- Use the established full validator, Ruff, mypy, pytest, Terraform format/validate, Checkov, and repository-hygiene gates. Validation is credential-free and never plans, applies, or reads protected state.

### Project Structure Notes

- Documentation belongs in README.md, module-local README.md, module basic examples, and docs/runbooks; keep operator procedures in the existing Runbooks and use links rather than copied commands.
- Tests belong under tests/contract or the existing hygiene/validation owner. Do not add a second validation entry point.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-4.1-Publish-the-Scheduled-Job-Adoption-Guide]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-4-Qualify-and-Adopt-the-Production-Standard]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-2]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-3]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-12]
- [Source: _bmad/custom/standards/aws-terraform-implementation.md]
- [Source: _bmad-output/implementation-artifacts/3-9-deprecate-and-retire-platform-versions.md]
- [Source: _bmad-output/project-context.md]

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Added the adoption guide, ordered repository navigation, Cell-safe completion-record contract, and fail-closed production reference.
- Linked module and runbook documentation to the guide; kept operator procedures in their authoritative runbooks.
- Made basic-example log retention explicit and added deterministic guide/link/example safety checks.
- Validation passed: `./scripts/validate.sh` (333 tests, 291 subtests; Terraform, Ruff, mypy, Checkov, and hygiene), plus `git diff --check`.
- Rollback/forward fix: revert the documentation and test changes together; no deployed resource, state, credential, or schedule was changed.
- Resolved six code-review findings: canonical completion records, activation/reservation gates, fail-closed production reference, compatibility guidance, interface references, and deterministic coverage.

### File List

- _bmad-output/implementation-artifacts/4-1-publish-the-scheduled-job-adoption-guide.md
- README.md
- docs/scheduled-job-adoption-guide.md
- docs/runbooks/README.md
- modules/ecs-scheduled-job/README.md
- modules/ecs-scheduled-job-platform/README.md
- modules/ecs-scheduled-job/examples/basic/main.tf
- tests/contract/test_documentation.py
- _bmad-output/implementation-artifacts/sprint-status.yaml

## Change Log

- 2026-07-31: Published scheduled-job adoption guidance, documentation qualification checks, and explicit non-production log retention.
- 2026-07-31: Addressed six code-review findings.
