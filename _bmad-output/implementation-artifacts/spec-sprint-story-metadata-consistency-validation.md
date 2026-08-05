---
title: 'Validate Sprint and Story Metadata Consistency'
type: 'chore'
created: '2026-08-04'
status: 'done'
baseline_commit: da39c8f294e00bfd0040be4f86bf9f13e977aefc
review_loop_iteration: 0
context:
  - '_bmad-output/project-context.md'
  - '_bmad-output/implementation-artifacts/sprint-status.yaml'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Story documents can silently disagree across their filename, story heading, body status, optional frontmatter, and `sprint-status.yaml`. Existing examples include a wrong Story 4.10 frontmatter identity and a stale Story 4.8 frontmatter status. This makes sprint reporting and workflow routing unreliable.

**Approach:** Add a deterministic, credential-free repository validation that discovers story records, parses their identity and status from the existing formats, and rejects missing, orphaned, or contradictory metadata. Add focused passing and negative fixtures/tests without changing story content as part of this implementation.

## Boundaries & Constraints

**Always:** Treat the filename slug and `# Story E.S:` heading as the canonical record identity; when frontmatter exists, require its `epic`, `story`, and `status` to agree with the record; require every discovered story record to have exactly one matching story key in `development_status` with the same status; allow legacy story files without frontmatter when their heading, body status, and sprint entry are consistent; fail closed with file/key-specific diagnostics; remain credential-free and deterministic.

**Ask First:** None.

**Never:** Do not rewrite or auto-correct story metadata; do not infer missing statuses; do not validate retrospective/action-item entries as stories; do not change sprint workflow semantics or require live AWS access.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | Consistent legacy and frontmatter story records plus matching sprint keys | Validation succeeds | N/A |
| FRONTMATTER_MISMATCH | Frontmatter identity or status differs from filename, heading, or body | Validation fails and names the story file and fields | Nonzero validation result |
| SPRINT_MISMATCH | Story record is missing from sprint status, or sprint status has no story record | Validation fails and names the orphan key/file | Nonzero validation result |
| MALFORMED_RECORD | Story heading or body status is missing/invalid | Validation fails without guessing | Nonzero validation result |

</frozen-after-approval>

## Code Map

- `scripts/story_metadata.py` -- pure parser and cross-source consistency validator.
- `scripts/validate.py` -- required full-repository validation entry point.
- `tests/contract/test_story_metadata.py` -- focused positive and negative metadata cases.
- `tests/contract/fixtures/story-metadata/` -- minimal deterministic story/sprint fixtures.

## Tasks & Acceptance

**Execution:**
- [x] `scripts/story_metadata.py` -- implement deterministic discovery, parsing, normalization, and fail-closed consistency checks -- centralize metadata rules for reuse by tests and the repository gate.
- [x] `tests/contract/test_story_metadata.py` and `tests/contract/fixtures/story-metadata/` -- add passing legacy/frontmatter cases and negative identity, status, missing, orphan, and malformed cases -- prove each boundary is executable.
- [x] `scripts/validate.py` -- invoke the metadata validator as a required credential-free stage -- prevent silent drift in normal validation.
- [x] `modules/` or `docs/` -- no runtime/infrastructure changes; document only if the validator’s operator-facing behavior needs explanation.

**Acceptance Criteria:**
- Given a story file and sprint entry agree across filename, heading, body status, and frontmatter when present, when validation runs, then it passes deterministically.
- Given any identity/status mismatch or missing/orphaned story record, when validation runs, then it fails with the exact path/key and conflicting values.
- Given malformed YAML, heading, or status metadata, when validation runs, then it fails closed without guessing.
- Given the repository’s current metadata, when the full validation gate runs, then it passes after the known defects are corrected in the validator’s test fixtures or source records as appropriate.

## Design Notes

The validator should distinguish story records from epic, retrospective, and action-item entries by requiring a story heading and numeric `E.S` identity. Numeric normalization must avoid float formatting errors (`4.10` is story number 10, not 1). Sprint keys should be matched by exact numeric identity plus slug, not prefix matching.

## Verification

**Commands:**
- `pytest tests/contract/test_story_metadata.py -q` -- expected: all focused metadata tests pass.
- `python3 -m scripts.validate` -- expected: full credential-free validation passes.
- `git diff --check` -- expected: no whitespace errors.

## Suggested Review Order

**Validation logic**

- Strictly parse story identity and optional frontmatter before synchronization.
  [`story_metadata.py:126`](../../scripts/story_metadata.py#L126)

- Reject malformed story keys and compare every record against sprint status.
  [`story_metadata.py:207`](../../scripts/story_metadata.py#L207)

- Parse complete sprint YAML and reject duplicate or invalid metadata structures.
  [`story_metadata.py:99`](../../scripts/story_metadata.py#L99)

**Validation integration**

- Make metadata drift a required credential-free repository gate.
  [`validate.py:598`](../../scripts/validate.py#L598)

**Evidence and regression coverage**

- Exercise legacy, frontmatter, quoted, malformed, orphan, and encoding cases.
  [`test_story_metadata.py:26`](../../tests/contract/test_story_metadata.py#L26)

- Keep the sprint action status synchronized with the completed implementation.
  [`sprint-status.yaml:153`](sprint-status.yaml#L153)
