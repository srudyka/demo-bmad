---
epic: 4
story: 4.2
title: Complete an Actionable Job Runbook
status: done
baseline_commit: b3fb5a65d27a8367cb06d419f0438675b6cba1d8
---

# Story 4.2: Complete an Actionable Job Runbook

## Story

As an On-call Engineer, I want a job-specific Runbook tied to platform alerts and controls, so that I can diagnose, rerun, escalate, and recover without guessing.

## Acceptance Criteria

1. Provide a reusable production Runbook template that requires job identity, ownership/escalation, Cell location, schedule/runtime/overlap/idempotency, dependencies, notification, Deployment Identity, recovery objective, and support hours; unresolved ownership, placeholders, and external prerequisites block readiness.
2. Provide a completed, non-production canary Runbook using secret-free discoverable fixture outputs, without account-specific reusable-template values.
3. Document canonical structured start/success/failure evidence, authoritative occurrence fields, marker-plus-essential-exit completion, deadline behavior, late/duplicate/conflicting evidence, and `EXPECTED`, `STARTED`, `SUCCEEDED`, `FAILED`, `OVERDUE`, `MISSED`, `AMBIGUOUS` states.
4. Map every schedule-delivery, launch, runtime, completion, deadline, log-delivery, alert-routing, and Cell-health alarm to first query, evidence, decision, owner/escalation, response, and tested procedure.
5. Provide safe operator-role investigation, rerun, rollback/forward-fix, recovery, and compensation procedures; prohibit workload roles, direct state/table mutation, secret/raw-config output, Terraform-state inspection, direct `RunTask`, caller occurrence IDs, schedule edits, stale CONFIG, automatic cancellation, and automatic cross-Region recovery.
6. Add deterministic credential-free documentation tests and keep `scripts/validate.py` as the sole full-repository entry point.

## Tasks / Subtasks

- [x] Create reusable and canary Runbooks (AC: 1-3, 5)
  - [x] Add `docs/runbooks/job-runbook-template.md` with readiness-blocking fields and safe operational decision trees.
  - [x] Add `docs/runbooks/canary-job-runbook.md` using `fixtures/canary` output names and no real account identifiers.
  - [x] Link the new Runbooks from `docs/runbooks/README.md` and the adoption guide without duplicating operator/recovery authority.
- [x] Add alert, investigation, and change-control guidance (AC: 3-5)
  - [x] Cover all alert planes and required output handoff (`job_identity`, `schedule`, `task`, `logs`, `config`, `operations`, `alarms`, `deployment_identity`).
  - [x] Bind Runbook version and reviewed source revision to the proposed generation; include tabletop/non-production exercise evidence.
- [x] Automate qualification and verify (AC: 6)
  - [x] Extend `tests/contract/test_documentation.py` for required sections, safe commands, output names, and absent placeholders/secrets.
  - [x] Run focused tests, `terraform fmt -check`, `git diff --check`, and `./scripts/validate.sh` with pinned uv; report any DNS failure separately.

## Dev Notes

- Scheduler always targets the Cell, never ECS. The Process Manager is the sole occurrence-state writer; evidence is immutable, deduplicated, and conflicts/multiple task ARNs are `AMBIGUOUS`.
- Reuse `docs/runbooks/operator-commands.md` for authenticated command authority and `docs/runbooks/cell-recovery.md` for restore ordering. Do not invent direct AWS mutation commands.
- The canary is disabled/non-production. Refer to `terraform output canary` and output keys, not account IDs, ARNs, secrets, or raw CONFIG.
- Use only short-lived MFA operator access. Reruns require the Job Owner plus an independent Platform approver, compensation acknowledgement, canonical selector, and marker-plus-zero-essential-exit verification.
- Recovery is account/Region-local: disable launch first, retain ledger/queues/DLQs/logs, restore compatible generations through approved workflow, and never claim infrastructure rollback undoes application side effects.
- Follow the AWS Terraform standard as documentation acceptance criteria: immutable images, private networking, bounded egress, scoped IAM/PassRole, retained logs, alarms, Runbook/rollback links, no state/tfvars/credentials or fictional production identifiers.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-4.2-Complete-an-Actionable-Job-Runbook]
- [Source: docs/runbooks/README.md]
- [Source: docs/runbooks/operator-commands.md]
- [Source: docs/runbooks/cell-recovery.md]
- [Source: _bmad-output/implementation-artifacts/4-1-publish-the-scheduled-job-adoption-guide.md]
- [Source: _bmad-output/project-context.md]

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Focused documentation contract tests passed: 8 tests and 113 subtests.
- Full validation reached Terraform initialization but was blocked by DNS resolution for `registry.terraform.io` and PyPI; no deployment or state artifacts were created.

### File List

## Change Log

- 2026-07-31: Created implementation-ready context for Story 4.2.

### Review Findings

- [x] [Review][Patch] Add an explicit Cell location/contract binding to the production readiness record and make it readiness-blocking [docs/runbooks/job-runbook-template.md:5-10]
- [x] [Review][Patch] Replace the generic alert-investigation instruction with concrete mappings for all eight alarm planes, including first query, evidence, decision, owner/escalation, response, and tested procedure; include the same actionable handoff in the canary runbook [docs/runbooks/job-runbook-template.md:22-30; docs/runbooks/canary-job-runbook.md:18-23]
- [x] [Review][Patch] Define deterministic deadline transitions and late/duplicate/conflicting evidence handling for MISSED and OVERDUE states [docs/runbooks/job-runbook-template.md:12-20; docs/runbooks/canary-job-runbook.md:9-16]
- [x] [Review][Patch] Enumerate the exact secret-free `fixtures/canary` output keys and their safe operational use instead of naming only conceptual values [docs/runbooks/canary-job-runbook.md:3-7]
- [x] [Review][Patch] Make canary state handling and rerun/recovery controls explicit for all required states, stale CONFIG, duplicate/late/conflicting evidence, caller occurrence IDs, schedule edits, workload roles, and compensation/dual approval [docs/runbooks/canary-job-runbook.md:9-23]
- [x] [Review][Patch] Add concrete rollback/recovery verification queries and pass/fail criteria for each required plane [docs/runbooks/job-runbook-template.md:41-46]
- [x] [Review][Patch] Add mandatory Runbook version, reviewed source revision, tabletop/non-production exercise date/result/evidence fields and readiness gating [docs/runbooks/job-runbook-template.md:48-57]
- [x] [Review][Patch] Strengthen documentation contract tests to assert all required fields, states, alarm planes, output keys, links, and forbidden placeholders/secrets/raw CONFIG/state/unsafe commands [tests/contract/test_documentation.py:10-36]
- [x] [Review][Patch] Add link-target assertions so the documented broken-link production gate is enforced [docs/runbooks/job-runbook-template.md:53-57; tests/contract/test_documentation.py:150-160]
