# Story {{epic_num}}.{{story_num}}: {{story_title}}

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a {{role}},
I want {{action}},
so that {{benefit}}.

## Acceptance Criteria

1. [Add acceptance criteria from epics/PRD]

## Tasks / Subtasks

- [ ] Task 1 (AC: #)
  - [ ] Subtask 1.1
- [ ] Task 2 (AC: #)
  - [ ] Subtask 2.1

## Dev Notes

- Relevant architecture patterns and constraints
- Source tree components to touch
- Testing standards summary

### Authority / Provenance / Adversarial Preflight

Complete this checklist before implementation begins. Link each checked item to the relevant acceptance criterion, task, source file, or test. Mark an item `N/A` only with a written rationale; do not leave unknowns implicit.

- [ ] **Authority:** Identify the authoritative state, writer, reader, and transition for every stateful or decision-bearing input. Do not create a competing authority.
- [ ] **Bound inputs:** List the exact release, source revision, workflow/run, account, Region, environment, job/generation, target, identity, policy, and configuration bindings that must remain consistent.
- [ ] **Provenance:** For every evidence or artifact input, identify its producer, checksum/seal, sensitivity class, retention/access boundary, freshness rule, and how the implementation verifies it.
- [ ] **Untrusted inputs:** Identify caller-supplied flags, paths, statuses, counts, timestamps, approvals, workflow outputs, and external payloads. State how each is independently validated or rejected.
- [ ] **Adversarial paths:** Define executable negative cases for stale, missing, malformed, duplicated, replayed, cross-scope, synthetic, unauthorized, partial-failure, and changed-input scenarios relevant to this story.
- [ ] **Security boundary:** Record IAM/identity, secret-handling, network, artifact-root, protected-workflow, self-review, and least-privilege constraints. Do not infer live authorization from static or fixture evidence.
- [ ] **Reliability and observability:** Identify retries, idempotency, concurrency, deadlines, alarms, metrics, logs, escalation, disablement, and evidence-preservation behavior for failure paths.
- [ ] **Rollback and compensation:** Define disable-first ordering, known-good identity/configuration, state/address safety, rollback verification, and application-side compensation limits.
- [ ] **Validation gate:** Name focused tests, full regression checks, formatting/type checks, infrastructure validation, security scans, and repository-hygiene checks required before review.
- [ ] **Live boundary:** State whether the story uses credential-free fixtures, protected/disposable qualification, or live production evidence. Explicitly prohibit claims outside that boundary.

### Project Structure Notes

- Alignment with unified project structure (paths, modules, naming)
- Detected conflicts or variances (with rationale)

### References

- Cite all technical details with source paths and sections, e.g. [Source: docs/<file>.md#Section]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

### Review Evidence Register

Keep one indexed review record for this story. Complete it before the story is marked `done`.

- Review baseline: `{{baseline_commit_or_revision}}`
- Acceptance audit: `{{acceptance_audit_reference_or_status}}`
- Adversarial review: `{{adversarial_review_reference_or_status}}`
- Edge-case review: `{{edge_case_review_reference_or_status}}`
- Validation evidence: `{{focused_tests_full_tests_lint_type_infrastructure_security_hygiene}}`
- Findings and dispositions: `{{review_findings_section_or_evidence_index}}`
- Deferred risks: `{{deferred_work_reference_or_none}}`
- Final review status: `{{review_status}}`
